import pika
import json
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Click 

def callback(ch, method, properties, body):
    data = json.loads(body)
    db : Session = SessionLocal()

    click = Click(short_code=data["code"])
    db.add(click)
    db.commit()
    db.close()

    print("Click Saved")

connection= pika.BlockingConnection(
    pika.ConnectionParamets(host="rabbitmq")
)

channel = connection.channel()
channel.queue_declare(queue='clicks', durable=True)

channel.basic_consume(queue='clicks', on_message_callback=callback, auto_ack=True)

print("Waiting for messages...")
channel.start_consuming()