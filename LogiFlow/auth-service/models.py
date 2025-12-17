from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
import sys

sys.path.append('..')
from shared.database import Base


class User(Base):
    """Modelo de usuario"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(
        String,
        nullable=False)  # ADMIN, GERENTE, SUPERVISOR, REPARTIDOR, CLIENTE
    phone = Column(String)
    zone_id = Column(String, nullable=True)  # Para supervisores y repartidores
    fleet_type = Column(String, nullable=True)  # Para repartidores
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime,
                        default=datetime.utcnow,
                        onupdate=datetime.utcnow)


class RefreshToken(Base):
    """Modelo de refresh tokens"""
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
