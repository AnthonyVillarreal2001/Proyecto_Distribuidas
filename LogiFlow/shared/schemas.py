from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TokenData(BaseModel):
    """Datos del token JWT"""
    user_id: int
    role: str
    scope: Optional[str] = None
    zone_id: Optional[str] = None
    fleet_type: Optional[str] = None


class Token(BaseModel):
    """Respuesta de autenticación"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ErrorResponse(BaseModel):
    """Respuesta estándar de error"""
    detail: str
    code: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


class SuccessResponse(BaseModel):
    """Respuesta estándar de éxito"""
    message: str
    data: Optional[dict] = None
    timestamp: datetime = datetime.utcnow()
