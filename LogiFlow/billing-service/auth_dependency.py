"""
Dependency para validación de JWT en BillingService
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from typing import Optional
import sys

sys.path.append('..')
from shared.config import get_settings
from shared.schemas import TokenData

settings = get_settings()
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(
    security)) -> TokenData:
    """
    Dependency para obtener usuario actual desde token JWT
    Verifica el token con el AuthService
    
    Raises:
        HTTPException si el token no es válido
    """
    token = credentials.credentials

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
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="AuthService unavailable")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(allowed_roles: list[str]):
    """
    Dependency factory para requerir roles específicos
    
    Usage:
        @app.get("/admin-only")
        async def admin_route(
            current_user: TokenData = Depends(require_roles(["ADMIN"]))
        ):
            ...
    """

    async def role_checker(current_user: TokenData = Depends(
        get_current_user)) -> TokenData:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=
                f"Access forbidden. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker
