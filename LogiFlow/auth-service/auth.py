from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import sys

sys.path.append('..')
from shared.config import get_settings
from shared.schemas import TokenData

settings = get_settings()

# Password hashing context
# Use bcrypt_sha256 to support long passwords (>72 bytes) safely
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña coincide con el hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera hash de contraseña"""
    return pwd_context.hash(password)


def create_access_token(data: dict,
                        expires_delta: Optional[timedelta] = None) -> str:
    """Crea un JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "iss": settings.jwt_issuer,
    })

    encoded_jwt = jwt.encode(to_encode,
                             settings.secret_key,
                             algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(data: dict,
                         expires_delta: Optional[timedelta] = None) -> str:
    """Crea un JWT refresh token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.refresh_token_expire_days)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "iss": settings.jwt_issuer,
    })

    encoded_jwt = jwt.encode(to_encode,
                             settings.secret_key,
                             algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str,
                 token_type: str = "access") -> Optional[TokenData]:
    """Verifica y decodifica un JWT token"""
    try:
        payload = jwt.decode(token,
                             settings.secret_key,
                             algorithms=[settings.algorithm],
                             options={"verify_exp": True})

        if payload.get("type") != token_type:
            return None

        user_id: int = payload.get("sub")
        role: str = payload.get("role")

        if user_id is None or role is None:
            return None

        token_data = TokenData(user_id=int(user_id),
                               role=role,
                               scope=payload.get("scope"),
                               zone_id=payload.get("zone_id"),
                               fleet_type=payload.get("fleet_type"))

        return token_data
    except JWTError:
        return None
