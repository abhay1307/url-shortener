"""
RabbitMQ publisher with a persistent connection.
Reuses one connection instead of opening a new one per click.
Falls back silently on failure — a missed analytics event is better than a failed redirect.
"""
import json
import threading
import time

import pika

from app.config import settings

_lock = threading.Lock()
_connection: pika.BlockingConnection | None = None
_channel: pika.adapters.blocking_connection.BlockingChannel | None = None


def _get_channel():
    global _connection, _channel
    try:
        if _channel and _channel.is_open:
            return _channel
        if _connection and not _connection.is_closed:
            _connection.close()
    except Exception:
        pass

    _connection = pika.BlockingConnection(
        pika.URLParameters(settings.rabbitmq_url)
    )
    _channel = _connection.channel()
    _channel.queue_declare(queue="clicks", durable=True)
    return _channel


def publish_click(
    short_code: str,
    ip_address: str = "",
    referrer: str = "",
    user_agent: str = "",
) -> None:
    """
    Publish click event asynchronously in a background thread.
    Uses a persistent channel — reconnects automatically if the connection drops.
    Never blocks or raises — redirect latency is never affected.
    """
    def _publish():
        with _lock:
            for attempt in range(3):
                try:
                    ch = _get_channel()
                    ch.basic_publish(
                        exchange="",
                        routing_key="clicks",
                        body=json.dumps({
                            "short_code": short_code,
                            "ip_address": ip_address,
                            "referrer": referrer,
                            "user_agent": user_agent,
                        }),
                        properties=pika.BasicProperties(delivery_mode=2),
                    )
                    return
                except Exception as e:
                    print(f"[Publisher] Attempt {attempt + 1} failed: {e}")
                    # Force reconnect on next call
                    global _channel, _connection
                    _channel = None
                    _connection = None
                    time.sleep(0.1 * (attempt + 1))

    thread = threading.Thread(target=_publish, daemon=True)
    thread.start()