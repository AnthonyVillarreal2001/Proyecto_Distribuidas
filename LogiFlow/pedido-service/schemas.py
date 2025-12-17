from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import sys

sys.path.append('..')
from shared.enums import EstadoPedido, TipoEntrega


class PedidoCreate(BaseModel):
    """Schema para crear pedido"""
    cliente_id: int
    origen_direccion: str
    origen_lat: Optional[float] = None
    origen_lon: Optional[float] = None
    destino_direccion: str
    destino_lat: Optional[float] = None
    destino_lon: Optional[float] = None
    zona_id: Optional[str] = None
    tipo_entrega: TipoEntrega
    descripcion: str
    peso_kg: float = Field(..., gt=0)
    dimensiones: Optional[str] = None
    valor_declarado: Optional[float] = None
    contacto_nombre: str
    contacto_telefono: str
    notas: Optional[str] = None


class PedidoUpdate(BaseModel):
    """Schema para actualizar pedido (PATCH)"""
    repartidor_id: Optional[int] = None
    estado: Optional[EstadoPedido] = None
    notas_entrega: Optional[str] = None
    destino_direccion: Optional[str] = None
    contacto_telefono: Optional[str] = None


class PedidoCancelacion(BaseModel):
    """Schema para cancelar pedido"""
    motivo_cancelacion: str
    cancelado_por: int


class PedidoResponse(BaseModel):
    """Schema de respuesta de pedido"""
    id: int
    codigo: str
    cliente_id: int
    repartidor_id: Optional[int]
    origen_direccion: str
    origen_lat: Optional[float]
    origen_lon: Optional[float]
    destino_direccion: str
    destino_lat: Optional[float]
    destino_lon: Optional[float]
    zona_id: Optional[str]
    tipo_entrega: str
    estado: str
    descripcion: str
    peso_kg: float
    dimensiones: Optional[str]
    valor_declarado: Optional[float]
    contacto_nombre: str
    contacto_telefono: str
    notas: Optional[str]
    notas_entrega: Optional[str]
    created_at: datetime
    asignado_at: Optional[datetime]
    en_ruta_at: Optional[datetime]
    entregado_at: Optional[datetime]
    cancelado_at: Optional[datetime]
    updated_at: datetime
    motivo_cancelacion: Optional[str]

    class Config:
        from_attributes = True


class PedidoListResponse(BaseModel):
    """Schema de lista de pedidos"""
    total: int
    pedidos: list[PedidoResponse]
