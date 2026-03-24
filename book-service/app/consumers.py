import logging

logger = logging.getLogger(__name__)


def handle_category_deleted(data):
    """When a category is deleted, nullify category_id on affected books."""
    from app.models import Book
    category_id = data.get('category_id')
    if not category_id:
        return
    count = Book.objects.filter(category_id=category_id).update(category_id=None)
    logger.info("Cleared category_id=%s from %d books", category_id, count)


BINDINGS = [
    ('category.deleted', handle_category_deleted),
]
