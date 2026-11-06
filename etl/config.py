import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables desde el archivo .env si existe
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("DB_HOST", "knossos.local")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "eduscan_db")
DB_USER = os.getenv("DB_USER", "eduscan_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

def get_database_url() -> str:
    """Retorna la URL de conexión para SQLAlchemy / psycopg2."""
    return f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
