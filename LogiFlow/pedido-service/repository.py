from shared.config import get_settings
from shared.enums import EstadoPedido, TipoEntrega
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import models
import schemas
import factory
import sys
import json
import pika
import httpx

sys.path.append('..')

settings = get_settings()


class PedidoRepository:
    """Repository pattern for pedido operations"""

    def __init__(self, db: Session):
        self.db = db

    def _generar_codigo_pedido(self) -> str:
        """Genera código único para pedido (P-00001, P-00002, ...)"""
        ultimo_pedido = self.db.query(models.Pedido).order_by(
            models.Pedido.id.desc()).first()

        if not ultimo_pedido:
            numero = 1
        else:
            # Extraer número del último código
            ultimo_codigo = ultimo_pedido.codigo
            numero = int(ultimo_codigo.split('-')[1]) + 1

        return f"P-{numero:05d}"

    def create_pedido(self,
                      pedido_data: schemas.PedidoCreate) -> models.Pedido:
        """
        Crea un nuevo pedido - Transacción ACID

        Valida el tipo de entrega y peso usando Factory Pattern
        """
        # Validar pedido usando Factory
        valido, mensaje_error = factory.EntregaFactory.validar_pedido(
            pedido_data.tipo_entrega, pedido_data.peso_kg)

        if not valido:
            raise ValueError(mensaje_error)

        # Generar código único
        codigo = self._generar_codigo_pedido()

        # Crear pedido
        db_pedido = models.Pedido(
            codigo=codigo,
            cliente_id=pedido_data.cliente_id,
            origen_direccion=pedido_data.origen_direccion,
            origen_lat=pedido_data.origen_lat,
            origen_lon=pedido_data.origen_lon,
            destino_direccion=pedido_data.destino_direccion,
            destino_lat=pedido_data.destino_lat,
            destino_lon=pedido_data.destino_lon,
            zona_id=pedido_data.zona_id,
            tipo_entrega=pedido_data.tipo_entrega.value,
            estado=EstadoPedido.RECIBIDO.value,
            descripcion=pedido_data.descripcion,
            peso_kg=pedido_data.peso_kg,
            dimensiones=pedido_data.dimensiones,
            valor_declarado=pedido_data.valor_declarado,
            contacto_nombre=pedido_data.contacto_nombre,
            contacto_telefono=pedido_data.contacto_telefono,
            notas=pedido_data.notas)

        self.db.add(db_pedido)
        self.db.commit()
        self.db.refresh(db_pedido)

        # Publicar evento de pedido creado
        payload = {
            "type": "pedido.creado",
            "data": {
                "pedido_id": db_pedido.id,
                "codigo": db_pedido.codigo,
                "cliente_id": db_pedido.cliente_id,
                "zona_id": db_pedido.zona_id,
                "estado": db_pedido.estado,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
        try:
            params = pika.URLParameters(settings.rabbitmq_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange="logiflow.events",
                                     exchange_type="topic",
                                     durable=True)
            channel.basic_publish(
                exchange="logiflow.events",
                routing_key="pedido.creado",
                body=json.dumps(payload).encode(),
                properties=pika.BasicProperties(delivery_mode=2),
            )
            connection.close()
        except Exception:
            # Fallback a publicar vía HTTP al realtime-service
            try:
                url = f"{settings.ws_service_url}/api/ws/publish"
                with httpx.Client(timeout=2.0) as client:
                    client.post(url, json=payload)
            except Exception:
                pass

        return db_pedido

    def get_pedido_by_id(self, pedido_id: int) -> Optional[models.Pedido]:
        """Obtiene pedido por ID"""
        return self.db.query(
            models.Pedido).filter(models.Pedido.id == pedido_id).first()

    def get_pedido_by_codigo(self, codigo: str) -> Optional[models.Pedido]:
        """Obtiene pedido por código"""
        return self.db.query(
            models.Pedido).filter(models.Pedido.codigo == codigo).first()

    def get_pedidos(
        self,
        skip: int = 0,
        limit: int = 100,
        estado: Optional[EstadoPedido] = None,
        cliente_id: Optional[int] = None,
        repartidor_id: Optional[int] = None
    ) -> tuple[List[models.Pedido], int]:
        """
        Obtiene lista de pedidos con filtros opcionales

        Returns:
            (lista_pedidos, total_count)
        """
        query = self.db.query(models.Pedido)

        if estado:
            query = query.filter(models.Pedido.estado == estado.value)

        if cliente_id:
            query = query.filter(models.Pedido.cliente_id == cliente_id)

        if repartidor_id:
            query = query.filter(models.Pedido.repartidor_id == repartidor_id)

        total = query.count()
        pedidos = query.order_by(
            models.Pedido.created_at.desc()).offset(skip).limit(limit).all()

        return pedidos, total

    def update_pedido(
            self, pedido_id: int,
            update_data: schemas.PedidoUpdate) -> Optional[models.Pedido]:
        """
        Actualiza pedido (PATCH) - Transacción ACID

        Actualiza solo los campos proporcionados
        """
        db_pedido = self.get_pedido_by_id(pedido_id)

        if not db_pedido:
            return None

        # Actualizar campos proporcionados
        update_dict = update_data.model_dump(exclude_unset=True)

        estado_cambiado = False
        for field, value in update_dict.items():
            if field == "estado":
                # Actualizar timestamps según estado
                if value == EstadoPedido.ASIGNADO:
                    db_pedido.asignado_at = datetime.utcnow()
                elif value == EstadoPedido.EN_RUTA:
                    db_pedido.en_ruta_at = datetime.utcnow()
                elif value == EstadoPedido.ENTREGADO:
                    db_pedido.entregado_at = datetime.utcnow()
                estado_cambiado = True
                setattr(db_pedido, field, value.value)
            else:
                setattr(db_pedido, field, value)

        db_pedido.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(db_pedido)

        # Publicar evento de cambio de estado en RabbitMQ
        if estado_cambiado:
            payload = {
                "type": "pedido.estado.actualizado",
                "data": {
                    "pedido_id": db_pedido.id,
                    "codigo": db_pedido.codigo,
                    "estado": db_pedido.estado,
                    "zona_id": db_pedido.zona_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            }
            try:
                params = pika.URLParameters(settings.rabbitmq_url)
                connection = pika.BlockingConnection(params)
                channel = connection.channel()
                channel.exchange_declare(exchange="logiflow.events",
                                         exchange_type="topic",
                                         durable=True)
                channel.basic_publish(
                    exchange="logiflow.events",
                    routing_key="pedido.estado.actualizado",
                    body=json.dumps(payload).encode(),
                    properties=pika.BasicProperties(delivery_mode=2),
                )
                connection.close()
            except Exception:
                # Fallback a publicar vía REST al realtime-service
                try:
                    url = f"{settings.ws_service_url}/api/ws/publish"
                    with httpx.Client(timeout=2.0) as client:
                        client.post(url, json=payload)
                except Exception:
                    pass

        return db_pedido

    def cancelar_pedido(
            self, pedido_id: int,
            cancelacion: schemas.PedidoCancelacion) -> Optional[models.Pedido]:
        """
        Cancela un pedido (cancelación lógica) - Transacción ACID
        """
        db_pedido = self.get_pedido_by_id(pedido_id)

        if not db_pedido:
            return None

        # Validar que el pedido pueda ser cancelado
        if db_pedido.estado == EstadoPedido.ENTREGADO.value:
            raise ValueError("No se puede cancelar un pedido ya entregado")

        if db_pedido.estado == EstadoPedido.CANCELADO.value:
            raise ValueError("El pedido ya está cancelado")

        # Cancelar pedido
        db_pedido.estado = EstadoPedido.CANCELADO.value
        db_pedido.motivo_cancelacion = cancelacion.motivo_cancelacion
        db_pedido.cancelado_por = cancelacion.cancelado_por
        db_pedido.cancelado_at = datetime.utcnow()
        db_pedido.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(db_pedido)

        return db_pedido

    def delete_pedido_fisico(self, pedido_id: int) -> bool:
        """
        Elimina un pedido físicamente de la base de datos

        Returns:
            True si se eliminó correctamente, False si no se encontró
        """
        db_pedido = self.get_pedido_by_id(pedido_id)

        if not db_pedido:
            return False

        self.db.delete(db_pedido)
        self.db.commit()

        return True
