"""
Middleware para validación de JWT en API Gateway
"""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from typing import Optional
import sys

sys.path.append('..')
from shared.config import get_settings
from shared.schemas import TokenData

settings = get_settings()
security = HTTPBearer()


async def verify_jwt_token(token: str) -> Optional[TokenData]:
    """
    Verifica JWT token llamando al AuthService
    
    Returns:
        TokenData si el token es válido, None si no lo es
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.auth_service_url}/api/auth/verify",
                params={"token": token},
                timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                return TokenData(user_id=data["user_id"],
                                 role=data["role"],
                                 zone_id=data.get("zone_id"),
                                 fleet_type=data.get("fleet_type"))
            else:
                return None
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None


async def get_current_user(
        credentials: HTTPAuthorizationCredentials) -> TokenData:
    """
    Dependency para obtener usuario actual desde token JWT
    
    Raises:
        HTTPException si el token no es válido
    """
    token = credentials.credentials

    token_data = await verify_jwt_token(token)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data


def require_roles(allowed_roles: list[str]):
    """
    Decorator para requerir roles específicos
    
    Usage:
        @require_roles(["ADMIN", "GERENTE"])
        async def protected_route(...):
            ...
    """

    async def role_checker(token_data: TokenData) -> TokenData:
        if token_data.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden. Required roles: {allowed_roles}")
        return token_data

    return role_checker
