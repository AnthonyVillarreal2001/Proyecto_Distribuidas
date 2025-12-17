from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import sys

sys.path.append('..')
from shared.enums import TipoEntrega, EstadoFactura


class TarifaCalculoRequest(BaseModel):
    """Schema para calcular tarifa"""
    tipo_entrega: TipoEntrega
    peso_kg: float = Field(..., gt=0)
    distancia_km: float = Field(..., gt=0)


class TarifaCalculoResponse(BaseModel):
    """Schema de respuesta de cálculo de tarifa"""
    tipo_entrega: str
    peso_kg: float
    distancia_km: float
    tarifa_base: float
    costo_peso: float
    costo_distancia: float
    subtotal: float
    impuestos: float
    total: float
    tiempo_estimado_horas: float


class FacturaCreate(BaseModel):
    """Schema para crear factura"""
    pedido_id: int
    cliente_id: int
    distancia_km: float = Field(..., gt=0)
    peso_kg: float = Field(..., gt=0)
    tipo_entrega: TipoEntrega
    notas: Optional[str] = None


class FacturaUpdate(BaseModel):
    """Schema para actualizar factura"""
    estado: Optional[EstadoFactura] = None
    metodo_pago: Optional[str] = None
    notas: Optional[str] = None


class FacturaResponse(BaseModel):
    """Schema de respuesta de factura"""
    id: int
    numero_factura: str
    pedido_id: int
    cliente_id: int
    distancia_km: float
    peso_kg: float
    tipo_entrega: str
    tarifa_base: float
    costo_peso: float
    costo_distancia: float
    subtotal: float
    impuestos: float
    total: float
    estado: str
    metodo_pago: Optional[str]
    notas: Optional[str]
    created_at: datetime
    emitida_at: Optional[datetime]
    pagada_at: Optional[datetime]
    anulada_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


class FacturaListResponse(BaseModel):
    """Schema de lista de facturas"""
    total: int
    facturas: list[FacturaResponse]
