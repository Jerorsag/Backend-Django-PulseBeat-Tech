import requests
import logging
import time
import json
from django.conf import settings

logger = logging.getLogger(__name__)

# Configuración (puedes moverla a settings.py)
OLLAMA_BASE_URL = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = getattr(settings, 'OLLAMA_MODEL', 'llama3')
OLLAMA_TIMEOUT = getattr(settings, 'OLLAMA_TIMEOUT', 30)
OLLAMA_MAX_TOKENS = getattr(settings, 'OLLAMA_MAX_TOKENS', 300)


def is_ollama_available():
    """Verifica si Ollama está disponible"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error al verificar disponibilidad de Ollama: {str(e)}")
        return False


def get_product_context(products=None):
    """Crea un contexto de productos para enriquecer las consultas"""
    context = ""

    if products and len(products) > 0:
        context += "\nInformación de productos relevantes:\n"
        for i, product in enumerate(products, 1):
            context += f"{i}. {product.name}: ${product.price}\n"
            if product.description:
                context += f"   Descripción: {product.description[:100]}...\n"
            context += f"   Categoría: {product.category}\n"

    return context


def get_enhanced_prompt(user_message, products=None, conversation_history=None, user=None):
    """Crea un prompt mejorado con contexto"""
    store_context = (
        "Eres el asistente virtual oficial de PulseBeat Tech, una tienda especializada "
        "en tecnología de audio de alta calidad. Tu nombre es PulseBeat Assistant. "
        "La tienda vende principalmente: auriculares (headphones), altavoces (speakers) "
        "y dispositivos de streaming de audio."
    )

    user_context = ""
    if user and user.is_authenticated:
        user_context = f"\nEstás hablando con {user.username}, un cliente registrado."

    products_context = get_product_context(products)

    conversation_context = ""
    if conversation_history and len(conversation_history) > 0:
        conversation_context = "\nHistorial de conversación reciente:\n"
        for i, msg in enumerate(conversation_history[-3:]):  # Últimos 3 mensajes
            sender = "Usuario" if not msg.is_bot else "Tú"
            conversation_context += f"{sender}: {msg.content}\n"

    response_guidelines = (
        "\nPautas para tus respuestas:"
        "\n1. Sé conciso pero informativo."
        "\n2. Responde siempre en español a menos que te pregunten en otro idioma."
        "\n3. Incluye un emoji relevante al final de tu respuesta."
        "\n4. Nunca inventes especificaciones de productos que no conoces."
        "\n5. Si no estás seguro de algo, ofrece contactar con servicio al cliente."
        "\n6. Mantén un tono amigable y profesional."
        "\n7. Si te preguntan por un producto específico, proporciona detalles precisos."
    )

    full_prompt = (
        f"{store_context}\n{user_context}\n{products_context}\n{conversation_context}\n"
        f"{response_guidelines}\n\nPregunta del usuario: {user_message}"
    )

    return full_prompt


def get_ollama_response(user_message, products=None, conversation_history=None, user=None):
    """
    Obtiene una respuesta de Ollama con contexto enriquecido
    """
    start_time = time.time()

    try:
        if not is_ollama_available():
            logger.warning("Ollama no está disponible")
            return {
                "response": "Lo siento, nuestro sistema de asistencia inteligente no está disponible en este momento. ¿Puedo ayudarte con alguna consulta básica sobre nuestros productos? 🤔",
                "source": "fallback",
                "processing_time": time.time() - start_time
            }

        enhanced_prompt = get_enhanced_prompt(
            user_message, products, conversation_history, user
        )

        logger.info(f"Enviando prompt a Ollama: {user_message[:50]}...")

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": enhanced_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": OLLAMA_MAX_TOKENS
                }
            },
            timeout=OLLAMA_TIMEOUT
        )

        if response.status_code == 200:
            result = response.json()
            ai_response = result['response'].strip()

            # Asegurar que hay un emoji
            if not any(c in ai_response for c in ['😊', '🎧', '🔊', '💰', '📦']):
                common_emojis = ['😊', '🎧', '🔊', '📱', '💻', '🎵', '🎚️', '📦', '💰']
                import random
                ai_response += f" {random.choice(common_emojis)}"

            logger.info(f"Respuesta recibida de Ollama: {ai_response[:50]}...")

            return {
                "response": ai_response,
                "source": "ollama",
                "processing_time": time.time() - start_time
            }
        else:
            logger.error(f"Error en la respuesta de Ollama: {response.status_code}")
            return {
                "response": "Lo siento, estoy teniendo problemas para procesar tu consulta. ¿Puedes intentarlo con otras palabras o preguntarme sobre nuestros productos destacados? 🔄",
                "source": "error",
                "processing_time": time.time() - start_time
            }

    except Exception as e:
        logger.error(f"Error al llamar a Ollama: {str(e)}")
        return {
            "response": "Disculpa, no puedo responder en este momento. ¿Puedo ayudarte con información básica sobre nuestros productos o servicios? 🙇",
            "source": "error",
            "processing_time": time.time() - start_time
        }