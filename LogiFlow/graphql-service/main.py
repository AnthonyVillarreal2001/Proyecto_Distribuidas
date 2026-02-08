from shared.config import get_settings
import strawberry
from strawberry.schema.config import StrawberryConfig
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from strawberry.fastapi import GraphQLRouter
import httpx
import sys

sys.path.append('..')

settings = get_settings()


# Basic GraphQL types mirroring REST schemas
@strawberry.type
class Pedido:
    id: int
    codigo: str
    cliente_id: int
    repartidor_id: Optional[int]
    origen_direccion: str
    origen_lat: Optional[float]
    origen_lon: Optional[float]
    destino_direccion: str
    destino_lat: Optional[float]
    destino_lon: Optional[float]
    zona_id: Optional[str]
    tipo_entrega: str
    estado: str
    descripcion: str
    peso_kg: float
    dimensiones: Optional[str]
    valor_declarado: Optional[float]
    contacto_nombre: str
    contacto_telefono: str
    notas: Optional[str]
    notas_entrega: Optional[str]
    created_at: Optional[str]
    asignado_at: Optional[str]
    en_ruta_at: Optional[str]
    entregado_at: Optional[str]
    cancelado_at: Optional[str]
    updated_at: Optional[str]
    motivo_cancelacion: Optional[str]


@strawberry.type
class Factura:
    id: int
    numero_factura: str
    pedido_id: int
    cliente_id: int
    total: float
    estado: str


@strawberry.type
class Tarifa:
    subtotal: float
    impuestos: float
    total: float


@strawberry.type
class FlotaResumen:
    zona_id: Optional[str]
    total_disponible: int
    total_en_ruta: int


@strawberry.type
class KPIDiario:
    fecha: str
    zona_id: Optional[str]
    total_pedidos: int
    entregados: int
    cancelados: int


@strawberry.type
class CacheStats:
    hits: int
    misses: int


_cache = {}
cache_hits = 0
cache_misses = 0


@strawberry.input
class PedidoInput:
    cliente_id: int
    origen_direccion: str
    destino_direccion: str
    tipo_entrega: str
    descripcion: str
    peso_kg: float
    contacto_nombre: str
    contacto_telefono: str
    origen_lat: Optional[float] = None
    origen_lon: Optional[float] = None
    destino_lat: Optional[float] = None
    destino_lon: Optional[float] = None
    zona_id: Optional[str] = None
    dimensiones: Optional[str] = None
    valor_declarado: Optional[float] = None
    notas: Optional[str] = None


PEDIDO_FIELDS: set[str] = {
    "id",
    "codigo",
    "cliente_id",
    "repartidor_id",
    "origen_direccion",
    "origen_lat",
    "origen_lon",
    "destino_direccion",
    "destino_lat",
    "destino_lon",
    "zona_id",
    "tipo_entrega",
    "estado",
    "descripcion",
    "peso_kg",
    "dimensiones",
    "valor_declarado",
    "contacto_nombre",
    "contacto_telefono",
    "notas",
    "notas_entrega",
    "created_at",
    "asignado_at",
    "en_ruta_at",
    "entregado_at",
    "cancelado_at",
    "updated_at",
    "motivo_cancelacion",
}


def to_pedido(data: Dict[str, Any]) -> Pedido:
    """Map REST payload to Pedido ignoring unexpected keys."""
    filtered = {k: data.get(k) for k in PEDIDO_FIELDS}
    return Pedido(**filtered)  # type: ignore[arg-type]


async def rest_get(url: str, token: Optional[str] = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # Simple cache to avoid N+1 and count hits/misses
    global cache_hits, cache_misses
    cache_key = f"GET:{url}"
    if cache_key in _cache:
        cache_hits += 1
        return _cache[cache_key]
    cache_misses += 1
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers=headers)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        data = r.json()
        _cache[cache_key] = data
        return data


async def rest_post(url: str, data: dict, token: Optional[str] = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(url, json=data, headers=headers)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()


# Auth dependency to pass JWT from headers to resolvers
async def get_token(authorization: Optional[str] = Header(
        None)) -> Optional[str]:
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1]
    return None


@strawberry.type
class Query:

    @strawberry.field
    async def pedido_by_id(self, id: int, info) -> Optional[Pedido]:
        token = await get_token(
            info.context["request"].headers.get("authorization"))
        data = await rest_get(
            f"{settings.pedido_service_url}/api/pedidos/{id}", token)
        return to_pedido(data)

    @strawberry.field
    async def pedidos(self, limit: int = 10, info=None) -> List[Pedido]:
        token = await get_token(
            info.context["request"].headers.get("authorization"))
        data = await rest_get(
            f"{settings.pedido_service_url}/api/pedidos?limit={limit}", token)
        return [to_pedido(p) for p in data.get("pedidos", [])]

    @strawberry.field
    async def factura_by_id(self, id: int, info=None) -> Optional[Factura]:
        token = await get_token(
            info.context["request"].headers.get("authorization"))
        data = await rest_get(
            f"{settings.billing_service_url}/api/billing/facturas/{id}", token)
        return Factura(**data)

    @strawberry.field
    async def calcular_tarifa(self,
                              tipo_entrega: str,
                              peso_kg: float,
                              distancia_km: float,
                              info=None) -> Tarifa:
        token = await get_token(
            info.context["request"].headers.get("authorization"))
        data = await rest_post(
            f"{settings.billing_service_url}/api/billing/calcular", {
                "tipo_entrega": tipo_entrega,
                "peso_kg": peso_kg,
                "distancia_km": distancia_km
            }, token)
        return Tarifa(subtotal=data["subtotal"],
                      impuestos=data["impuestos"],
                      total=data["total"])

    @strawberry.field
    async def flotaActiva(self, zona_id: str, info=None) -> FlotaResumen:
        token = await get_token(
            info.context["request"].headers.get("authorization"))
        base = f"{settings.fleet_service_url}/api/flota/repartidores?limit=1000&zona_id={zona_id}"
        # Disponibles
        dispo = await rest_get(base + "&estado=DISPONIBLE", token)
        # En ruta
        ruta = await rest_get(base + "&estado=EN_RUTA", token)
        return FlotaResumen(zona_id=zona_id,
                            total_disponible=dispo.get("total", 0),
                            total_en_ruta=ruta.get("total", 0))

    @strawberry.field
    async def kpiDiario(self,
                        fecha: str,
                        zona_id: Optional[str] = None,
                        info=None) -> KPIDiario:
        token = await get_token(
            info.context["request"].headers.get("authorization"))
        # Obtener pedidos (paginado básico)
        data = await rest_get(
            f"{settings.pedido_service_url}/api/pedidos?limit=1000", token)
        pedidos = data.get("pedidos", [])
        # Filtrar por fecha (YYYY-MM-DD) y zona si aplica
        from datetime import datetime as dt

        def is_same_day(iso: str, target: str) -> bool:
            try:
                return dt.fromisoformat(iso.replace(
                    "Z", "")).date().isoformat() == target
            except Exception:
                return False

        filtered = [
            p for p in pedidos if is_same_day(p.get("created_at"), fecha) and (
                zona_id is None or p.get("zona_id") == zona_id)
        ]
        total = len(filtered)
        entregados = sum(1 for p in filtered if p.get("estado") == "ENTREGADO")
        cancelados = sum(1 for p in filtered if p.get("estado") == "CANCELADO")
        return KPIDiario(fecha=fecha,
                         zona_id=zona_id,
                         total_pedidos=total,
                         entregados=entregados,
                         cancelados=cancelados)

    @strawberry.field
    async def cache_stats(self) -> CacheStats:
        return CacheStats(hits=cache_hits, misses=cache_misses)


@strawberry.type
class Mutation:

    @strawberry.mutation
    async def crear_pedido(self, payload: PedidoInput, info=None) -> Pedido:
        token = await get_token(
            info.context["request"].headers.get("authorization"))
        body = {k: v for k, v in payload.__dict__.items() if v is not None}
        data = await rest_post(f"{settings.pedido_service_url}/api/pedidos",
                               body, token)
        return to_pedido(data)

    @strawberry.mutation
    async def crear_factura(self,
                            pedido_id: int,
                            cliente_id: int,
                            tipo_entrega: str,
                            peso_kg: float,
                            distancia_km: float,
                            info=None) -> Factura:
        token = await get_token(
            info.context["request"].headers.get("authorization"))
        body = {
            "pedido_id": pedido_id,
            "cliente_id": cliente_id,
            "tipo_entrega": tipo_entrega,
            "peso_kg": peso_kg,
            "distancia_km": distancia_km
        }
        data = await rest_post(
            f"{settings.billing_service_url}/api/billing/facturas", body,
            token)
        return Factura(**data)


schema = strawberry.Schema(query=Query,
                           mutation=Mutation,
                           config=StrawberryConfig(auto_camel_case=False))

app = FastAPI(title="LogiFlow - GraphQL Service")


async def get_context(request: Request):
    # Ensure request is present in context for resolvers
    return {"request": request}


# Habilita GraphiQL para probar queries/mutations desde la UI gráfica
graphql_app = GraphQLRouter(schema, context_getter=get_context, graphiql=True)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/")
async def health():
    return {"service": "GraphQLService", "status": "running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5006)
