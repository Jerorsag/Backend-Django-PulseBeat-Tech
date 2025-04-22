import logging
import random
from django.conf import settings

logger = logging.getLogger(__name__)

# Respuestas predefinidas para casos comunes
PREDEFINED_RESPONSES = {
    'saludo': [
        "¡Hola! Soy el asistente virtual de PulseBeat Tech. ¿En qué puedo ayudarte hoy? 😊",
        "¡Bienvenido a PulseBeat Tech! Estoy aquí para ayudarte con nuestros productos de audio. ¿Qué estás buscando? 🎧",
        "¡Hola! Encantado de atenderte. ¿Cómo puedo asistirte con nuestros productos? 👋"
    ],
    'despedida': [
        "¡Gracias por contactarnos! Si necesitas algo más, estaré aquí para ayudarte. ¡Hasta pronto! 👋",
        "Ha sido un placer ayudarte. ¡Vuelve pronto! 😊",
        "¡Que tengas un excelente día! Estamos para servirte cuando lo necesites. 🎵"
    ],
    'agradecimiento': [
        "¡De nada! Estoy aquí para ayudarte. ¿Hay algo más en lo que pueda asistirte? 😊",
        "Es un placer poder ayudarte. ¿Necesitas algo más? 🎧",
        "No hay de qué. ¿Puedo ayudarte con algo más sobre nuestros productos? 👍"
    ],
    'productos_no_encontrados': [
        "Lo siento, no encontré productos que coincidan con tu búsqueda. ¿Puedes ser más específico o quieres ver nuestras categorías disponibles? 🔍",
        "No tenemos productos que coincidan exactamente con esa descripción. ¿Te gustaría ver alternativas similares o explorar nuestro catálogo? 📋",
        "No encontré resultados para esa consulta. ¿Quieres que te muestre nuestros productos más populares? 🎧"
    ],
    'error_generico': [
        "Lo siento, estoy teniendo problemas para procesar tu solicitud. ¿Puedes intentarlo de nuevo o preguntar de otra forma? 🔄",
        "Parece que hay un problema técnico. ¿Podemos intentar con otra consulta? 🛠️",
        "No pude completar esa operación. ¿Puedo ayudarte con algo más mientras tanto? 🤔"
    ]
}

# Sugerencias para diferentes tipos de consultas
CONTEXTUAL_SUGGESTIONS = {
    'busqueda_producto': [
        "Ver más detalles",
        "Comparar modelos",
        "Ver precio",
        "Añadir al carrito"
    ],
    'precio_producto': [
        "Ver especificaciones",
        "Comparar con otros modelos",
        "Ver opiniones",
        "Añadir al carrito"
    ],
    'info_producto': [
        "Ver precio",
        "Ver productos similares",
        "Conocer disponibilidad",
        "Añadir al carrito"
    ],
    'soporte_problema': [
        "Contactar soporte",
        "Ver garantía",
        "Preguntar por reembolso",
        "Buscar solución"
    ]
}


def get_predefined_response(type_key):
    """Obtiene una respuesta predefinida aleatoria según el tipo"""
    if type_key in PREDEFINED_RESPONSES:
        return random.choice(PREDEFINED_RESPONSES[type_key])
    return None


def get_contextual_suggestions(intent):
    """Obtiene sugerencias contextuales basadas en la intención"""
    if intent in CONTEXTUAL_SUGGESTIONS:
        # Obtener todas las sugerencias para esta intención
        suggestions = CONTEXTUAL_SUGGESTIONS[intent]
        # Devolver hasta 3 sugerencias aleatorias
        if len(suggestions) > 3:
            return random.sample(suggestions, 3)
        return suggestions

    # Sugerencias por defecto
    return ["Ver productos", "Preguntar precio", "Contactar soporte"]


def format_bot_response(response_text, source, intent=None, entities=None):
    """
    Formatea la respuesta del bot para enviarla al frontend
    Incluye sugerencias contextuales basadas en la intención
    """
    # Asegurar que la respuesta termine con emoji si es respuesta de Ollama
    if source == 'ollama' and not any(emoji in response_text for emoji in ['😊', '👍', '🎧', '💰', '📦']):
        common_emojis = ['😊', '👍', '🎧', '🎵', '🔊', '💰', '📦', '🎚️', '🎛️']
        response_text += f" {random.choice(common_emojis)}"

    # Obtener sugerencias contextuales
    suggestions = get_contextual_suggestions(intent) if intent else []

    # Estructurar la respuesta para el frontend
    formatted_response = {
        "response": response_text,
        "source": source,
        "suggestions": suggestions
    }

    # Incluir metadatos adicionales si están disponibles
    if intent:
        formatted_response["intent"] = intent

    if entities:
        formatted_response["entities"] = entities

    return formatted_response


def format_product_recommendations(products, query=None):
    """
    Formatea una lista de recomendaciones de productos para mostrar en el chat
    """
    if not products or len(products) == 0:
        return get_predefined_response('productos_no_encontrados')

    intro_phrases = [
        f"He encontrado {len(products)} productos que podrían interesarte:",
        f"Aquí tienes {len(products)} recomendaciones basadas en tu búsqueda:",
        f"Estos son los productos que coinciden con '{query}':" if query else "Estos productos podrían interesarte:"
    ]

    response = f"{random.choice(intro_phrases)}\n\n"

    for i, product in enumerate(products, 1):
        response += f"{i}. **{product.name}** - ${product.price}\n"
        if product.description:
            # Truncar descripción larga
            desc = product.description[:100] + "..." if len(product.description) > 100 else product.description
            response += f"   {desc}\n"
        if product.category:
            response += f"   Categoría: {product.category}\n"

        # Añadir espacio entre productos
        if i < len(products):
            response += "\n"

    # Añadir una pregunta de seguimiento
    followup_questions = [
        "¿Te gustaría más información sobre alguno de estos productos? 🎧",
        "¿Hay algún producto específico que te interese conocer más? 🔍",
        "¿Puedo ayudarte a decidir cuál se adapta mejor a tus necesidades? 🤔"
    ]

    response += f"\n{random.choice(followup_questions)}"

    return response


def format_single_product_details(product):
    """
    Formatea los detalles completos de un producto para mostrar en el chat
    """
    if not product:
        return get_predefined_response('productos_no_encontrados')

    response = f"**{product.name}**\n\n"
    response += f"💰 **Precio:** ${product.price}\n"

    if product.category:
        response += f"🏷️ **Categoría:** {product.category}\n"

    if product.description:
        response += f"\n📝 **Descripción:**\n{product.description}\n"

    # Añadir call-to-action
    cta_options = [
        "¿Te gustaría añadir este producto al carrito? 🛒",
        "¿Quieres ver productos similares o tienes alguna pregunta específica? 🔍",
        "Si estás interesado, puedo ayudarte con el proceso de compra. ¿Qué te parece? 💳"
    ]

    response += f"\n{random.choice(cta_options)}"

    return response