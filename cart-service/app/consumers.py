import logging

logger = logging.getLogger(__name__)


def handle_customer_created(data):
    """Auto-create cart when a new customer is created."""
    from app.models import Cart

    customer_id = data.get('customer_id')
    if not customer_id:
        return
    # Idempotency: customer_id is unique in Cart model
    if Cart.objects.filter(customer_id=customer_id).exists():
        logger.info("Cart for customer_id=%s already exists", customer_id)
        return
    Cart.objects.create(customer_id=customer_id)
    logger.info("Created cart for customer_id=%s", customer_id)


BINDINGS = [
    ('customer.created', handle_customer_created),
]
