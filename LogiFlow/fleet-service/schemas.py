from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
import sys

sys.path.append('..')
from shared.enums import EstadoRepartidor, TipoVehiculo


class RepartidorCreate(BaseModel):
    """Schema para crear repartidor"""
    user_id: int
    nombre_completo: str
    telefono: str
    email: EmailStr
    licencia_conducir: Optional[str] = None
    zona_id: Optional[str] = None


class RepartidorUpdate(BaseModel):
    """Schema para actualizar repartidor"""
    estado: Optional[EstadoRepartidor] = None
    zona_id: Optional[str] = None
    telefono: Optional[str] = None
    ubicacion_lat: Optional[float] = None
    ubicacion_lon: Optional[float] = None


class RepartidorResponse(BaseModel):
    """Schema de respuesta de repartidor"""
    id: int
    user_id: int
    nombre_completo: str
    telefono: str
    email: str
    licencia_conducir: Optional[str]
    zona_id: Optional[str]
    estado: str
    ubicacion_lat: Optional[float]
    ubicacion_lon: Optional[float]
    ultima_actualizacion_gps: Optional[datetime]
    fecha_ingreso: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VehiculoCreate(BaseModel):
    """Schema para crear vehículo"""
    repartidor_id: int
    tipo: TipoVehiculo
    placa: str
    marca: str
    modelo: str
    año: int = Field(..., ge=1900, le=2030)
    color: Optional[str] = None
    capacidad_peso_kg: float = Field(..., gt=0)
    capacidad_volumen_m3: Optional[float] = None
    soat_vencimiento: Optional[datetime] = None
    revision_tecnica_vencimiento: Optional[datetime] = None


class VehiculoUpdate(BaseModel):
    """Schema para actualizar vehículo"""
    estado: Optional[str] = None
    ultimo_mantenimiento: Optional[datetime] = None
    proximo_mantenimiento: Optional[datetime] = None
    soat_vencimiento: Optional[datetime] = None
    revision_tecnica_vencimiento: Optional[datetime] = None


class VehiculoResponse(BaseModel):
    """Schema de respuesta de vehículo"""
    id: int
    repartidor_id: int
    tipo: str
    placa: str
    marca: str
    modelo: str
    año: int
    color: Optional[str]
    capacidad_peso_kg: float
    capacidad_volumen_m3: Optional[float]
    estado: str
    ultimo_mantenimiento: Optional[datetime]
    proximo_mantenimiento: Optional[datetime]
    soat_vencimiento: Optional[datetime]
    revision_tecnica_vencimiento: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RepartidorListResponse(BaseModel):
    """Schema de lista de repartidores"""
    total: int
    repartidores: list[RepartidorResponse]


class VehiculoListResponse(BaseModel):
    """Schema de lista de vehículos"""
    total: int
    vehiculos: list[VehiculoResponse]
