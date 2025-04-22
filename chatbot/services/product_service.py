# chatbot/services/product_service.py
import logging
from shop_app.models import Product
from django.db.models import Q

logger = logging.getLogger(__name__)


def search_products(query, limit=5):
    """
    Busca productos basado en un query
    Retorna una lista de productos ordenados por relevancia
    """
    if not query or len(query) < 3:
        return get_featured_products(limit)

    try:
        # Búsqueda por nombre o descripción
        name_matches = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).distinct()

        # Búsqueda por categoría
        category_matches = Product.objects.filter(
            category__icontains=query
        )

        # Combinar resultados sin duplicados
        combined_results = list(name_matches)
        for product in category_matches:
            if product not in combined_results:
                combined_results.append(product)

        return combined_results[:limit]

    except Exception as e:
        logger.error(f"Error al buscar productos: {str(e)}")
        return []


def get_featured_products(limit=5):
    """Obtiene productos destacados"""
    try:
        # Usar los productos más recientes como destacados
        return Product.objects.all().order_by('-id')[:limit]
    except Exception as e:
        logger.error(f"Error al obtener productos destacados: {str(e)}")
        return []


def get_products_by_category(category, limit=5):
    """Obtiene productos por categoría"""
    try:
        # Normalizar la categoría para coincidir con las opciones del modelo
        category_map = {
            'headphones': 'Headphones',
            'speakers': 'Speakers',
            'streaming': 'Streaming'
        }

        category_key = category_map.get(category.lower(), category)
        return Product.objects.filter(category=category_key)[:limit]
    except Exception as e:
        logger.error(f"Error al obtener productos por categoría: {str(e)}")
        return []


def get_product_details(product_id_or_name):
    """Obtiene detalles completos de un producto específico"""
    try:
        # Intentar buscar por ID
        if isinstance(product_id_or_name, int) or (
                isinstance(product_id_or_name, str) and product_id_or_name.isdigit()):
            return Product.objects.filter(id=int(product_id_or_name)).first()

        # Buscar por nombre exacto
        exact_match = Product.objects.filter(name__iexact=product_id_or_name).first()
        if exact_match:
            return exact_match

        # Buscar por nombre parcial
        partial_matches = Product.objects.filter(name__icontains=product_id_or_name)
        if partial_matches.exists():
            return partial_matches.first()

        return None

    except Exception as e:
        logger.error(f"Error al obtener detalles del producto: {str(e)}")
        return None


def get_all_categories():
    """Obtiene todas las categorías disponibles"""
    try:
        # Usar directamente las opciones del modelo Product
        return [choice[0] for choice in Product.CATEGORY]
    except Exception as e:
        logger.error(f"Error al obtener categorías: {str(e)}")
        return ["Headphones", "Speakers", "Streaming"]  # Fallback con valores conocidos


def format_product_for_chat(product):
    """Formatea un producto para mostrar en el chat"""
    if not product:
        return "Producto no disponible"

    formatted = f"**{product.name}**\n"
    formatted += f"Precio: ${product.price}\n"
    if product.category:
        formatted += f"Categoría: {product.category}\n"
    if product.description:
        formatted += f"Descripción: {product.description[:150]}...\n"

    return formatted


def format_product_list(products):
    """Formatea una lista de productos para mostrar en el chat"""
    if not products:
        return "No hay productos disponibles"

    response = ""
    for i, product in enumerate(products, 1):
        response += f"{i}. **{product.name}** - ${product.price}\n"

    return response