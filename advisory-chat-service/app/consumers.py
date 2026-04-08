"""
RabbitMQ event consumers for advisory-chat-service.
Listens to order and payment events to update customer behavior summaries.
"""
import logging

logger = logging.getLogger(__name__)


def handle_order_created(data):
    """When a new order is created, refresh customer behavior summary."""
    from .behavior_analyzer import analyze_customer_behavior

    customer_id = data.get('customer_id')
    if not customer_id:
        logger.warning("order.created event missing customer_id")
        return

    try:
        analyze_customer_behavior(int(customer_id))
        logger.info("Behavior updated for customer #%s after order.created", customer_id)
    except Exception as e:
        logger.error("Failed to update behavior for customer #%s: %s", customer_id, e)


def handle_payment_completed(data):
    """When payment is completed, refresh customer behavior summary."""
    from .behavior_analyzer import analyze_customer_behavior

    order_id = data.get('order_id')
    if not order_id:
        logger.warning("payment.completed event missing order_id")
        return

    # Fetch order to get customer_id
    import requests
    try:
        from django.conf import settings
        order_url = getattr(settings, 'ORDER_SERVICE_URL', 'http://order-service:8000')
        r = requests.get(f"{order_url}/orders/{order_id}/", timeout=5)
        if r.status_code == 200:
            customer_id = r.json().get('customer_id')
            if customer_id:
                analyze_customer_behavior(int(customer_id))
                logger.info("Behavior updated for customer #%s after payment.completed", customer_id)
    except requests.exceptions.RequestException as e:
        logger.error("Failed to fetch order #%s for behavior update: %s", order_id, e)


BINDINGS = [
    ('order.created', handle_order_created),
    ('payment.completed', handle_payment_completed),
]
