from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from datetime import datetime
import sys

sys.path.append('..')

from shared.config import get_settings
from shared.schemas import TokenData
from .auth_middleware import get_current_user, verify_jwt_token
from .rate_limiter import rate_limit_middleware, rate_limiter
from .logging_middleware import log_request_middleware

settings = get_settings()
security = HTTPBearer()

app = FastAPI(
    title="LogiFlow - API Gateway",
    description="Punto único de entrada para todos los microservicios",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
app.middleware("http")(log_request_middleware)


@app.get("/")
def root():
    """Health check del API Gateway"""
    return {
        "service": "API Gateway",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "auth": settings.auth_service_url,
            "pedidos": settings.pedido_service_url,
            "fleet": settings.fleet_service_url,
            "billing": settings.billing_service_url
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check de todos los servicios
    
    Verifica conectividad con cada microservicio
    """
    services_health = {}

    async with httpx.AsyncClient() as client:
        # Check AuthService
        try:
            response = await client.get(f"{settings.auth_service_url}/",
                                        timeout=3.0)
            services_health["auth"] = {
                "status":
                "healthy" if response.status_code == 200 else "unhealthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        except Exception as e:
            services_health["auth"] = {
                "status": "unreachable",
                "error": str(e)
            }

        # Check PedidoService
        try:
            response = await client.get(f"{settings.pedido_service_url}/",
                                        timeout=3.0)
            services_health["pedidos"] = {
                "status":
                "healthy" if response.status_code == 200 else "unhealthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        except Exception as e:
            services_health["pedidos"] = {
                "status": "unreachable",
                "error": str(e)
            }

        # Check FleetService
        try:
            response = await client.get(f"{settings.fleet_service_url}/",
                                        timeout=3.0)
            services_health["fleet"] = {
                "status":
                "healthy" if response.status_code == 200 else "unhealthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        except Exception as e:
            services_health["fleet"] = {
                "status": "unreachable",
                "error": str(e)
            }

        # Check BillingService
        try:
            response = await client.get(f"{settings.billing_service_url}/",
                                        timeout=3.0)
            services_health["billing"] = {
                "status":
                "healthy" if response.status_code == 200 else "unhealthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        except Exception as e:
            services_health["billing"] = {
                "status": "unreachable",
                "error": str(e)
            }

    overall_healthy = all(
        service.get("status") == "healthy"
        for service in services_health.values())

    return {
        "overall_status": "healthy" if overall_healthy else "degraded",
        "services": services_health,
        "timestamp": datetime.utcnow().isoformat()
    }


# ========== PROXY ENDPOINTS ==========


async def proxy_request(request: Request,
                        target_url: str,
                        require_auth: bool = False) -> JSONResponse:
    """
    Proxy genérico para reenviar requests a microservicios
    
    Args:
        request: FastAPI Request object
        target_url: URL del servicio destino
        require_auth: Si requiere autenticación
    """
    # Rate limiting
    await rate_limit_middleware(request)

    # Autenticación si es requerida
    user_id = None
    if require_auth:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header")

        token = auth_header.split(" ")[1]
        token_data = await verify_jwt_token(token)

        if not token_data:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid or expired token")

        user_id = token_data.user_id
        request.state.user_id = user_id

    # Proxy request
    async with httpx.AsyncClient() as client:
        try:
            # Copiar headers (excepto Host)
            headers = {
                key: value
                for key, value in request.headers.items()
                if key.lower() not in ["host", "content-length"]
            }

            # Realizar request al servicio
            response = await client.request(method=request.method,
                                            url=target_url,
                                            headers=headers,
                                            content=await request.body(),
                                            timeout=30.0)

            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code,
                headers=dict(response.headers))

        except httpx.TimeoutException:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                                detail="Service timeout")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                                detail=f"Service unavailable: {str(e)}")


# ========== AUTH SERVICE ROUTES (Public) ==========


@app.api_route("/api/auth/{path:path}",
               methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def auth_service_proxy(request: Request, path: str):
    """Proxy para AuthService - Rutas públicas"""
    target_url = f"{settings.auth_service_url}/api/auth/{path}"
    return await proxy_request(request, target_url, require_auth=False)


# ========== PEDIDO SERVICE ROUTES (Protected) ==========


@app.api_route("/api/pedidos/{path:path}",
               methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def pedidos_service_proxy(request: Request, path: str):
    """Proxy para PedidoService - Rutas protegidas"""
    target_url = f"{settings.pedido_service_url}/api/pedidos/{path}"
    return await proxy_request(request, target_url, require_auth=True)


@app.api_route("/api/pedidos", methods=["GET", "POST"])
async def pedidos_service_root(request: Request):
    """Proxy para PedidoService root - Rutas protegidas"""
    target_url = f"{settings.pedido_service_url}/api/pedidos"
    return await proxy_request(request, target_url, require_auth=True)


# ========== FLEET SERVICE ROUTES (Protected) ==========


@app.api_route("/api/flota/{path:path}",
               methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def fleet_service_proxy(request: Request, path: str):
    """Proxy para FleetService - Rutas protegidas"""
    target_url = f"{settings.fleet_service_url}/api/flota/{path}"
    return await proxy_request(request, target_url, require_auth=True)


# ========== BILLING SERVICE ROUTES (Protected) ==========


@app.api_route("/api/billing/{path:path}",
               methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def billing_service_proxy(request: Request, path: str):
    """Proxy para BillingService - Rutas protegidas"""
    target_url = f"{settings.billing_service_url}/api/billing/{path}"
    return await proxy_request(request, target_url, require_auth=True)


# ========== RATE LIMIT INFO ==========


@app.get("/api/rate-limit/info")
async def get_rate_limit_info(request: Request):
    """Obtener información de rate limiting para el cliente actual"""
    client_id = request.client.host if request.client else "unknown"
    remaining = rate_limiter.get_remaining_requests(client_id)

    return {
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "remaining_requests": remaining,
        "client_id": client_id
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.api_gateway_port)
