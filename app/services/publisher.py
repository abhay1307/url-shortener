import json
import threading

import pika

from app.config import settings

_lock = threading.Lock()


def publish_click(
    short_code: str,
    ip_address: str = "",
    referrer: str = "",
    user_agent: str = "",
) -> None:
    """
    Publish a click event to RabbitMQ asynchronously.
    Runs in a background thread so the redirect response is never delayed.
    Fails silently — a missed click event is preferable to a failed redirect.
    """

    def _publish():
        try:
            with _lock:
                conn = pika.BlockingConnection(
                    pika.URLParameters(settings.rabbitmq_url)
                )
                ch = conn.channel()
                ch.queue_declare(queue="clicks", durable=True)
                ch.basic_publish(
                    exchange="",
                    routing_key="clicks",
                    body=json.dumps(
                        {
                            "short_code": short_code,
                            "ip_address": ip_address,
                            "referrer": referrer,
                            "user_agent": user_agent,
                        }
                    ),
                    properties=pika.BasicProperties(delivery_mode=2),
                )
                conn.close()
        except Exception as e:
            print(f"[Publisher] Failed to publish click for {short_code}: {e}")

    thread = threading.Thread(target=_publish, daemon=True)
    thread.start()
