from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import sys

sys.path.append('..')

from shared.database import get_db, Base, engine, wait_for_database
from shared.config import get_settings
import models
import schemas
import auth
import repository

# Wait for DB and create tables
wait_for_database()
Base.metadata.create_all(bind=engine)

settings = get_settings()

app = FastAPI(title="LogiFlow - AuthService",
              description="Servicio de autenticación y autorización",
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
        "service": "AuthService",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/auth/register",
          response_model=schemas.TokenResponse,
          status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    """
    Registro de nuevo usuario
    
    - **email**: Email único del usuario
    - **username**: Nombre de usuario único
    - **password**: Contraseña (mínimo 6 caracteres)
    - **full_name**: Nombre completo
    - **role**: Rol del usuario (ADMIN, GERENTE, SUPERVISOR, REPARTIDOR, CLIENTE)
    - **phone**: Teléfono (opcional)
    - **zone_id**: ID de zona para supervisores/repartidores (opcional)
    - **fleet_type**: Tipo de flota para repartidores (opcional)
    """
    repo = repository.AuthRepository(db)

    # Verificar si el usuario ya existe
    if repo.get_user_by_username(user_data.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username already registered")

    if repo.get_user_by_email(user_data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Email already registered")

    # Crear usuario (ACID transaction)
    db_user = repo.create_user(user_data)

    # Generar tokens
    token_data = {
        "sub": str(db_user.id),
        "role": db_user.role,
        "scope": "full_access",
        "zone_id": db_user.zone_id,
        "fleet_type": db_user.fleet_type
    }

    access_token = auth.create_access_token(token_data)
    refresh_token = auth.create_refresh_token({"sub": str(db_user.id)})

    # Guardar refresh token (ACID transaction)
    repo.save_refresh_token(db_user.id, refresh_token)

    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=schemas.UserResponse.model_validate(db_user))


@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    Autenticación de usuario
    
    - **username**: Nombre de usuario
    - **password**: Contraseña
    
    Retorna access_token y refresh_token JWT
    """
    repo = repository.AuthRepository(db)

    # Autenticar usuario
    user = repo.authenticate_user(credentials.username, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generar tokens con claims estructurados
    token_data = {
        "sub": str(user.id),
        "role": user.role,
        "scope": "full_access",
        "zone_id": user.zone_id,
        "fleet_type": user.fleet_type
    }

    access_token = auth.create_access_token(token_data)
    refresh_token = auth.create_refresh_token({"sub": str(user.id)})

    # Guardar refresh token (ACID transaction)
    repo.save_refresh_token(user.id, refresh_token)

    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=schemas.UserResponse.model_validate(user))


@app.post("/api/auth/token/refresh", response_model=schemas.TokenResponse)
def refresh_token(request: schemas.RefreshTokenRequest,
                  db: Session = Depends(get_db)):
    """
    Renovar access token usando refresh token
    
    - **refresh_token**: Refresh token válido
    """
    repo = repository.AuthRepository(db)

    # Verificar refresh token
    token_data = auth.verify_token(request.refresh_token, token_type="refresh")

    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid refresh token")

    # Verificar que el token no esté revocado
    db_token = repo.get_refresh_token(request.refresh_token)

    if not db_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Refresh token revoked or not found")

    # Verificar que no haya expirado
    if db_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Refresh token expired")

    # Obtener usuario
    user = repo.get_user_by_id(token_data.user_id)

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="User not found or inactive")

    # Generar nuevo access token
    new_token_data = {
        "sub": str(user.id),
        "role": user.role,
        "scope": "full_access",
        "zone_id": user.zone_id,
        "fleet_type": user.fleet_type
    }

    new_access_token = auth.create_access_token(new_token_data)

    return schemas.TokenResponse(
        access_token=new_access_token,
        refresh_token=request.refresh_token,
        user=schemas.UserResponse.model_validate(user))


@app.post("/api/auth/token/revoke", status_code=status.HTTP_200_OK)
def revoke_token(request: schemas.RevokeTokenRequest,
                 db: Session = Depends(get_db)):
    """
    Revocar refresh token
    
    - **refresh_token**: Refresh token a revocar
    """
    repo = repository.AuthRepository(db)

    # Revocar token (ACID transaction)
    success = repo.revoke_refresh_token(request.refresh_token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refresh token not found or already revoked")

    return {
        "message": "Token revoked successfully",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/auth/verify")
def verify_access_token(token: str):
    """
    Verificar validez de access token (usado por otros servicios)
    
    - **token**: Access token a verificar
    """
    token_data = auth.verify_token(token, token_type="access")

    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired token")

    return {
        "valid": True,
        "user_id": token_data.user_id,
        "role": token_data.role,
        "zone_id": token_data.zone_id,
        "fleet_type": token_data.fleet_type
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.auth_service_port)
