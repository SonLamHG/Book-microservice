import logging

logger = logging.getLogger(__name__)


def handle_category_deleted(data):
    """When a category is deleted, nullify category_id on all affected products
    (across all product types: book, electronics, fashion)."""
    from app.models import Product
    category_id = data.get('category_id')
    if not category_id:
        return
    count = Product.objects.filter(category_id=category_id).update(category_id=None)
    logger.info("Cleared category_id=%s from %d products", category_id, count)


BINDINGS = [
    ('category.deleted', handle_category_deleted),
]
