from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from datetime import datetime
import sys

sys.path.append('..')
from shared.database import Base


class Repartidor(Base):
    """Modelo de repartidor"""
    __tablename__ = "repartidores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True,
                     nullable=False)  # Referencia a usuario en AuthService
    nombre_completo = Column(String, nullable=False)
    telefono = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    licencia_conducir = Column(String, nullable=True)
    zona_id = Column(String, nullable=True)

    # Estado
    estado = Column(
        String, nullable=False,
        default="DISPONIBLE")  # DISPONIBLE, EN_RUTA, MANTENIMIENTO, INACTIVO

    # Ubicación actual
    ubicacion_lat = Column(Float, nullable=True)
    ubicacion_lon = Column(Float, nullable=True)
    ultima_actualizacion_gps = Column(DateTime, nullable=True)

    # Información laboral
    fecha_ingreso = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime,
                        default=datetime.utcnow,
                        onupdate=datetime.utcnow)


class Vehiculo(Base):
    """Modelo de vehículo"""
    __tablename__ = "vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    repartidor_id = Column(Integer,
                           ForeignKey("repartidores.id"),
                           nullable=False)

    # Tipo de vehículo
    tipo = Column(String,
                  nullable=False)  # MOTORIZADO, VEHICULO_LIVIANO, CAMION

    # Información del vehículo
    placa = Column(String, unique=True, nullable=False)
    marca = Column(String, nullable=False)
    modelo = Column(String, nullable=False)
    año = Column(Integer, nullable=False)
    color = Column(String, nullable=True)

    # Capacidad
    capacidad_peso_kg = Column(Float, nullable=False)
    capacidad_volumen_m3 = Column(Float, nullable=True)

    # Estado y mantenimiento
    estado = Column(String, nullable=False,
                    default="ACTIVO")  # ACTIVO, MANTENIMIENTO, INACTIVO
    ultimo_mantenimiento = Column(DateTime, nullable=True)
    proximo_mantenimiento = Column(DateTime, nullable=True)

    # Documentación
    soat_vencimiento = Column(DateTime, nullable=True)
    revision_tecnica_vencimiento = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime,
                        default=datetime.utcnow,
                        onupdate=datetime.utcnow)
