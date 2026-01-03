from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import models
import schemas
import vehiculo_hierarchy
import sys
import httpx
import pika
import json

sys.path.append('..')
from shared.enums import EstadoRepartidor, TipoVehiculo
from shared.config import get_settings

settings = get_settings()


class FleetRepository:
    """Repository pattern for fleet operations"""

    def __init__(self, db: Session):
        self.db = db

    # ========== REPARTIDORES ==========

    def create_repartidor(
            self,
            repartidor_data: schemas.RepartidorCreate) -> models.Repartidor:
        """Crea un nuevo repartidor - Transacción ACID"""
        # Verificar que user_id no esté duplicado
        existing = self.db.query(models.Repartidor).filter(
            models.Repartidor.user_id == repartidor_data.user_id).first()

        if existing:
            raise ValueError(
                f"Ya existe un repartidor con user_id {repartidor_data.user_id}"
            )

        # Verificar email único
        existing_email = self.db.query(models.Repartidor).filter(
            models.Repartidor.email == repartidor_data.email).first()

        if existing_email:
            raise ValueError(
                f"Ya existe un repartidor con email {repartidor_data.email}")

        db_repartidor = models.Repartidor(
            user_id=repartidor_data.user_id,
            nombre_completo=repartidor_data.nombre_completo,
            telefono=repartidor_data.telefono,
            email=repartidor_data.email,
            licencia_conducir=repartidor_data.licencia_conducir,
            zona_id=repartidor_data.zona_id,
            estado=EstadoRepartidor.DISPONIBLE.value)

        self.db.add(db_repartidor)
        self.db.commit()
        self.db.refresh(db_repartidor)

        return db_repartidor

    def get_repartidor_by_id(
            self, repartidor_id: int) -> Optional[models.Repartidor]:
        """Obtiene repartidor por ID"""
        return self.db.query(models.Repartidor).filter(
            models.Repartidor.id == repartidor_id).first()

    def get_repartidores(
            self,
            skip: int = 0,
            limit: int = 100,
            estado: Optional[EstadoRepartidor] = None,
            zona_id: Optional[str] = None
    ) -> tuple[List[models.Repartidor], int]:
        """Obtiene lista de repartidores con filtros"""
        query = self.db.query(models.Repartidor)

        if estado:
            query = query.filter(models.Repartidor.estado == estado.value)

        if zona_id:
            query = query.filter(models.Repartidor.zona_id == zona_id)

        total = query.count()
        repartidores = query.order_by(
            models.Repartidor.created_at.desc()).offset(skip).limit(
                limit).all()

        return repartidores, total

    def update_repartidor(
            self, repartidor_id: int, update_data: schemas.RepartidorUpdate
    ) -> Optional[models.Repartidor]:
        """Actualiza repartidor - Transacción ACID"""
        db_repartidor = self.get_repartidor_by_id(repartidor_id)

        if not db_repartidor:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            if field == "estado":
                setattr(db_repartidor, field, value.value)
            else:
                setattr(db_repartidor, field, value)

        # Actualizar timestamp de GPS si se actualizó ubicación
        if "ubicacion_lat" in update_dict or "ubicacion_lon" in update_dict:
            db_repartidor.ultima_actualizacion_gps = datetime.utcnow()

            # Publish location update to RabbitMQ (best-effort)
            payload = {
                "type": "location_update",
                "data": {
                    "repartidor_id":
                    repartidor_id,
                    "ubicacion_lat":
                    update_dict.get("ubicacion_lat",
                                    db_repartidor.ubicacion_lat),
                    "ubicacion_lon":
                    update_dict.get("ubicacion_lon",
                                    db_repartidor.ubicacion_lon),
                    "timestamp":
                    datetime.utcnow().isoformat(),
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
                    routing_key="realtime.location",
                    body=json.dumps(payload).encode(),
                    properties=pika.BasicProperties(delivery_mode=2),
                )
                connection.close()
            except Exception:
                # Fallback to HTTP publish if RabbitMQ unavailable
                try:
                    url = f"{settings.ws_service_url}/api/ws/publish"
                    with httpx.Client(timeout=2.0) as client:
                        client.post(url, json=payload)
                except Exception:
                    pass

        db_repartidor.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(db_repartidor)

        return db_repartidor

    def delete_repartidor_fisico(self, repartidor_id: int) -> bool:
        """
        Inactiva un repartidor (soft delete) para evitar errores de llave foránea.
        Ajusta `is_active=False` y `estado=INACTIVO`.
        """
        db_repartidor = self.get_repartidor_by_id(repartidor_id)

        if not db_repartidor:
            return False

        db_repartidor.is_active = False
        db_repartidor.estado = EstadoRepartidor.INACTIVO.value
        db_repartidor.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    # ========== VEHÍCULOS ==========

    def create_vehiculo(
            self, vehiculo_data: schemas.VehiculoCreate) -> models.Vehiculo:
        """Crea un nuevo vehículo - Transacción ACID"""
        # Verificar que el repartidor existe
        repartidor = self.get_repartidor_by_id(vehiculo_data.repartidor_id)

        if not repartidor:
            raise ValueError(
                f"Repartidor {vehiculo_data.repartidor_id} no encontrado")

        # Verificar placa única
        existing = self.db.query(models.Vehiculo).filter(
            models.Vehiculo.placa == vehiculo_data.placa).first()

        if existing:
            raise ValueError(
                f"Ya existe un vehículo con placa {vehiculo_data.placa}")

        # Usar Factory para validar capacidades
        try:
            vehiculo_obj = vehiculo_hierarchy.VehiculoFactory.crear_vehiculo(
                vehiculo_data.tipo, vehiculo_data.placa, vehiculo_data.marca,
                vehiculo_data.modelo, vehiculo_data.año)

            # La capacidad del vehículo debe ser coherente con el tipo
            capacidad_esperada = vehiculo_obj.capacidad_maxima_kg

        except ValueError as e:
            raise ValueError(f"Error al validar vehículo: {str(e)}")

        db_vehiculo = models.Vehiculo(
            repartidor_id=vehiculo_data.repartidor_id,
            tipo=vehiculo_data.tipo.value,
            placa=vehiculo_data.placa,
            marca=vehiculo_data.marca,
            modelo=vehiculo_data.modelo,
            año=vehiculo_data.año,
            color=vehiculo_data.color,
            capacidad_peso_kg=vehiculo_data.capacidad_peso_kg,
            capacidad_volumen_m3=vehiculo_data.capacidad_volumen_m3,
            soat_vencimiento=vehiculo_data.soat_vencimiento,
            revision_tecnica_vencimiento=vehiculo_data.
            revision_tecnica_vencimiento)

        self.db.add(db_vehiculo)
        self.db.commit()
        self.db.refresh(db_vehiculo)

        return db_vehiculo

    def get_vehiculo_by_id(self,
                           vehiculo_id: int) -> Optional[models.Vehiculo]:
        """Obtiene vehículo por ID"""
        return self.db.query(
            models.Vehiculo).filter(models.Vehiculo.id == vehiculo_id).first()

    def get_vehiculos(
        self,
        skip: int = 0,
        limit: int = 100,
        tipo: Optional[TipoVehiculo] = None,
        repartidor_id: Optional[int] = None
    ) -> tuple[List[models.Vehiculo], int]:
        """Obtiene lista de vehículos con filtros"""
        query = self.db.query(models.Vehiculo)

        if tipo:
            query = query.filter(models.Vehiculo.tipo == tipo.value)

        if repartidor_id:
            query = query.filter(
                models.Vehiculo.repartidor_id == repartidor_id)

        total = query.count()
        vehiculos = query.order_by(
            models.Vehiculo.created_at.desc()).offset(skip).limit(limit).all()

        return vehiculos, total

    def update_vehiculo(
            self, vehiculo_id: int,
            update_data: schemas.VehiculoUpdate) -> Optional[models.Vehiculo]:
        """Actualiza vehículo - Transacción ACID"""
        db_vehiculo = self.get_vehiculo_by_id(vehiculo_id)

        if not db_vehiculo:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(db_vehiculo, field, value)

        db_vehiculo.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(db_vehiculo)

        return db_vehiculo

    def delete_vehiculo_fisico(self, vehiculo_id: int) -> bool:
        """
        Inactiva un vehículo (soft delete) usando `estado=INACTIVO`.
        """
        db_vehiculo = self.get_vehiculo_by_id(vehiculo_id)

        if not db_vehiculo:
            return False

        db_vehiculo.estado = "INACTIVO"
        db_vehiculo.updated_at = datetime.utcnow()
        self.db.commit()
        return True
