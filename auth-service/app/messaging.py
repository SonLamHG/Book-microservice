import json
import logging
import pika

logger = logging.getLogger(__name__)

RABBITMQ_HOST = 'rabbitmq'
EXCHANGE = 'bookstore'


def publish_event(event_type, data):
    """Publish an event to the bookstore exchange."""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, connection_attempts=3, retry_delay=1)
        )
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE, exchange_type='topic', durable=True)
        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=event_type,
            body=json.dumps(data),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()
        logger.info("Published event: %s", event_type)
    except Exception as e:
        logger.error("Failed to publish event %s: %s", event_type, e)
