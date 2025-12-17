from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import sys

sys.path.append('..')

from shared.database import get_db, Base, engine
from shared.config import get_settings
from shared.enums import EstadoFactura
import models
import schemas
import repository
import calculator

# Create tables
Base.metadata.create_all(bind=engine)

settings = get_settings()

app = FastAPI(title="LogiFlow - BillingService",
              description="Servicio de facturación y cálculo de tarifas",
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


@app.get("/")
def root():
    """Health check"""
    return {
        "service": "BillingService",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/billing/calcular",
          response_model=schemas.TarifaCalculoResponse)
def calcular_tarifa(calculo_request: schemas.TarifaCalculoRequest):
    """
    Calcular tarifa para una entrega
    
    No crea factura, solo calcula el costo estimado.
    
    - **tipo_entrega**: URBANA_RAPIDA, INTERMUNICIPAL, NACIONAL
    - **peso_kg**: Peso del paquete en kilogramos
    - **distancia_km**: Distancia estimada en kilómetros
    """
    try:
        calculo = calculator.TarifaCalculator.calcular_tarifa(
            calculo_request.tipo_entrega, calculo_request.peso_kg,
            calculo_request.distancia_km)

        return schemas.TarifaCalculoResponse(
            tipo_entrega=calculo_request.tipo_entrega.value,
            peso_kg=calculo_request.peso_kg,
            distancia_km=calculo_request.distancia_km,
            **calculo)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e))


@app.post("/api/billing/facturas",
          response_model=schemas.FacturaResponse,
          status_code=status.HTTP_201_CREATED)
def crear_factura(factura_data: schemas.FacturaCreate,
                  db: Session = Depends(get_db)):
    """
    Generar factura para un pedido
    
    Crea factura en estado BORRADOR con cálculo automático de tarifas.
    
    - **pedido_id**: ID del pedido
    - **cliente_id**: ID del cliente
    - **tipo_entrega**: Tipo de entrega
    - **peso_kg**: Peso del paquete
    - **distancia_km**: Distancia recorrida
    """
    repo = repository.BillingRepository(db)

    # Verificar que no exista factura para el pedido
    existing = repo.get_factura_by_pedido(factura_data.pedido_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=
            f"Ya existe una factura para el pedido {factura_data.pedido_id}")

    try:
        db_factura = repo.create_factura(factura_data)
        return schemas.FacturaResponse.model_validate(db_factura)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e))


@app.get("/api/billing/facturas", response_model=schemas.FacturaListResponse)
def listar_facturas(skip: int = Query(0, ge=0),
                    limit: int = Query(100, ge=1, le=1000),
                    estado: Optional[EstadoFactura] = None,
                    cliente_id: Optional[int] = None,
                    db: Session = Depends(get_db)):
    """
    Listar facturas con filtros opcionales
    
    - **skip**: Paginación - registros a saltar
    - **limit**: Paginación - máximo de registros
    - **estado**: Filtrar por estado (BORRADOR, EMITIDA, PAGADA, ANULADA)
    - **cliente_id**: Filtrar por cliente
    """
    repo = repository.BillingRepository(db)

    facturas, total = repo.get_facturas(skip=skip,
                                        limit=limit,
                                        estado=estado,
                                        cliente_id=cliente_id)

    return schemas.FacturaListResponse(
        total=total,
        facturas=[schemas.FacturaResponse.model_validate(f) for f in facturas])


@app.get("/api/billing/facturas/{factura_id}",
         response_model=schemas.FacturaResponse)
def obtener_factura(factura_id: int, db: Session = Depends(get_db)):
    """Obtener factura por ID"""
    repo = repository.BillingRepository(db)

    db_factura = repo.get_factura_by_id(factura_id)

    if not db_factura:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Factura {factura_id} no encontrada")

    return schemas.FacturaResponse.model_validate(db_factura)


@app.get("/api/billing/facturas/numero/{numero_factura}",
         response_model=schemas.FacturaResponse)
def obtener_factura_por_numero(numero_factura: str,
                               db: Session = Depends(get_db)):
    """Obtener factura por número (F-00001)"""
    repo = repository.BillingRepository(db)

    db_factura = repo.get_factura_by_numero(numero_factura)

    if not db_factura:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Factura {numero_factura} no encontrada")

    return schemas.FacturaResponse.model_validate(db_factura)


@app.get("/api/billing/facturas/pedido/{pedido_id}",
         response_model=schemas.FacturaResponse)
def obtener_factura_por_pedido(pedido_id: int, db: Session = Depends(get_db)):
    """Obtener factura asociada a un pedido"""
    repo = repository.BillingRepository(db)

    db_factura = repo.get_factura_by_pedido(pedido_id)

    if not db_factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe factura para el pedido {pedido_id}")

    return schemas.FacturaResponse.model_validate(db_factura)


@app.patch("/api/billing/facturas/{factura_id}",
           response_model=schemas.FacturaResponse)
def actualizar_factura(factura_id: int,
                       update_data: schemas.FacturaUpdate,
                       db: Session = Depends(get_db)):
    """
    Actualizar factura (PATCH)
    
    Permite cambiar estado, método de pago, etc.
    Actualiza automáticamente timestamps según cambios de estado.
    """
    repo = repository.BillingRepository(db)

    db_factura = repo.update_factura(factura_id, update_data)

    if not db_factura:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Factura {factura_id} no encontrada")

    return schemas.FacturaResponse.model_validate(db_factura)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.billing_service_port)
