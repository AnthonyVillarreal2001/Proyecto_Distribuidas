from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from datetime import datetime
import sys

sys.path.append('..')
from shared.database import Base


class Pedido(Base):
    """Modelo de pedido"""
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True, nullable=False)  # P-00001
    cliente_id = Column(Integer, nullable=False)
    repartidor_id = Column(Integer, nullable=True)

    # Información de origen y destino
    origen_direccion = Column(String, nullable=False)
    origen_lat = Column(Float, nullable=True)
    origen_lon = Column(Float, nullable=True)
    destino_direccion = Column(String, nullable=False)
    destino_lat = Column(Float, nullable=True)
    destino_lon = Column(Float, nullable=True)
    zona_id = Column(String, nullable=True)

    # Tipo de entrega y estado
    tipo_entrega = Column(
        String, nullable=False)  # URBANA_RAPIDA, INTERMUNICIPAL, NACIONAL
    estado = Column(String, nullable=False, default="RECIBIDO"
                    )  # RECIBIDO, ASIGNADO, EN_RUTA, ENTREGADO, CANCELADO

    # Información del paquete
    descripcion = Column(String, nullable=False)
    peso_kg = Column(Float, nullable=False)
    dimensiones = Column(String, nullable=True)  # "30x20x10 cm"
    valor_declarado = Column(Float, nullable=True)

    # Información de contacto
    contacto_nombre = Column(String, nullable=False)
    contacto_telefono = Column(String, nullable=False)

    # Notas y observaciones
    notas = Column(String, nullable=True)
    notas_entrega = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    asignado_at = Column(DateTime, nullable=True)
    en_ruta_at = Column(DateTime, nullable=True)
    entregado_at = Column(DateTime, nullable=True)
    cancelado_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime,
                        default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Cancelación
    motivo_cancelacion = Column(String, nullable=True)
    cancelado_por = Column(Integer, nullable=True)
