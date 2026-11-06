-- Inicialización de Base de Datos para EduScan en servidor knossos

-- 1. Habilitar extensión para ignorar tildes en búsquedas
CREATE EXTENSION IF NOT EXISTS unaccent;

-- 2. Tabla de Establecimientos Educacionales (Catálogo Maestro)
CREATE TABLE IF NOT EXISTS establecimiento (
    rbd INTEGER PRIMARY KEY,
    dv_rbd VARCHAR(2),
    nombre VARCHAR(255) NOT NULL,
    cod_region INTEGER,
    nom_region VARCHAR(100),
    cod_provincia INTEGER,
    nom_provincia VARCHAR(100),
    cod_comuna INTEGER,
    nom_comuna VARCHAR(100) NOT NULL,
    cod_deprov INTEGER,
    nom_deprov VARCHAR(100),
    cod_depe1 INTEGER,
    cod_depe2 INTEGER,
    dependencia VARCHAR(100),
    cod_rural INTEGER, -- 1: Urbano, 2: Rural
    es_urbano BOOLEAN GENERATED ALWAYS AS (cod_rural = 1) STORED,
    latitud NUMERIC(10, 7),
    longitud NUMERIC(10, 7),
    creado_el TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_el TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabla de Resultados SIMCE por Establecimiento (RBD)
CREATE TABLE IF NOT EXISTS evaluacion_simce (
    id SERIAL PRIMARY KEY,
    rbd INTEGER NOT NULL REFERENCES establecimiento(rbd) ON DELETE CASCADE,
    anio INTEGER NOT NULL,
    grado VARCHAR(10) NOT NULL, -- '4b', '6b', '8b', '2m'
    grupo_nse VARCHAR(10),       -- Grupo socioeconómico: A, B, C, D, E o código
    alumnos_lectura INTEGER,
    alumnos_matematica INTEGER,
    puntaje_lectura NUMERIC(6, 2),
    puntaje_matematica NUMERIC(6, 2),
    puntaje_ciencias NUMERIC(6, 2),
    puntaje_historia NUMERIC(6, 2),
    -- Estándares de Aprendizaje (% Insuficiente, Elemental, Adecuado)
    pct_insuficiente_lectura NUMERIC(5, 2),
    pct_elemental_lectura NUMERIC(5, 2),
    pct_adecuado_lectura NUMERIC(5, 2),
    pct_insuficiente_matematica NUMERIC(5, 2),
    pct_elemental_matematica NUMERIC(5, 2),
    pct_adecuado_matematica NUMERIC(5, 2),
    creado_el TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_simce_rbd_anio_grado UNIQUE (rbd, anio, grado)
);

-- 4. Tabla de Promedios Comunales SIMCE (Benchmark para comparativas)
CREATE TABLE IF NOT EXISTS promedio_comunal_simce (
    id SERIAL PRIMARY KEY,
    cod_comuna INTEGER NOT NULL,
    nom_comuna VARCHAR(100) NOT NULL,
    anio INTEGER NOT NULL,
    grado VARCHAR(10) NOT NULL,
    promedio_lectura NUMERIC(6, 2),
    promedio_matematica NUMERIC(6, 2),
    promedio_ciencias NUMERIC(6, 2),
    promedio_historia NUMERIC(6, 2),
    CONSTRAINT uq_promedio_comuna_anio_grado UNIQUE (cod_comuna, anio, grado)
);

-- 5. Tabla de Promedios Regionales SIMCE (Benchmark para comparativas)
CREATE TABLE IF NOT EXISTS promedio_regional_simce (
    id SERIAL PRIMARY KEY,
    cod_region INTEGER NOT NULL,
    nom_region VARCHAR(100) NOT NULL,
    anio INTEGER NOT NULL,
    grado VARCHAR(10) NOT NULL,
    promedio_lectura NUMERIC(6, 2),
    promedio_matematica NUMERIC(6, 2),
    promedio_ciencias NUMERIC(6, 2),
    promedio_historia NUMERIC(6, 2),
    CONSTRAINT uq_promedio_region_anio_grado UNIQUE (cod_region, anio, grado)
);

-- 6. Índices para acelerar búsquedas y filtros
CREATE INDEX IF NOT EXISTS idx_est_nombre ON establecimiento USING btree (nombre);
CREATE INDEX IF NOT EXISTS idx_est_comuna ON establecimiento (nom_comuna);
CREATE INDEX IF NOT EXISTS idx_est_cod_comuna ON establecimiento (cod_comuna);
CREATE INDEX IF NOT EXISTS idx_est_region ON establecimiento (nom_region);
CREATE INDEX IF NOT EXISTS idx_est_depe2 ON establecimiento (cod_depe2);

CREATE INDEX IF NOT EXISTS idx_simce_rbd_anio ON evaluacion_simce (rbd, anio);
CREATE INDEX IF NOT EXISTS idx_simce_grado ON evaluacion_simce (grado);
CREATE INDEX IF NOT EXISTS idx_simce_anio_grado ON evaluacion_simce (anio, grado);
