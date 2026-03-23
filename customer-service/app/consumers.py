import logging

logger = logging.getLogger(__name__)


def handle_user_created(data):
    """Auto-create customer profile when a CUSTOMER user registers via auth-service."""
    from app.models import Customer
    from app.messaging import publish_event

    auth_user_id = data.get('user_id')
    if not auth_user_id:
        return
    # Idempotency: skip if profile already exists
    if Customer.objects.filter(auth_user_id=auth_user_id).exists():
        logger.info("Customer profile for auth_user_id=%s already exists", auth_user_id)
        return
    customer = Customer.objects.create(
        name=data.get('username', ''),
        email=data.get('email', ''),
        auth_user_id=auth_user_id,
    )
    logger.info("Created customer profile #%s for auth_user_id=%s", customer.id, auth_user_id)

    # Chain event: notify cart-service to auto-create cart
    publish_event('customer.created', {'customer_id': customer.id})


BINDINGS = [
    ('user.created.customer', handle_user_created),
]
