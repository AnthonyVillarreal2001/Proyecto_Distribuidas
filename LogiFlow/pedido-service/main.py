from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import sys

sys.path.append('..')

from shared.database import get_db, Base, engine
from shared.config import get_settings
from shared.enums import EstadoPedido
import models
import schemas
import repository

# Create tables
Base.metadata.create_all(bind=engine)

settings = get_settings()

app = FastAPI(title="LogiFlow - PedidoService",
              description="Servicio de gestión de pedidos",
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
        "service": "PedidoService",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/pedidos",
          response_model=schemas.PedidoResponse,
          status_code=status.HTTP_201_CREATED)
def crear_pedido(pedido_data: schemas.PedidoCreate,
                 db: Session = Depends(get_db)):
    """
    Crear nuevo pedido
    
    Valida automáticamente el tipo de entrega y peso usando Factory Pattern.
    
    - **cliente_id**: ID del cliente que realiza el pedido
    - **tipo_entrega**: URBANA_RAPIDA, INTERMUNICIPAL, NACIONAL
    - **origen/destino**: Direcciones y coordenadas
    - **descripcion**: Descripción del paquete
    - **peso_kg**: Peso en kilogramos
    - **contacto**: Información de contacto del destinatario
    """
    repo = repository.PedidoRepository(db)

    try:
        db_pedido = repo.create_pedido(pedido_data)
        return schemas.PedidoResponse.model_validate(db_pedido)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e))


@app.get("/api/pedidos", response_model=schemas.PedidoListResponse)
def listar_pedidos(skip: int = Query(0, ge=0),
                   limit: int = Query(100, ge=1, le=1000),
                   estado: Optional[EstadoPedido] = None,
                   cliente_id: Optional[int] = None,
                   repartidor_id: Optional[int] = None,
                   db: Session = Depends(get_db)):
    """
    Listar pedidos con filtros opcionales
    
    - **skip**: Número de registros a saltar (paginación)
    - **limit**: Número máximo de registros a retornar
    - **estado**: Filtrar por estado del pedido
    - **cliente_id**: Filtrar por cliente
    - **repartidor_id**: Filtrar por repartidor
    """
    repo = repository.PedidoRepository(db)

    pedidos, total = repo.get_pedidos(skip=skip,
                                      limit=limit,
                                      estado=estado,
                                      cliente_id=cliente_id,
                                      repartidor_id=repartidor_id)

    return schemas.PedidoListResponse(
        total=total,
        pedidos=[schemas.PedidoResponse.model_validate(p) for p in pedidos])


@app.get("/api/pedidos/{pedido_id}", response_model=schemas.PedidoResponse)
def obtener_pedido(pedido_id: int, db: Session = Depends(get_db)):
    """
    Obtener pedido por ID
    """
    repo = repository.PedidoRepository(db)

    db_pedido = repo.get_pedido_by_id(pedido_id)

    if not db_pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Pedido {pedido_id} no encontrado")

    return schemas.PedidoResponse.model_validate(db_pedido)


@app.get("/api/pedidos/codigo/{codigo}", response_model=schemas.PedidoResponse)
def obtener_pedido_por_codigo(codigo: str, db: Session = Depends(get_db)):
    """
    Obtener pedido por código (P-00001)
    """
    repo = repository.PedidoRepository(db)

    db_pedido = repo.get_pedido_by_codigo(codigo)

    if not db_pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Pedido {codigo} no encontrado")

    return schemas.PedidoResponse.model_validate(db_pedido)


@app.patch("/api/pedidos/{pedido_id}", response_model=schemas.PedidoResponse)
def actualizar_pedido(pedido_id: int,
                      update_data: schemas.PedidoUpdate,
                      db: Session = Depends(get_db)):
    """
    Actualizar pedido parcialmente (PATCH)
    
    Solo actualiza los campos proporcionados.
    Actualiza automáticamente timestamps según cambios de estado.
    """
    repo = repository.PedidoRepository(db)

    db_pedido = repo.update_pedido(pedido_id, update_data)

    if not db_pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Pedido {pedido_id} no encontrado")

    return schemas.PedidoResponse.model_validate(db_pedido)


@app.delete("/api/pedidos/{pedido_id}", response_model=schemas.PedidoResponse)
def cancelar_pedido(pedido_id: int,
                    cancelacion: schemas.PedidoCancelacion,
                    db: Session = Depends(get_db)):
    """
    Cancelar pedido (cancelación lógica)
    
    - **motivo_cancelacion**: Motivo de la cancelación
    - **cancelado_por**: ID del usuario que cancela
    
    No se pueden cancelar pedidos ya entregados.
    """
    repo = repository.PedidoRepository(db)

    try:
        db_pedido = repo.cancelar_pedido(pedido_id, cancelacion)

        if not db_pedido:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Pedido {pedido_id} no encontrado")

        return schemas.PedidoResponse.model_validate(db_pedido)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.pedido_service_port)
