import json
import logging
import threading
import time
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


def start_consumer(service_name, bindings):
    """
    Start a blocking consumer in a background daemon thread.

    bindings: list of (routing_key, callback_function) tuples
    callback_function signature: def handler(data: dict) -> None
    """
    def _run():
        while True:
            try:
                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=RABBITMQ_HOST,
                        connection_attempts=5,
                        retry_delay=5,
                        heartbeat=600,
                        blocked_connection_timeout=300,
                    )
                )
                channel = connection.channel()
                channel.exchange_declare(exchange=EXCHANGE, exchange_type='topic', durable=True)
                channel.basic_qos(prefetch_count=1)

                for routing_key, handler in bindings:
                    queue_name = f"{service_name}.{routing_key}"
                    channel.queue_declare(queue=queue_name, durable=True)
                    channel.queue_bind(exchange=EXCHANGE, queue=queue_name, routing_key=routing_key)

                    def make_callback(h):
                        def callback(ch, method, properties, body):
                            try:
                                data = json.loads(body)
                                logger.info("Received %s: %s", method.routing_key, data)
                                h(data)
                                ch.basic_ack(delivery_tag=method.delivery_tag)
                            except Exception as e:
                                logger.error("Error handling %s: %s", method.routing_key, e)
                                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                        return callback

                    channel.basic_consume(queue=queue_name, on_message_callback=make_callback(handler))

                logger.info("[%s] Consumer started, waiting for messages...", service_name)
                channel.start_consuming()

            except pika.exceptions.AMQPConnectionError as e:
                logger.error("[%s] RabbitMQ connection lost: %s. Retrying in 5s...", service_name, e)
                time.sleep(5)
            except Exception as e:
                logger.error("[%s] Consumer error: %s. Retrying in 5s...", service_name, e)
                time.sleep(5)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    logger.info("[%s] Consumer thread started", service_name)
