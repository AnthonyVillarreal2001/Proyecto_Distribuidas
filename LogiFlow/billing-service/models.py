from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
import sys

sys.path.append('..')
from shared.database import Base


class Factura(Base):
    """Modelo de factura"""
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, index=True)
    numero_factura = Column(String, unique=True, index=True,
                            nullable=False)  # F-00001
    pedido_id = Column(Integer, nullable=False)
    cliente_id = Column(Integer, nullable=False)

    # Cálculo de tarifas
    distancia_km = Column(Float, nullable=False)
    peso_kg = Column(Float, nullable=False)
    tipo_entrega = Column(String, nullable=False)

    # Desglose de costos
    tarifa_base = Column(Float, nullable=False)
    costo_peso = Column(Float, nullable=False)
    costo_distancia = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    impuestos = Column(Float, nullable=False)
    total = Column(Float, nullable=False)

    # Estado
    estado = Column(String, nullable=False,
                    default="BORRADOR")  # BORRADOR, EMITIDA, PAGADA, ANULADA

    # Información adicional
    metodo_pago = Column(String, nullable=True)
    notas = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    emitida_at = Column(DateTime, nullable=True)
    pagada_at = Column(DateTime, nullable=True)
    anulada_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime,
                        default=datetime.utcnow,
                        onupdate=datetime.utcnow)
