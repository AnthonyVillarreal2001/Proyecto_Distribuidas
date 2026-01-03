from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set, DefaultDict
import asyncio
import httpx
import sys
import json
import threading
import pika

sys.path.append('..')
from shared.config import get_settings

settings = get_settings()

app = FastAPI(
    title="LogiFlow - RealtimeService",
    description="Servicio de WebSockets para tracking en tiempo real",
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

# Connected clients by user_id (or a generic channel)
connections: Set[WebSocket] = set()
# Suscripciones por tópico
topic_subscribers: DefaultDict[str, Set[WebSocket]] = DefaultDict(set)


async def verify_token_with_auth(token: str) -> Dict:
    """Verify JWT via AuthService /api/auth/verify"""
    url = f"{settings.auth_service_url}/api/auth/verify"
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(url, params={"token": token})
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid or expired token")
        return resp.json()


@app.get("/")
async def health():
    return {"service": "RealtimeService", "status": "running"}


@app.websocket("/api/ws/track")
async def websocket_endpoint(ws: WebSocket):
    # Expect Authorization header: Bearer <token>
    auth_header = ws.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    token = auth_header.split(" ", 1)[1]

    try:
        token_info = await verify_token_with_auth(token)
    except HTTPException:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws.accept()
    connections.add(ws)
    # Suscribir a tópico inicial si se envía en query param
    initial_topic = ws.query_params.get("topic") or "realtime.location"
    topic_subscribers[initial_topic].add(ws)
    print(f"[RealtimeService] Cliente conectado y suscrito a {initial_topic}")

    try:
        # Send a welcome message with token info
        await ws.send_json({"type": "welcome", "data": token_info})
        while True:
            # Keep the socket alive; clients may send pings or subscription messages
            msg_text = await ws.receive_text()
            try:
                msg = json.loads(msg_text)
            except Exception:
                msg = {"type": "echo", "data": msg_text}
            # Manejo de suscripciones
            if isinstance(msg, dict) and msg.get("type") == "subscribe":
                topic = msg.get("topic") or "realtime.location"
                # Limpiar suscripciones previas y añadir nueva
                for t, subs in list(topic_subscribers.items()):
                    if ws in subs and t != topic:
                        subs.discard(ws)
                topic_subscribers[topic].add(ws)
                await ws.send_json({"type": "subscribed", "topic": topic})
                print(f"[RealtimeService] Cliente suscrito a {topic}")
            else:
                # Echo simple
                await ws.send_json(msg)
    except WebSocketDisconnect:
        connections.discard(ws)
        for subs in topic_subscribers.values():
            subs.discard(ws)
        print("[RealtimeService] Cliente desconectado")
    except Exception:
        connections.discard(ws)
        for subs in topic_subscribers.values():
            subs.discard(ws)
        await ws.close()


@app.post("/api/ws/publish")
async def publish_event(event: Dict):
    """Broadcast an event to all connected clients.
    Expected payload: {"type": "location_update", "data": {...}}
    """
    topic = event.get("type", "realtime.location")
    subs = topic_subscribers.get(topic, set())
    dead: Set[WebSocket] = set()
    for ws in list(subs):
        try:
            await ws.send_json(event)
        except Exception:
            dead.add(ws)
    for ws in dead:
        subs.discard(ws)
        connections.discard(ws)
    return {"topic": topic, "delivered": len(subs)}


def _rabbit_consumer():
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.exchange_declare(exchange="logiflow.events",
                             exchange_type="topic",
                             durable=True)
    result = channel.queue_declare(queue="realtime.broadcast", durable=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange="logiflow.events",
                       queue=queue_name,
                       routing_key="realtime.*")

    def callback(ch, method, properties, body):
        try:
            event = json.loads(body)
        except Exception:
            event = {"type": "raw", "data": body.decode(errors="ignore")}
        topic = method.routing_key or event.get("type", "realtime.location")
        subs = topic_subscribers.get(topic, set())
        dead = set()
        for ws in list(subs):
            try:
                asyncio.get_event_loop().create_task(ws.send_json(event))
            except Exception:
                dead.add(ws)
        for ws in dead:
            subs.discard(ws)
            connections.discard(ws)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=queue_name,
                          on_message_callback=callback,
                          auto_ack=False)
    channel.start_consuming()


@app.on_event("startup")
async def start_rabbit():
    thread = threading.Thread(target=_rabbit_consumer, daemon=True)
    thread.start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5005)
