# EduScan: Plataforma de Visualización y Análisis Escolar

Plataforma web para democratizar y analizar los datos abiertos del sistema educacional chileno (SIMCE, IDPS y Categorías de Desempeño).

---

## 🚀 Despliegue en Servidor «Knossos» (Base de Datos PostgreSQL)

Para levantar el contenedor de PostgreSQL en el mini servidor `knossos`:

### 1. Clonar el repositorio en Knossos
```bash
git clone https://github.com/pototo1991/eduscan.git
cd eduscan/deploy/knossos
```

### 2. Configurar variables de entorno
Crea tu archivo `.env` en esa misma carpeta (`deploy/knossos/.env`):
```dotenv
POSTGRES_DB=eduscan_db
POSTGRES_USER=eduscan_user
POSTGRES_PASSWORD=tu_contrasena_segura
```

### 3. Iniciar el servicio con Docker
```bash
docker compose up -d
```

* El contenedor creará automáticamente el volumen persistente `eduscan_pgdata`.
* Ejecutará el script `init_db.sql` inicializando las tablas, índices y la extensión `unaccent`.
* Expondrá el puerto `5432` en la red local.

Para verificar que está corriendo:
```bash
docker compose ps
docker compose logs -f
```

---

## 💻 Desarrollo Local e Ingesta de Datos (ETL)

En tu máquina local:

### 1. Variables de Entorno
Copia la plantilla `.env.example` a `.env` en la raíz del proyecto y ajusta la IP de `knossos`:
```dotenv
DB_HOST=IP_DE_KNOSSOS    # ej: 192.168.1.xxx o knossos.local
DB_PORT=5432
DB_NAME=eduscan_db
DB_USER=eduscan_user
DB_PASSWORD=tu_contrasena_segura
```

### 2. Entorno Virtual Python y Dependencias
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Ejecutar Ingesta Inicial a Knossos
```bash
python etl/cargar_a_postgres.py
```

---

## 📄 Documentación Completa
Consulta el archivo [documentacion_del_proyecto.md](documentacion_del_proyecto.md) para detalles del modelo relacional, diseño arquitectónico y roadmap de fases.
