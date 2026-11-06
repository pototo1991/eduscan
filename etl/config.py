"""
Módulo de Configuración y Conexión para el Pipeline ETL de EduScan
==================================================================

Este módulo centraliza la lectura de variables de entorno y provee la URL de conexión
estándar hacia la base de datos PostgreSQL alojada en el mini servidor 'knossos' (o local).

Variables leídas desde el archivo .env:
---------------------------------------
- DB_HOST: Dirección IP o hostname del servidor PostgreSQL (ej: 192.168.100.16 o knossos.local).
- DB_PORT: Puerto expuesto del servicio (por defecto 5433 para evitar colisiones).
- DB_NAME: Nombre de la base de datos (ej: eduscan_db).
- DB_USER: Usuario con permisos de lectura/escritura (ej: eduscan_user).
- DB_PASSWORD: Clave de autenticación.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar automáticamente las variables definidas en .env en la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Configuración de conexión con valores predeterminados seguros
DB_HOST = os.getenv("DB_HOST", "knossos.local")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "eduscan_db")
DB_USER = os.getenv("DB_USER", "eduscan_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

def get_database_url() -> str:
    """
    Construye y retorna la cadena de conexión RFC 1738 para SQLAlchemy y psycopg2.

    Returns:
        str: URI de conexión con formato 'postgresql+psycopg2://user:pass@host:port/dbname'.
    
    Example:
        >>> from etl.config import get_database_url
        >>> from sqlalchemy import create_engine
        >>> engine = create_engine(get_database_url())
    """
    return f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
