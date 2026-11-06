"""
Servidor Principal de EduScan (FastAPI)
=======================================
"""

import sys
from pathlib import Path

# Añadir la raíz del proyecto al sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.api import router as api_router

app = FastAPI(
    title="EduScan API",
    description="Plataforma de Visualización y Análisis del Sistema Educacional Chileno",
    version="1.0.0"
)

# Permitir CORS para desarrollo local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir las rutas de la API REST
app.include_router(api_router)

# Servir archivos estáticos del frontend (CSS, JS, Assets)
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/css", StaticFiles(directory=frontend_dir / "css"), name="css")
    app.mount("/js", StaticFiles(directory=frontend_dir / "js"), name="js")

@app.get("/", include_in_schema=False)
def serve_index():
    """Ruta raíz que entrega la aplicación web de EduScan."""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "EduScan API está activa. Accede a /docs para ver la documentación interactiva."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
