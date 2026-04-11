import pika
import json

def publish_click(code):
    connection = pika.BlockingConnection(
        pika.ConnectionParamets(host='rabbitmq')
    )
    channel = connection.channel()

    channel.queue_declare(queue='clicks', durable=True)

    message =json.dumps({"code" : code})

    channel.basic_publish(
        exchange='',
        routing_key='clicks',
        body=message
    )

    connection.close()