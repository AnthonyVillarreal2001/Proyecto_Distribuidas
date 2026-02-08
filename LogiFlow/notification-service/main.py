from models import Notification, Base
from shared.database import wait_for_database
from shared.database import SessionLocal, engine
from shared.config import get_settings
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
import threading
import pika
import json
import sys
import time
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

sys.path.append('..')

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

    # Retry loop to avoid crashing if RabbitMQ is not ready yet
    while True:
        try:
            connection = pika.BlockingConnection(params)
            break
        except Exception:
            print("[NotificationService] RabbitMQ no disponible, reintentando en 2s...")
            time.sleep(2)

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
    channel.queue_bind(exchange="logiflow.events",
                       queue=queue_name,
                       routing_key="pedido.creado")

    def callback(ch, method, properties, body):
        try:
            event = json.loads(body)
        except Exception:
            event = {"raw": body.decode(errors="ignore")}
        # Guardar en base de datos
        try:
            db: Session = SessionLocal()
            notif = Notification(event_type=event.get("type", "unknown"),
                                 routing_key=method.routing_key,
                                 payload=event)
            db.add(notif)
            db.commit()
            print("[NotificationService] Evento guardado:", notif.event_type)
        except Exception as e:
            print("[NotificationService] Error guardando notificación:", e)
        finally:
            try:
                db.close()
            except Exception:
                pass
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=queue_name,
                          on_message_callback=callback,
                          auto_ack=False)
    channel.start_consuming()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_type: str
    routing_key: Optional[str]
    payload: dict
    created_at: datetime


@app.get("/api/notifications", response_model=List[NotificationOut])
def list_notifications(limit: int = Query(50, ge=1, le=200),
                       offset: int = Query(0, ge=0),
                       event_type: Optional[str] = None,
                       routing_key: Optional[str] = None,
                       db: Session = Depends(get_db)):
    query = db.query(Notification)
    if event_type:
        query = query.filter(Notification.event_type == event_type)
    if routing_key:
        query = query.filter(Notification.routing_key == routing_key)
    return query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()


@app.get("/api/notifications/categories/{category}", response_model=List[NotificationOut])
def list_notifications_by_category(category: str,
                                   limit: int = Query(50, ge=1, le=200),
                                   offset: int = Query(0, ge=0),
                                   db: Session = Depends(get_db)):
    # category se alinea con el prefijo del routing_key (ej. "pedido", "realtime")
    pattern = f"{category}.%"
    query = db.query(Notification).filter(
        Notification.routing_key.ilike(pattern))
    return query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()


@app.on_event("startup")
async def start_consumer():
    # Asegurar que la tabla existe
    wait_for_database()
    Base.metadata.create_all(bind=engine)
    thread = threading.Thread(target=_rabbit_consumer, daemon=True)
    thread.start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5007)
