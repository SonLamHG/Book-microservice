import logging

logger = logging.getLogger(__name__)


def handle_payment_completed(data):
    """When payment is completed, update order status to PAID."""
    from app.models import Order
    order_id = data.get('order_id')
    if not order_id:
        return
    try:
        order = Order.objects.get(pk=order_id)
        if order.status in ('CONFIRMED', 'PENDING'):
            order.status = 'PAID'
            order.save()
            logger.info("Order #%s status updated to PAID", order_id)
    except Order.DoesNotExist:
        logger.warning("Order #%s not found for payment.completed", order_id)


def handle_shipment_shipped(data):
    """When shipment is shipped, update order status to SHIPPING."""
    from app.models import Order
    order_id = data.get('order_id')
    if not order_id:
        return
    try:
        order = Order.objects.get(pk=order_id)
        if order.status in ('CONFIRMED', 'PAID'):
            order.status = 'SHIPPING'
            order.save()
            logger.info("Order #%s status updated to SHIPPING", order_id)
    except Order.DoesNotExist:
        logger.warning("Order #%s not found for shipment.shipped", order_id)


BINDINGS = [
    ('payment.completed', handle_payment_completed),
    ('shipment.shipped', handle_shipment_shipped),
]
