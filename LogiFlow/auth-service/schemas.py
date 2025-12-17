from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
import sys

sys.path.append('..')
from shared.enums import UserRole


class UserRegister(BaseModel):
    """Schema para registro de usuario"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    zone_id: Optional[str] = None
    fleet_type: Optional[str] = None


class UserLogin(BaseModel):
    """Schema para login"""
    username: str
    password: str


class UserResponse(BaseModel):
    """Schema de respuesta de usuario"""
    id: int
    email: str
    username: str
    full_name: str
    role: str
    phone: Optional[str]
    zone_id: Optional[str]
    fleet_type: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema de respuesta de tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema para solicitud de refresh token"""
    refresh_token: str


class RevokeTokenRequest(BaseModel):
    """Schema para revocar token"""
    refresh_token: str
