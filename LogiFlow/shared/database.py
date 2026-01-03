from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
import time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import get_settings

settings = get_settings()

# Singleton pattern for database engine
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_database(max_attempts: int = 30,
                      delay_seconds: float = 2.0) -> None:
    """Block until the database is reachable.

    Tries to acquire a connection and execute a simple query. Useful to avoid
    race conditions during container startup when services initialize tables.
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            time.sleep(delay_seconds)
            attempt += 1

    # If we get here, DB never became ready
    raise RuntimeError(
        f"Database not ready after {max_attempts} attempts ("\
        f"{delay_seconds}s interval)"
    )
