from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading
import pika
import json
import sys

sys.path.append('..')
from shared.config import get_settings

settings = get_settings()

app = FastAPI(title="LogiFlow - NotificationService",
              description="Consumidor de eventos para notificaciones",
              version="1.0.0",
              docs_url="/docs",
              redoc_url="/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health():
    return {"service": "NotificationService", "status": "running"}


def _rabbit_consumer():
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.exchange_declare(exchange="logiflow.events",
                             exchange_type="topic",
                             durable=True)
    # Cola para eventos de pedido
    result = channel.queue_declare(queue="notification.pedido", durable=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange="logiflow.events",
                       queue=queue_name,
                       routing_key="pedido.estado.*")

    def callback(ch, method, properties, body):
        try:
            event = json.loads(body)
        except Exception:
            event = {"raw": body.decode(errors="ignore")}
        # Simulación de envío de notificación (log)
        print("[NotificationService] Evento recibido:", event)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=queue_name,
                          on_message_callback=callback,
                          auto_ack=False)
    channel.start_consuming()


@app.on_event("startup")
async def start_consumer():
    thread = threading.Thread(target=_rabbit_consumer, daemon=True)
    thread.start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5007)
