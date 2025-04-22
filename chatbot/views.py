import json
import logging
import time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .models import ChatConversation, ChatMessage, TrainingFeedback
from .services import (
    get_ollama_response, is_ollama_available,
    search_products, get_featured_products, get_products_by_category, get_product_details,
    format_bot_response, format_product_recommendations, format_single_product_details, get_predefined_response
)
from .utils.intent_analyzer import analyze_intent, extract_entities, extract_product_name

logger = logging.getLogger(__name__)


@csrf_exempt
def chat_endpoint(request):
    """
    Endpoint principal para el chatbot
    Procesa mensajes y devuelve respuestas inteligentes
    """
    if request.method == 'POST':
        start_time = time.time()

        try:
            # Extraer datos del request
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            session_id = data.get('session_id', '')
            feedback = data.get('feedback', None)  # Para retroalimentación de respuestas anteriores

            # Si es retroalimentación, procesarla y terminar
            if feedback is not None and 'message_id' in data:
                process_feedback(data.get('message_id'), feedback)
                return JsonResponse({"success": True})

            # Verificar mensaje y session_id
            if not message:
                return JsonResponse({
                    "response": "Por favor, envía un mensaje para que pueda ayudarte. 😊",
                    "source": "validation"
                })

            if not session_id:
                logger.warning("Request sin session_id")
                session_id = f"temp_{time.time()}"

            # Registrar el mensaje para análisis
            logger.info(f"Chat message - Session: {session_id}, Message: {message[:50]}...")

            # Analizar la intención y entidades del mensaje
            intent_analysis = analyze_intent(message)
            entities = extract_entities(message)

            # Obtener o crear conversación
            user = request.user if request.user.is_authenticated else None
            conversation = get_or_create_conversation(session_id, user, request)

            # Guardar mensaje del usuario
            user_message = save_message(
                conversation=conversation,
                content=message,
                is_bot=False,
                detected_intent=intent_analysis['primary_intent'],
                detected_entities=entities
            )

            # Obtener historial de conversación para contexto
            conversation_history = get_conversation_history(conversation)

            # Determinar la respuesta basada en la intención
            response_data = generate_response(
                message,
                intent_analysis,
                entities,
                conversation_history,
                user
            )

            # Guardar respuesta del bot
            bot_message = save_message(
                conversation=conversation,
                content=response_data['response'],
                is_bot=True,
                source=response_data['source'],
                detected_intent=intent_analysis['primary_intent'],
                detected_entities=entities,
                processing_time=time.time() - start_time
            )

            # Incluir ID del mensaje para retroalimentación
            response_data['message_id'] = bot_message.id
            response_data['session_id'] = session_id
            response_data['processing_time'] = round(time.time() - start_time, 2)

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            logger.error("Error: JSON inválido en la solicitud")
            return JsonResponse({
                "response": "Lo siento, hubo un error al procesar tu solicitud. Por favor, inténtalo de nuevo. 🔄",
                "source": "error"
            }, status=400)

        except Exception as e:
            logger.exception(f"Error en chat_endpoint: {str(e)}")
            return JsonResponse({
                "response": "Lo siento, estoy teniendo problemas para procesar tu solicitud en este momento. ¿Podrías intentarlo de nuevo más tarde? 🙇",
                "source": "error"
            }, status=500)

    return JsonResponse({"error": "Método no permitido"}, status=405)


def process_feedback(message_id, feedback_value):
    """Procesa la retroalimentación para un mensaje del bot"""
    try:
        message = ChatMessage.objects.get(id=message_id, is_bot=True)
        message.feedback = feedback_value  # True=positivo, False=negativo
        message.save(update_fields=['feedback'])

        # Para feedback negativo, crear entrada para mejorar
        if feedback_value is False:
            TrainingFeedback.objects.create(
                message=message,
                notes="Retroalimentación negativa del usuario"
            )

        logger.info(f"Feedback registrado para mensaje {message_id}: {'positivo' if feedback_value else 'negativo'}")
    except Exception as e:
        logger.error(f"Error al procesar feedback: {str(e)}")


def get_or_create_conversation(session_id, user=None, request=None):
    """Obtiene o crea una conversación"""
    try:
        conversation, created = ChatConversation.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user': user,
                'user_location': request.META.get('HTTP_X_FORWARDED_FOR', '') if request else None,
                'source_page': request.META.get('HTTP_REFERER', '') if request else None,
                'browser_info': request.META.get('HTTP_USER_AGENT', '') if request else None
            }
        )

        # Actualizar usuario si existe y la conversación no tiene usuario asignado
        if user and not conversation.user:
            conversation.user = user
            conversation.save(update_fields=['user'])

        return conversation
    except Exception as e:
        logger.error(f"Error al obtener/crear conversación: {str(e)}")
        # Fallback: crear conversación temporal
        return ChatConversation.objects.create(session_id=session_id)


def save_message(conversation, content, is_bot, source='user', detected_intent=None, detected_entities=None,
                 processing_time=None):
    """Guarda un mensaje en la base de datos"""
    try:
        message = ChatMessage.objects.create(
            conversation=conversation,
            content=content,
            is_bot=is_bot,
            source=source,
            detected_intent=detected_intent,
            detected_entities=detected_entities,
            processing_time=processing_time
        )
        return message
    except Exception as e:
        logger.error(f"Error al guardar mensaje: {str(e)}")
        return None


def get_conversation_history(conversation, limit=5):
    """Obtiene el historial reciente de la conversación"""
    try:
        return conversation.messages.order_by('-timestamp')[:limit][::-1]
    except Exception as e:
        logger.error(f"Error al obtener historial de conversación: {str(e)}")
        return []


def generate_response(message, intent_analysis, entities, conversation_history, user):
    """
    Genera una respuesta basada en la intención y entidades detectadas
    """
    intent = intent_analysis['primary_intent']
    confidence = intent_analysis['confidence']

    # 1. Manejar intenciones específicas con alta confianza
    if confidence > 0.7:
        # Saludos y expresiones sociales
        if intent == 'general':
            if any(word in message.lower() for word in ['hola', 'hey', 'saludos', 'buenos']):
                predefined = get_predefined_response('saludo')
                return format_bot_response(predefined, 'predefined', intent, entities)

            if any(word in message.lower() for word in ['gracias', 'agradezco', 'thanks']):
                predefined = get_predefined_response('agradecimiento')
                return format_bot_response(predefined, 'predefined', intent, entities)

            if any(word in message.lower() for word in ['adiós', 'adios', 'chao', 'hasta luego']):
                predefined = get_predefined_response('despedida')
                return format_bot_response(predefined, 'predefined', intent, entities)

        # Búsqueda de productos
        elif intent == 'busqueda_producto':
            product_name = extract_product_name(message)

            if product_name:
                # Buscar productos relacionados
                products = search_products(product_name)
                if products:
                    response = format_product_recommendations(products, product_name)
                    return format_bot_response(response, 'products', intent, entities)

            # Si no se encontró un producto específico, mostrar destacados
            featured_products = get_featured_products()
            response = format_product_recommendations(featured_products)
            return format_bot_response(response, 'products', intent, entities)

        # Información de precios
        elif intent == 'precio_producto':
            product_name = extract_product_name(message)

            if product_name:
                product = get_product_details(product_name)
                if product:
                    response = f"El precio de **{product.name}** es ${product.price}. ¿Te gustaría más información sobre este producto o añadirlo al carrito? 💰"
                    return format_bot_response(response, 'price', intent, entities)

            # No se pudo identificar el producto específico
            response = "¿De qué producto específico te gustaría saber el precio? Puedo ayudarte a encontrar la información que necesitas. 🔍"
            return format_bot_response(response, 'assistance', intent, entities)

        # Información de producto específica
        elif intent == 'info_producto':
            product_name = extract_product_name(message)

            if product_name:
                product = get_product_details(product_name)
                if product:
                    response = format_single_product_details(product)
                    return format_bot_response(response, 'product_details', intent, entities)

    # 2. Usar Ollama con contexto enriquecido para respuestas más complejas o de baja confianza
    # Buscar productos relacionados para enriquecer el contexto
    related_products = []
    product_name = extract_product_name(message)
    if product_name:
        related_products = search_products(product_name)

    # Obtener respuesta de Ollama
    ollama_result = get_ollama_response(
        message,
        products=related_products,
        conversation_history=conversation_history,
        user=user
    )

    if ollama_result:
        return format_bot_response(
            ollama_result['response'],
            ollama_result['source'],
            intent,
            entities
        )

    # 3. Respuesta de fallback
    fallback = "Lo siento, no pude entender completamente tu consulta. ¿Podrías reformularla o ser más específico? Estoy aquí para ayudarte con información sobre nuestros productos de audio. 🎧"
    return format_bot_response(fallback, 'fallback', intent, entities)