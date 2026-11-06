"""
Capa de Conexión y Sesiones de Base de Datos para FastAPI
==========================================================
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from etl.config import get_database_url

# Crear el motor de SQLAlchemy con pool de conexiones optimizado
engine = create_engine(
    get_database_url(),
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    Dependency generator para inyección de sesiones SQL en endpoints de FastAPI.
    Garantiza el cierre automático de la conexión tras responder a la petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
