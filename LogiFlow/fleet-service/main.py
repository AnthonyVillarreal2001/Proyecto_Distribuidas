from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import sys

sys.path.append('..')

from shared.database import get_db, Base, engine
from shared.config import get_settings
from shared.enums import EstadoRepartidor, TipoVehiculo
from shared.schemas import TokenData
import models
import schemas
import repository
import vehiculo_hierarchy
import auth_dependency

# Create tables
Base.metadata.create_all(bind=engine)

settings = get_settings()

app = FastAPI(title="LogiFlow - FleetService",
              description="Servicio de gestión de flota y repartidores",
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
        "service": "FleetService",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


# ========== REPARTIDORES ==========


@app.post("/api/flota/repartidores",
          response_model=schemas.RepartidorResponse,
          status_code=status.HTTP_201_CREATED)
def crear_repartidor(repartidor_data: schemas.RepartidorCreate,
                     db: Session = Depends(get_db),
                     current_user: TokenData = Depends(
                         auth_dependency.require_roles(["ADMIN", "GERENTE"]))):
    """
    Crear nuevo repartidor
    
    - **user_id**: ID del usuario en AuthService
    - **nombre_completo**: Nombre completo del repartidor
    - **telefono**: Teléfono de contacto
    - **email**: Email único
    - **licencia_conducir**: Número de licencia (opcional)
    - **zona_id**: Zona asignada (opcional)
    """
    repo = repository.FleetRepository(db)

    try:
        db_repartidor = repo.create_repartidor(repartidor_data)
        return schemas.RepartidorResponse.model_validate(db_repartidor)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e))


@app.get("/api/flota/repartidores",
         response_model=schemas.RepartidorListResponse)
def listar_repartidores(skip: int = Query(0, ge=0),
                        limit: int = Query(100, ge=1, le=1000),
                        estado: Optional[EstadoRepartidor] = None,
                        zona_id: Optional[str] = None,
                        db: Session = Depends(get_db),
                        current_user: TokenData = Depends(
                            auth_dependency.get_current_user)):
    """
    Listar repartidores con filtros opcionales
    
    - **skip**: Paginación - registros a saltar
    - **limit**: Paginación - máximo de registros
    - **estado**: Filtrar por estado (DISPONIBLE, EN_RUTA, MANTENIMIENTO, INACTIVO)
    - **zona_id**: Filtrar por zona
    """
    repo = repository.FleetRepository(db)

    repartidores, total = repo.get_repartidores(skip=skip,
                                                limit=limit,
                                                estado=estado,
                                                zona_id=zona_id)

    return schemas.RepartidorListResponse(
        total=total,
        repartidores=[
            schemas.RepartidorResponse.model_validate(r) for r in repartidores
        ])


@app.get("/api/flota/repartidores/{repartidor_id}",
         response_model=schemas.RepartidorResponse)
def obtener_repartidor(repartidor_id: int,
                       db: Session = Depends(get_db),
                       current_user: TokenData = Depends(
                           auth_dependency.get_current_user)):
    """Obtener repartidor por ID"""
    repo = repository.FleetRepository(db)

    db_repartidor = repo.get_repartidor_by_id(repartidor_id)

    if not db_repartidor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Repartidor {repartidor_id} no encontrado")

    return schemas.RepartidorResponse.model_validate(db_repartidor)


@app.patch("/api/flota/repartidores/{repartidor_id}",
           response_model=schemas.RepartidorResponse)
def actualizar_repartidor(repartidor_id: int,
                          update_data: schemas.RepartidorUpdate,
                          db: Session = Depends(get_db),
                          current_user: TokenData = Depends(
                              auth_dependency.get_current_user)):
    """
    Actualizar repartidor (PATCH)
    
    Actualiza solo los campos proporcionados.
    Actualiza automáticamente timestamp GPS si se envía ubicación.
    """
    repo = repository.FleetRepository(db)

    db_repartidor = repo.update_repartidor(repartidor_id, update_data)

    if not db_repartidor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Repartidor {repartidor_id} no encontrado")

    return schemas.RepartidorResponse.model_validate(db_repartidor)


@app.delete("/api/flota/repartidores/{repartidor_id}/del",
            status_code=status.HTTP_204_NO_CONTENT)
def eliminar_repartidor_permanente(repartidor_id: int,
                                   db: Session = Depends(get_db),
                                   current_user: TokenData = Depends(
                                       auth_dependency.require_roles(["ADMIN"
                                                                      ]))):
    """
    Eliminar repartidor permanentemente de la base de datos (solo ADMIN)
    
    ADVERTENCIA: Esta operación es irreversible.
    Solo usuarios con rol ADMIN pueden realizar eliminación permanente.
    """
    repo = repository.FleetRepository(db)

    if not repo.delete_repartidor_fisico(repartidor_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Repartidor {repartidor_id} no encontrado")

    return None


# ========== VEHÍCULOS ==========


@app.post("/api/flota/vehiculos",
          response_model=schemas.VehiculoResponse,
          status_code=status.HTTP_201_CREATED)
def crear_vehiculo(vehiculo_data: schemas.VehiculoCreate,
                   db: Session = Depends(get_db),
                   current_user: TokenData = Depends(
                       auth_dependency.require_roles(["ADMIN", "GERENTE"]))):
    """
    Crear nuevo vehículo
    
    Utiliza jerarquía de clases (VehiculoEntrega) para validar capacidades.
    
    - **repartidor_id**: ID del repartidor asignado
    - **tipo**: MOTORIZADO, VEHICULO_LIVIANO, CAMION
    - **placa**: Placa única del vehículo
    - **marca**: Marca del vehículo
    - **modelo**: Modelo del vehículo
    - **año**: Año de fabricación
    - **capacidad_peso_kg**: Capacidad de carga en kg
    """
    repo = repository.FleetRepository(db)

    try:
        db_vehiculo = repo.create_vehiculo(vehiculo_data)
        return schemas.VehiculoResponse.model_validate(db_vehiculo)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e))


@app.get("/api/flota/vehiculos", response_model=schemas.VehiculoListResponse)
def listar_vehiculos(skip: int = Query(0, ge=0),
                     limit: int = Query(100, ge=1, le=1000),
                     tipo: Optional[TipoVehiculo] = None,
                     repartidor_id: Optional[int] = None,
                     db: Session = Depends(get_db),
                     current_user: TokenData = Depends(
                         auth_dependency.get_current_user)):
    """
    Listar vehículos con filtros opcionales
    
    - **tipo**: Filtrar por tipo de vehículo
    - **repartidor_id**: Filtrar por repartidor
    """
    repo = repository.FleetRepository(db)

    vehiculos, total = repo.get_vehiculos(skip=skip,
                                          limit=limit,
                                          tipo=tipo,
                                          repartidor_id=repartidor_id)

    return schemas.VehiculoListResponse(
        total=total,
        vehiculos=[
            schemas.VehiculoResponse.model_validate(v) for v in vehiculos
        ])


@app.get("/api/flota/vehiculos/{vehiculo_id}",
         response_model=schemas.VehiculoResponse)
def obtener_vehiculo(vehiculo_id: int,
                     db: Session = Depends(get_db),
                     current_user: TokenData = Depends(
                         auth_dependency.get_current_user)):
    """Obtener vehículo por ID"""
    repo = repository.FleetRepository(db)

    db_vehiculo = repo.get_vehiculo_by_id(vehiculo_id)

    if not db_vehiculo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Vehículo {vehiculo_id} no encontrado")

    return schemas.VehiculoResponse.model_validate(db_vehiculo)


@app.patch("/api/flota/vehiculos/{vehiculo_id}",
           response_model=schemas.VehiculoResponse)
def actualizar_vehiculo(vehiculo_id: int,
                        update_data: schemas.VehiculoUpdate,
                        db: Session = Depends(get_db),
                        current_user: TokenData = Depends(
                            auth_dependency.get_current_user)):
    """
    Actualizar vehículo (PATCH)
    
    Útil para actualizar estado, fechas de mantenimiento, etc.
    """
    repo = repository.FleetRepository(db)

    db_vehiculo = repo.update_vehiculo(vehiculo_id, update_data)

    if not db_vehiculo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Vehículo {vehiculo_id} no encontrado")

    return schemas.VehiculoResponse.model_validate(db_vehiculo)


@app.delete("/api/flota/vehiculos/{vehiculo_id}/del",
            status_code=status.HTTP_204_NO_CONTENT)
def eliminar_vehiculo_permanente(vehiculo_id: int,
                                 db: Session = Depends(get_db),
                                 current_user: TokenData = Depends(
                                     auth_dependency.require_roles(["ADMIN"
                                                                    ]))):
    """
    Eliminar vehículo permanentemente de la base de datos (solo ADMIN)
    
    ADVERTENCIA: Esta operación es irreversible.
    Solo usuarios con rol ADMIN pueden realizar eliminación permanente.
    """
    repo = repository.FleetRepository(db)

    if not repo.delete_vehiculo_fisico(vehiculo_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Vehículo {vehiculo_id} no encontrado")

    return None


@app.get("/api/flota/vehiculos/capacidades/info")
def obtener_capacidades_vehiculos():
    """
    Obtener información de capacidades de cada tipo de vehículo
    
    Útil para el frontend al crear pedidos
    """
    capacidades = vehiculo_hierarchy.VehiculoFactory.obtener_capacidades()

    return {
        "capacidades": {
            tipo.value: info
            for tipo, info in capacidades.items()
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.fleet_service_port)
