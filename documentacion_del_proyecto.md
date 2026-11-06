# EduScan: Plataforma de Visualización y Análisis Escolar

## 1. Resumen Ejecutivo

**EduScan** es una solución web orientada a la democratización, ordenamiento y análisis accesible de datos del sistema educacional chileno. 

Actualmente, organismos estatales como la Agencia de Calidad de la Educación y el Ministerio de Educación (Mineduc) publican grandes volúmenes de datos abiertos en formatos densos (`.csv`, `.dta`, `.xlsx`), los cuales no son directamente comprensibles para el público general ni para apoderados que buscan tomar decisiones informadas sobre la educación de sus hijos.

**EduScan** toma estos registros masivos y los transforma en:
* Una interfaz visual intuitiva, moderna y ágil (diseño Mobile-First).
* Fichas escolares claras por establecimiento (**RBD** - *Rol Base de Datos*).
* Filtros dinámicos por criterios territoriales y administrativos (comuna, dependencia, puntaje).
* Comparativas directas («lado a lado») entre instituciones similares.

---

## 2. Propuesta de Valor y Audiencia

| Perfil de Usuario | Caso de Uso en EduScan |
| :--- | :--- |
| **Apoderados y Familias** | Evaluar alternativas escolares en su comuna, comparar colegios particulares pagados, subvencionados y públicos (Municipales / SLEP), y conocer trayectorias históricas de rendimiento y clima escolar. |
| **Equipos Directivos y Sostenedores** | Comparar su posición frente al promedio comunal o de su mismo nivel socioeconómico (NSE) para definir planes de mejoramiento educativo (PME). |
| **Investigadores y Periodistas** | Acceder a datos históricos y actuales limpios para análisis de políticas públicas y brechas de aprendizaje territorial. |

---

## 3. Funcionalidades Principales

1. **Buscador Universal y Multicriterio:**
   * Búsqueda por nombre de colegio o código **RBD**.
   * Filtros combinables en tiempo real:
     * Región, Provincia y Comuna.
     * Dependencia administrativa: Municipal / SLEP, Particular Subvencionado, Particular Pagado, Administración Delegada.
     * Nivel escolar evaluado (4° Básico, 8° Básico, II° Medio).
     * Grupo socioeconómico del colegio (A, B, C, D, E).

2. **Ficha Escolar Inteligente:**
   * Resumen de puntajes de la prueba SIMCE más reciente (Lectura, Matemática, Ciencias/Historia).
   * Indicadores de Desarrollo Personal y Social (IDPS): Autoestima académica, convivencia escolar, hábitos de vida saludable y participación ciudadana.
   * Categoría de Desempeño oficial asignada por la Agencia (Alto, Medio, Medio-Bajo, Insuficiente).
   * Gráficos interactivos de evolución histórica temporal.
   * Indicadores de contexto: matrícula total, ruralidad/urbanidad y grupo socioeconómico.

3. **Módulo Comparador («Lado a Lado»):**
   * Selección de 2 a 3 colegios de la misma comuna o características similares.
   * Tabla y gráficos comparativos respecto a:
     * Rendimiento por materia.
     * Diferencia porcentual con el promedio comunal y nacional.
     * Comparativa de IDPS y clima de convivencia.

4. **Visor Territorial:**
   * Mapa interactivo con georreferenciación de establecimientos e indicadores de color según desempeño y dependencia administrativa.

---

## 4. Estrategia de Ingesta y Limpieza de Datos (ETL)

Los datos abiertos provienen del portal oficial de la Agencia de Calidad de la Educación:
* **Fuente Oficial:** [Bases de Datos Agencia de Educación](https://informacionestadistica.agenciaeducacion.cl/#/bases)

### 4.1. Metodología: Descarga Manual Inicial e Ingesta por Procesos

Dado que la Agencia publica datos con frecuencia anual (o bianual) y que los esquemas de nombres de columnas y codificación cambian con frecuencia entre periodos, la estrategia adoptada es:

1. **Descarga Manual Controlada:** Se descargan manualmente los paquetes de datos y sus respectivos *Libros de Códigos* (diccionarios metodológicos).
2. **Priorización Proceso por Proceso (Enfoque Iterativo):**
   * **Paso 1 (Núcleo SIMCE):** Ingesta de resultados SIMCE de 4° Básico y II° Medio para los periodos más recientes. Permite poblar el catálogo base de establecimientos y desplegar el primer buscador y comparador funcional.
   * **Paso 2 (IDPS):** Incorporación de Indicadores de Desarrollo Personal y Social, asociados al mismo `rbd` y `anio`.
   * **Paso 3 (Categorías de Desempeño):** Carga de las clasificaciones anuales consolidadas emitidas por la Agencia.
3. **Normalización Automatizada con Python:** Scripts encargados de:
   * Detección de codificación (`UTF-8`, `latin-1`, `cp1252`).
   * Normalización de delimitadores (generalmente `;`).
   * Homogeneización de nombres de columnas a minúsculas y snake_case.
   * Carga masiva (*bulk insert* / `COPY`) hacia la base de datos PostgreSQL en el servidor `knossos`.

### 4.2. Estructura de Archivos del Proyecto

```text
eduscan/
├── data/
│   ├── raw/                      # Archivos CSV descargados sin modificar (en .gitignore)
│   │   ├── simce/
│   │   ├── idps/
│   │   └── categorias/
│   └── diccionarios/             # PDFs y fichas metodológicas oficiales
├── etl/
│   ├── config.py                 # Conexión DB leyendo variables de entorno
│   ├── normalizador.py           # Funciones de parseo, limpieza y validación
│   ├── 01_cargar_establecimientos.py
│   ├── 02_cargar_simce.py
│   └── 03_cargar_idps.py
├── backend/                      # API Backend (FastAPI)
├── frontend/                     # Aplicación Web (HTML5, CSS, JS)
├── docker-compose.local.yml       # Orquestación de entorno web local
├── docker-compose.knossos.yml     # Orquestación de base de datos en knossos
└── .env.example                  # Plantilla de variables de entorno
```

---

## 5. Arquitectura de Despliegue e Infraestructura (Contenedores)

El sistema se estructura en dos entornos desacoplados para aprovechar los recursos locales y el servidor dedicado:

```text
 ┌──────────────────────────────────────────────┐
 │               TU EQUIPO LOCAL                │
 │                                              │
 │  ┌────────────────────────────────────────┐  │
 │  │ Contenedor Web & API (EduScan App)     │  │
 │  │ • FastAPI (Backend REST)               │  │
 │  │ • Servidor Web Frontend (Hot-reload)   │  │
 │  └───────────────────┬────────────────────┘  │
 │                      │                       │
 │  ┌───────────────────▼────────────────────┐  │
 │  │ Scripts ETL de Limpieza y Carga        │  │
 │  └───────────────────┬────────────────────┘  │
 └──────────────────────┼───────────────────────┘
                        │ Conexión Red Local / LAN
                        │ Puerto 5433 (PostgreSQL en knossos)
                        ▼
 ┌──────────────────────────────────────────────┐
 │        MINI SERVIDOR «KNOSSOS»               │
 │                                              │
 │  ┌────────────────────────────────────────┐  │
 │  │ Contenedor Docker: PostgreSQL 16       │  │
 │  │ • Base de Datos: eduscan_db            │  │
 │  │ • Extensiones: unaccent (búsquedas),   │  │
 │  │   postgis (opcional para visor mapas)  │  │
 │  └───────────────────┬────────────────────┘  │
 │                      ▼                       │
 │        [Volumen Docker Persistente]          │
 └──────────────────────────────────────────────┘
```

### 5.1. Configuración de Base de Datos en Servidor «Knossos»

Archivo de orquestación para ejecutar en el mini servidor `knossos`:

```yaml
# docker-compose.knossos.yml (en servidor knossos)
version: '3.8'

services:
  eduscan-db:
    image: postgres:16-alpine
    container_name: eduscan_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: eduscan_db
      POSTGRES_USER: ${POSTGRES_USER:-eduscan_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Debe definirse contraseña segura}
    ports:
      # Exposición en la red local (o bind a IP específica de knossos)
      - "${DB_PORT:-5433}:5432"
    volumes:
      - eduscan_pgdata:/var/lib/postgresql/data
    networks:
      - eduscan_net

volumes:
  eduscan_pgdata:
    driver: local

networks:
  eduscan_net:
    driver: bridge
```

### 5.2. Configuración de la Aplicación en Equipo Local

Archivo para el entorno de desarrollo y ejecución de la aplicación web:

```yaml
# docker-compose.local.yml (en equipo local)
version: '3.8'

services:
  web-api:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: eduscan_web
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app/backend
      - ./frontend:/app/frontend
      - ./etl:/app/etl
      - ./data:/app/data
    env_file:
      - .env
    environment:
      - PYTHONUNBUFFERED=1
```

### 5.3. Plantilla de Variables de Entorno (`.env.example`)

```dotenv
# Conexión a Base de Datos en servidor Knossos
DB_HOST=knossos.local        # O IP estática de knossos en tu red local (ej: 192.168.1.xxx)
DB_PORT=5433
DB_NAME=eduscan_db
DB_USER=eduscan_user
DB_PASSWORD=tu_contrasena_segura

# Entorno de la aplicación
APP_ENV=development
APP_PORT=8000
```

---

## 6. Diseño del Modelo Relacional

```sql
-- Habilitar extensión para ignorar tildes en búsquedas textuales
CREATE EXTENSION IF NOT EXISTS unaccent;

-- 1. Tabla de Establecimientos Educacionales
CREATE TABLE establecimiento (
    rbd INTEGER PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    dependencia VARCHAR(100) NOT NULL,
    cod_depe INTEGER,
    region VARCHAR(100),
    cod_region INTEGER,
    provincia VARCHAR(100),
    comuna VARCHAR(100) NOT NULL,
    cod_comuna INTEGER,
    es_urbano BOOLEAN,
    estado VARCHAR(50) DEFAULT 'FUNCIONANDO',
    latitud NUMERIC(10, 7),
    longitud NUMERIC(10, 7),
    actualizado_al DATE DEFAULT CURRENT_DATE
);

-- 2. Tabla de Resultados SIMCE
CREATE TABLE evaluacion_simce (
    id SERIAL PRIMARY KEY,
    rbd INTEGER NOT NULL REFERENCES establecimiento(rbd) ON DELETE CASCADE,
    anio INTEGER NOT NULL,
    grado VARCHAR(10) NOT NULL, -- '4b', '8b', '2m'
    nse VARCHAR(10),             -- Grupo socioeconómico
    alumnos_evaluados INTEGER,
    puntaje_lectura NUMERIC(6, 2),
    puntaje_matematica NUMERIC(6, 2),
    puntaje_ciencias NUMERIC(6, 2),
    puntaje_historia NUMERIC(6, 2),
    CONSTRAINT uq_simce_rbd_anio_grado UNIQUE (rbd, anio, grado)
);

-- 3. Tabla de Indicadores de Desarrollo Personal y Social (IDPS)
CREATE TABLE indicador_desarrollo_social (
    id SERIAL PRIMARY KEY,
    rbd INTEGER NOT NULL REFERENCES establecimiento(rbd) ON DELETE CASCADE,
    anio INTEGER NOT NULL,
    grado VARCHAR(10) NOT NULL,
    autoestima_academica NUMERIC(5, 2),
    clima_convivencia NUMERIC(5, 2),
    participacion_ciudadana NUMERIC(5, 2),
    habitos_vida_saludable NUMERIC(5, 2),
    CONSTRAINT uq_idps_rbd_anio_grado UNIQUE (rbd, anio, grado)
);

-- 4. Tabla de Categoría de Desempeño Oficial
CREATE TABLE categoria_desempeno (
    id SERIAL PRIMARY KEY,
    rbd INTEGER NOT NULL REFERENCES establecimiento(rbd) ON DELETE CASCADE,
    anio INTEGER NOT NULL,
    nivel VARCHAR(50) NOT NULL, -- 'Básica' o 'Media'
    categoria VARCHAR(50) NOT NULL, -- 'Alto', 'Medio', 'Medio-Bajo', 'Insuficiente'
    CONSTRAINT uq_categoria_rbd_anio_nivel UNIQUE (rbd, anio, nivel)
);

-- Índices optimizados para filtros de búsqueda y comparadores
CREATE INDEX idx_establecimiento_nombre ON establecimiento USING btree (nombre);
CREATE INDEX idx_establecimiento_comuna ON establecimiento (comuna);
CREATE INDEX idx_establecimiento_dependencia ON establecimiento (dependencia);
CREATE INDEX idx_simce_rbd_anio ON evaluacion_simce (rbd, anio);
CREATE INDEX idx_simce_grado ON evaluacion_simce (grado);
CREATE INDEX idx_idps_rbd_anio ON indicador_desarrollo_social (rbd, anio);
```

---

## 7. Plan de Trabajo por Fases (Roadmap)

```text
Fase 1: Infraestructura & Ingesta Núcleo SIMCE
├── Despliegue de PostgreSQL 16 en contenedor Docker en servidor 'knossos'
├── Creación del esquema relacional e índices en knossos
├── Descarga manual de bases SIMCE (4° Básico y II° Medio) y libro de códigos
├── Script ETL en Python para normalización y carga masiva inicial
└── Verificación de integridad de datos e índices

Fase 2: Backend API & Frontend Web Local
├── Configuración de contenedor web local (FastAPI + servidor frontend)
├── Endpoints de búsqueda por nombre/RBD y filtros por Comuna y Dependencia
├── Fichas de establecimiento con vista limpia de puntajes y datos de contexto
├── Visualización gráfica con Chart.js (evolución histórica de puntajes)
└── Módulo comparador interactivo entre 2 y 3 establecimientos

Fase 3: Expansión de Procesos (IDPS y Desempeño)
├── Ingesta manual y ETL de bases IDPS (convivencia, autoestima escolar, hábitos)
├── Ingesta y normalización de Categorías de Desempeño de la Agencia
└── Actualización de fichas y comparadores con los nuevos indicadores

Fase 4: Georreferenciación & Exportación
├── Visor territorial interactivo (Leaflet + OpenStreetMap)
└── Generación de reportes resumen descargables en PDF para apoderados
```