"""
Rate Limiting Middleware
"""
from fastapi import Request, HTTPException, status
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict
import sys

sys.path.append('..')
from shared.config import get_settings

settings = get_settings()


class RateLimiter:
    """
    Simple in-memory rate limiter
    
    En producción se debería usar Redis para compartir estado entre instancias
    """

    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)

    def _clean_old_requests(self, client_id: str):
        """Limpia requests antiguos (más de 1 minuto)"""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=1)

        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]

    async def check_rate_limit(self, request: Request) -> bool:
        """
        Verifica si el cliente ha excedido el rate limit
        
        Returns:
            True si está dentro del límite, False si lo excedió
        """
        # Usar IP del cliente como identificador
        client_id = request.client.host if request.client else "unknown"

        # Limpiar requests antiguos
        self._clean_old_requests(client_id)

        # Verificar límite
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False

        # Agregar request actual
        self.requests[client_id].append(datetime.utcnow())

        return True

    def get_remaining_requests(self, client_id: str) -> int:
        """Retorna el número de requests restantes"""
        self._clean_old_requests(client_id)
        return max(0, self.requests_per_minute - len(self.requests[client_id]))


# Singleton global del rate limiter
rate_limiter = RateLimiter(requests_per_minute=settings.rate_limit_per_minute)


async def rate_limit_middleware(request: Request):
    """
    Middleware para aplicar rate limiting
    
    Raises:
        HTTPException 429 si se excede el límite
    """
    if not await rate_limiter.check_rate_limit(request):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Rate limit exceeded. Try again later.",
                            headers={
                                "Retry-After":
                                "60",
                                "X-RateLimit-Limit":
                                str(settings.rate_limit_per_minute),
                                "X-RateLimit-Remaining":
                                "0"
                            })

    client_id = request.client.host if request.client else "unknown"
    remaining = rate_limiter.get_remaining_requests(client_id)

    # Agregar headers de rate limit a la respuesta
    request.state.rate_limit_remaining = remaining
