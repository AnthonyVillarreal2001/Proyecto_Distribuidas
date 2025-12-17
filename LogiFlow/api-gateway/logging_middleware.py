"""
Logging Middleware para API Gateway
"""
from fastapi import Request
from datetime import datetime
import logging
import sys

sys.path.append('..')

# Configurar logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("APIGateway")


async def log_request_middleware(request: Request, call_next):
    """
    Middleware para logging centralizado
    
    Registra: método, URI, código de respuesta, user_id (si está autenticado)
    """
    start_time = datetime.utcnow()

    # Información de la request
    method = request.method
    url = str(request.url)
    client_host = request.client.host if request.client else "unknown"

    # Procesar request
    response = await call_next(request)

    # Calcular tiempo de procesamiento
    process_time = (datetime.utcnow() - start_time).total_seconds()

    # Obtener user_id si existe (del estado de la request)
    user_id = getattr(request.state, "user_id", None)

    # Log estructurado
    log_data = {
        "timestamp": start_time.isoformat(),
        "method": method,
        "url": url,
        "client_host": client_host,
        "status_code": response.status_code,
        "user_id": user_id,
        "process_time_seconds": round(process_time, 3)
    }

    # Agregar headers personalizados a la respuesta
    response.headers["X-Process-Time"] = str(process_time)

    if hasattr(request.state, "rate_limit_remaining"):
        response.headers["X-RateLimit-Remaining"] = str(
            request.state.rate_limit_remaining)

    # Log según nivel
    if response.status_code >= 500:
        logger.error(f"Request failed: {log_data}")
    elif response.status_code >= 400:
        logger.warning(f"Request error: {log_data}")
    else:
        logger.info(f"Request processed: {log_data}")

    return response
