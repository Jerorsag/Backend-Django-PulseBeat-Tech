import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# Patrones de intención por categoría
INTENT_PATTERNS = {
    'busqueda_producto': [
        r'(?:busco|quiero|necesito|tienen|venden|hay)(?:.*)(?:auriculares|audífonos|altavoces|speakers|dispositivos)',
        r'(?:me interesan?|me gustan?)(?:.*)(?:productos|auriculares|altavoces)',
        r'(?:cuáles|que)(?:.*)(?:productos|modelos|opciones)(?:.*)(?:tienen|ofrecen)',
        r'(?:estoy buscando)(?:.*)',
        r'(?:muestrame|muéstrame|muestra|ver)(?:.*)(?:productos|catálogo|ofertas)'
    ],
    'info_producto': [
        r'(?:cómo|como)(?:.*)(?:funciona|es)(?:.*)',
        r'(?:características|caracteristicas|specs|especificaciones)(?:.*)',
        r'(?:detalles|información|informacion)(?:.*)(?:sobre|de|del)(?:.*)',
        r'(?:me puedes contar|explícame|explicame)(?:.*)(?:sobre|acerca)',
        r'(?:color|tamaño|peso|dimensiones|material)'
    ],
    'precio_producto': [
        r'(?:cuánto|cuanto)(?:.*)(?:cuesta|vale|es el precio|es el costo)',
        r'(?:precio|costo|valor)(?:.*)(?:de|del|de los|sobre)',
        r'(?:qué|que)(?:.*)(?:precio|costo)',
        r'(?:es caro|es barato|económico|economico)',
        r'(?:ofertas|descuentos|promociones)'
    ],
    'comparacion_productos': [
        r'(?:comparar|comparación|comparacion)(?:.*)',
        r'(?:diferencias|diferencia)(?:.*)(?:entre|con)',
        r'(?:qué|que|cual|cuál)(?:.*)(?:mejor|peor|recomendable)',
        r'(?:ventajas|desventajas)(?:.*)',
        r'(?:versus|vs|o)(?:.*)'
    ],
    'compra_carrito': [
        r'(?:comprar|adquirir|conseguir)(?:.*)',
        r'(?:añadir|anadir|agregar|poner)(?:.*)(?:carrito|cesta|carro)',
        r'(?:cómo|como)(?:.*)(?:compro|comprar|adquiero|puedo comprar)',
        r'(?:proceso de compra|checkout)',
        r'(?:pasarela de pago|pagar)'
    ],
    'envio_entrega': [
        r'(?:envío|envio|enviar|envían|envian|mandan)(?:.*)',
        r'(?:entrega|recibir|recibo|llega)(?:.*)',
        r'(?:cuánto|cuanto)(?:.*)(?:tarda|demora|toma|tiempo)',
        r'(?:a domicilio|shipping|seguimiento|tracking)',
        r'(?:internacional|fuera del país|fuera del pais)'
    ],
    'soporte_problema': [
        r'(?:problema|issue|error|falla|no funciona)(?:.*)',
        r'(?:ayuda|soporte|asistencia)(?:.*)(?:con|sobre|para)',
        r'(?:garantía|garantia|servicio|reparación|reparacion)',
        r'(?:no puedo|tengo problemas|dificultad)',
        r'(?:se dañó|se daño|roto|descompuesto)'
    ],
    'general': [
        r'(?:hola|hey|saludos|buenos días|buenas tardes|buenas noches)',
        r'(?:gracias|muchas gracias|te agradezco|agradecido)',
        r'(?:adiós|adios|chao|hasta luego|hasta pronto)',
        r'(?:cómo estás|como estas|qué tal|que tal)',
        r'(?:quién eres|quien eres|qué eres|que eres|tu nombre)'
    ]
}


def analyze_intent(message):
    """
    Analiza la intención del mensaje del usuario
    Retorna un diccionario con la intención principal y la confianza
    """
    message = message.lower().strip()
    matched_intents = {}

    # Verificar cada patrón de intención
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message):
                matched_intents[intent] = matched_intents.get(intent, 0) + 1

    # Si no hay coincidencias, asignar intención general
    if not matched_intents:
        return {
            'primary_intent': 'general',
            'confidence': 1.0,
            'all_intents': {'general': 1}
        }

    # Calcular la intención principal y la confianza
    total_matches = sum(matched_intents.values())
    primary_intent = max(matched_intents, key=matched_intents.get)
    confidence = matched_intents[primary_intent] / total_matches

    return {
        'primary_intent': primary_intent,
        'confidence': confidence,
        'all_intents': matched_intents
    }


def extract_entities(message):
    """
    Extrae entidades relevantes del mensaje
    Devuelve un diccionario de entidades encontradas
    """
    message = message.lower().strip()
    entities = {}

    # Detectar productos
    product_patterns = [
        (r'(?:auriculares|audífonos|headphones)(?:\s\w+){0,3}', 'producto_audio'),
        (r'(?:altavoces|bocinas|speakers|parlantes)(?:\s\w+){0,3}', 'producto_altavoz'),
        (r'(?:streaming|streamer|reproductor)(?:\s\w+){0,3}', 'producto_streaming')
    ]

    for pattern, entity_type in product_patterns:
        matches = re.findall(pattern, message)
        if matches:
            entities[entity_type] = matches

    # Detectar referencias a precios
    price_matches = re.findall(r'\$\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*(?:dólares|dolares|pesos)', message)
    if price_matches:
        entities['precio'] = price_matches

    # Detectar referencias temporales
    time_matches = re.findall(r'(?:hoy|mañana|pasado mañana|ayer|próxima semana|proximo mes)', message)
    if time_matches:
        entities['tiempo'] = time_matches

    # Detectar nombres de productos específicos (ejemplo simplificado)
    specific_products = [
        'pulsebeat pro', 'soundwave x3', 'bassboost elite', 'soundtower',
        'pulsebox', 'roomfill'
    ]

    for product in specific_products:
        if product in message:
            if 'producto_especifico' not in entities:
                entities['producto_especifico'] = []
            entities['producto_especifico'].append(product)

    return entities


def extract_product_name(message):
    """Extrae posibles nombres de productos del mensaje"""
    # Palabras a ignorar
    stop_words = [
        'producto', 'productos', 'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
        'vender', 'venden', 'tiene', 'tienen', 'quiero', 'busco', 'precio', 'precios',
        'cuanto', 'cuánto', 'cuesta', 'cuestan', 'sobre', 'acerca', 'para', 'como', 'cómo'
    ]

    # Primero intentamos extraer productos específicos
    entities = extract_entities(message)
    if 'producto_especifico' in entities and entities['producto_especifico']:
        return entities['producto_especifico'][0]

    # Procesamiento general por palabras
    words = message.lower().split()
    potential_words = [word for word in words if len(word) > 3 and word not in stop_words]

    if potential_words:
        # Devolver la palabra más larga (posiblemente más específica)
        return max(potential_words, key=len)

    return None