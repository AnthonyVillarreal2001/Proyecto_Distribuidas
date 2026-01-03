from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from typing import Optional
import models
import schemas
import auth
import sys

sys.path.append('..')
from shared.config import get_settings

settings = get_settings()


class AuthRepository:
    """Repository pattern for authentication operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str) -> Optional[models.User]:
        """Obtiene usuario por username"""
        return self.db.query(
            models.User).filter(models.User.username == username).first()

    def get_user_by_email(self, email: str) -> Optional[models.User]:
        """Obtiene usuario por email"""
        return self.db.query(
            models.User).filter(models.User.email == email).first()

    def get_user_by_id(self, user_id: int) -> Optional[models.User]:
        """Obtiene usuario por ID"""
        return self.db.query(
            models.User).filter(models.User.id == user_id).first()

    def create_user(self, user_data: schemas.UserRegister) -> models.User:
        """Crea un nuevo usuario - Transacción ACID"""
        hashed_password = auth.get_password_hash(user_data.password)

        db_user = models.User(email=user_data.email,
                              username=user_data.username,
                              hashed_password=hashed_password,
                              full_name=user_data.full_name,
                              role=user_data.role.value,
                              phone=user_data.phone,
                              zone_id=user_data.zone_id,
                              fleet_type=user_data.fleet_type)

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        return db_user

    def authenticate_user(self, username: str,
                          password: str) -> Optional[models.User]:
        """Autentica un usuario"""
        user = self.get_user_by_username(username)

        if not user:
            return None

        if not user.is_active:
            return None

        if not auth.verify_password(password, user.hashed_password):
            return None

        return user

    def save_refresh_token(self, user_id: int,
                           token: str) -> models.RefreshToken:
        """Guarda refresh token - Transacción ACID.

        Maneja colisiones de token único devolviendo el existente en caso de
        duplicado, evitando errores 500 por UniqueViolation.
        """
        expires_at = datetime.utcnow() + timedelta(
            days=settings.refresh_token_expire_days)

        db_token = models.RefreshToken(user_id=user_id,
                                       token=token,
                                       expires_at=expires_at)
        try:
            self.db.add(db_token)
            self.db.commit()
            self.db.refresh(db_token)
            return db_token
        except IntegrityError:
            self.db.rollback()
            existing = self.get_refresh_token(token)
            if existing:
                return existing
            # If the existing token is revoked, generate a new one and retry once
            new_token = auth.create_refresh_token({"sub": str(user_id)})
            retry = models.RefreshToken(user_id=user_id,
                                        token=new_token,
                                        expires_at=expires_at)
            self.db.add(retry)
            self.db.commit()
            self.db.refresh(retry)
            return retry

    def get_refresh_token(self, token: str) -> Optional[models.RefreshToken]:
        """Obtiene refresh token"""
        return self.db.query(models.RefreshToken).filter(
            models.RefreshToken.token == token,
            models.RefreshToken.is_revoked == False).first()

    def revoke_refresh_token(self, token: str) -> bool:
        """Revoca refresh token - Transacción ACID"""
        db_token = self.get_refresh_token(token)

        if not db_token:
            return False

        db_token.is_revoked = True
        self.db.commit()

        return True

    def revoke_all_user_tokens(self, user_id: int) -> int:
        """Revoca todos los tokens de un usuario - Transacción ACID"""
        count = self.db.query(models.RefreshToken).filter(
            models.RefreshToken.user_id == user_id,
            models.RefreshToken.is_revoked == False).update(
                {"is_revoked": True})

        self.db.commit()

        return count
