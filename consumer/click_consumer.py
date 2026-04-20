"""
Click Consumer — runs as a separate Docker service.
Reads click events from RabbitMQ and persists them to PostgreSQL.
"""
import json
import sys
import time
from pathlib import Path

# Allow imports from project root
sys.path.append(str(Path(__file__).parent.parent))

import pika
from user_agents import parse as parse_ua

from app.config import settings
from app.database import SessionLocal, create_tables
from app.models import Click


def detect_device(user_agent_string: str) -> str:
    if not user_agent_string:
        return "unknown"
    ua = parse_ua(user_agent_string)
    if ua.is_mobile:
        return "mobile"
    if ua.is_tablet:
        return "tablet"
    if ua.is_bot:
        return "bot"
    return "desktop"


def on_message(channel, method, properties, body):
    try:
        data = json.loads(body)
        code = data.get("short_code", "")
        ua_string = data.get("user_agent", "")
        device = detect_device(ua_string)

        db = SessionLocal()
        try:
            click = Click(
                short_code=code,
                ip_address=data.get("ip_address", ""),
                referrer=data.get("referrer", ""),
                user_agent=ua_string,
                device_type=device,
            )
            db.add(click)
            db.commit()
            print(f"[Consumer] Saved click → {code} | device={device}")
        finally:
            db.close()

        channel.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"[Consumer] Error processing message: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_consumer(max_retries: int = 20):
    create_tables()
    retries = 0

    while retries < max_retries:
        try:
            print(f"[Consumer] Connecting to RabbitMQ... (attempt {retries + 1})")
            conn = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
            channel = conn.channel()
            channel.queue_declare(queue="clicks", durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue="clicks", on_message_callback=on_message)
            print("[Consumer] Ready. Waiting for click events...")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError:
            retries += 1
            wait = min(2 ** retries, 30)
            print(f"[Consumer] RabbitMQ not ready. Retrying in {wait}s...")
            time.sleep(wait)

        except KeyboardInterrupt:
            print("[Consumer] Shutting down.")
            break

        except Exception as e:
            print(f"[Consumer] Unexpected error: {e}")
            retries += 1
            time.sleep(5)


if __name__ == "__main__":
    start_consumer()
