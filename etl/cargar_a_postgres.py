"""
Módulo de Ingesta y Carga Masiva a PostgreSQL (Etapa 'Load' del ETL)
====================================================================

Este módulo orquesta la conexión a la base de datos PostgreSQL alojada en el mini
servidor 'knossos' (o entorno local), ejecuta la verificación de tablas e índices,
y realiza la inserción masiva y actualización transaccional (UPSERT) de:
1. Catálogo maestro de establecimientos escolares (`establecimiento`).
2. Evaluaciones y puntajes históricos (`evaluacion_simce`).
3. Promedios comunales oficiales (`promedio_comunal_simce`).
4. Promedios regionales oficiales (`promedio_regional_simce`).

Propiedades Clave:
------------------
- Idempotencia (UPSERT):
  Utiliza sentencias SQL con `ON CONFLICT (...) DO UPDATE` para garantizar que la
  ejecución repetida del script nunca genere registros duplicados y siempre mantenga
  los datos actualizados con la información más reciente.
- Sanitización de Tipos:
  Convierte valores `NaN` de float en `None` (SQL NULL) y asegura conversión estricta
  a enteros de las columnas numéricas para evitar errores de deserialización en psycopg2.
- Transaccionalidad:
  Utiliza context managers de SQLAlchemy (`engine.begin()`) que garantizan commit
  automático en caso de éxito o rollback inmediato si ocurre cualquier fallo.
"""

import sys
import math
from pathlib import Path
from typing import List, Dict, Any, Optional

# Garantizar que la raíz del proyecto esté en sys.path al ejecutarse directamente
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
from sqlalchemy import create_engine, text, Engine
from etl.config import get_database_url
from etl.normalizador import parse_rbd_file, parse_comuna_file, parse_region_file

STAGING_DIR = BASE_DIR / "data" / "staging" / "simce"
INIT_SQL_PATH = BASE_DIR / "deploy" / "knossos" / "init_db.sql"

def init_schema(engine: Engine) -> None:
    """
    Verifica e inicializa el esquema relacional en la base de datos.

    Lee el archivo `deploy/knossos/init_db.sql` y ejecuta secuencialmente las
    sentencias DDL (tablas, extensiones e índices) si aún no existen.

    Args:
        engine (Engine): Instancia del motor SQLAlchemy conectado a PostgreSQL.
    """
    print("Verificando esquema relacional en la base de datos...")
    if not INIT_SQL_PATH.exists():
        print(f"[!] No se encontró el archivo de esquema {INIT_SQL_PATH}")
        return
        
    with open(INIT_SQL_PATH, "r", encoding="utf-8") as f:
        sql_content = f.read()
        
    with engine.begin() as conn:
        for statement in sql_content.split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(text(stmt))
    print("[OK] Tablas e índices inicializados correctamente.")

def clean_records(records: List[Dict[str, Any]], int_keys: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Sanitiza una lista de diccionarios antes de enviarla a PostgreSQL.

    Resuelve dos problemas críticos de compatibilidad entre Pandas y psycopg2:
    1. Reemplaza cualquier `float('nan')` por `None`, permitiendo que PostgreSQL
       lo interprete como `NULL`.
    2. Asegura que las columnas enteras especificadas en `int_keys` sean del tipo
       `int` nativo de Python o `None`, previniendo errores de 'integer out of range'.

    Args:
        records (List[Dict[str, Any]]): Lista de filas generadas por DataFrame.to_dict().
        int_keys (Optional[List[str]]): Lista de nombres de columnas que deben ser enteras.

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios sanitizada y lista para psycopg2.
    """
    int_keys_set = set(int_keys or [])
    for r in records:
        for k, v in r.items():
            if v is not None and isinstance(v, float) and math.isnan(v):
                r[k] = None
            elif k in int_keys_set and v is not None:
                try:
                    r[k] = int(v)
                except (ValueError, TypeError):
                    r[k] = None
    return records

def upsert_establecimientos(engine: Engine, df_est: pd.DataFrame) -> int:
    """
    Inserta o actualiza colegios en la tabla `establecimiento`.

    Si el colegio ya existe (identificado unívocamente por su clave primaria `rbd`),
    actualiza su nombre, comuna, dependencia y fecha de última modificación.

    Args:
        engine (Engine): Motor SQLAlchemy.
        df_est (pd.DataFrame): DataFrame con la información de los establecimientos.

    Returns:
        int: Número de registros procesados.
    """
    if df_est.empty:
        return 0
    raw_records = df_est.to_dict(orient="records")
    records = clean_records(raw_records, [
        "rbd", "cod_region", "cod_provincia", "cod_comuna",
        "cod_deprov", "cod_depe1", "cod_depe2", "cod_rural"
    ])
    sql = text("""
        INSERT INTO establecimiento (
            rbd, dv_rbd, nombre, cod_region, nom_region, cod_provincia, nom_provincia,
            cod_comuna, nom_comuna, cod_deprov, nom_deprov, cod_depe1, cod_depe2,
            dependencia, cod_rural, actualizado_el
        ) VALUES (
            :rbd, :dv_rbd, :nombre, :cod_region, :nom_region, :cod_provincia, :nom_provincia,
            :cod_comuna, :nom_comuna, :cod_deprov, :nom_deprov, :cod_depe1, :cod_depe2,
            :dependencia, :cod_rural, CURRENT_TIMESTAMP
        )
        ON CONFLICT (rbd) DO UPDATE SET
            nombre = EXCLUDED.nombre,
            nom_comuna = EXCLUDED.nom_comuna,
            cod_comuna = EXCLUDED.cod_comuna,
            dependencia = EXCLUDED.dependencia,
            cod_depe2 = EXCLUDED.cod_depe2,
            cod_rural = EXCLUDED.cod_rural,
            actualizado_el = CURRENT_TIMESTAMP;
    """)
    with engine.begin() as conn:
        conn.execute(sql, records)
    return len(records)

def upsert_evaluaciones(engine: Engine, df_eval: pd.DataFrame) -> int:
    """
    Inserta o actualiza evaluaciones en la tabla `evaluacion_simce`.

    La restricción única `(rbd, anio, grado)` previene duplicados. Si ya existe
    la evaluación de un grado para un colegio en ese año, actualiza los puntajes
    y estándares de aprendizaje con la versión más reciente.

    Args:
        engine (Engine): Motor SQLAlchemy.
        df_eval (pd.DataFrame): DataFrame con puntajes y porcentajes EDA.

    Returns:
        int: Número de evaluaciones procesadas.
    """
    if df_eval.empty:
        return 0
    raw_records = df_eval.to_dict(orient="records")
    records = clean_records(raw_records, ["rbd", "anio", "alumnos_lectura", "alumnos_matematica"])
    sql = text("""
        INSERT INTO evaluacion_simce (
            rbd, anio, grado, grupo_nse, alumnos_lectura, alumnos_matematica,
            puntaje_lectura, puntaje_matematica, puntaje_ciencias, puntaje_historia,
            pct_insuficiente_lectura, pct_elemental_lectura, pct_adecuado_lectura,
            pct_insuficiente_matematica, pct_elemental_matematica, pct_adecuado_matematica
        ) VALUES (
            :rbd, :anio, :grado, :grupo_nse, :alumnos_lectura, :alumnos_matematica,
            :puntaje_lectura, :puntaje_matematica, :puntaje_ciencias, :puntaje_historia,
            :pct_insuficiente_lectura, :pct_elemental_lectura, :pct_adecuado_lectura,
            :pct_insuficiente_matematica, :pct_elemental_matematica, :pct_adecuado_matematica
        )
        ON CONFLICT (rbd, anio, grado) DO UPDATE SET
            puntaje_lectura = EXCLUDED.puntaje_lectura,
            puntaje_matematica = EXCLUDED.puntaje_matematica,
            puntaje_ciencias = EXCLUDED.puntaje_ciencias,
            puntaje_historia = EXCLUDED.puntaje_historia,
            alumnos_lectura = EXCLUDED.alumnos_lectura,
            alumnos_matematica = EXCLUDED.alumnos_matematica,
            grupo_nse = EXCLUDED.grupo_nse,
            pct_insuficiente_lectura = EXCLUDED.pct_insuficiente_lectura,
            pct_elemental_lectura = EXCLUDED.pct_elemental_lectura,
            pct_adecuado_lectura = EXCLUDED.pct_adecuado_lectura,
            pct_insuficiente_matematica = EXCLUDED.pct_insuficiente_matematica,
            pct_elemental_matematica = EXCLUDED.pct_elemental_matematica,
            pct_adecuado_matematica = EXCLUDED.pct_adecuado_matematica;
    """)
    with engine.begin() as conn:
        conn.execute(sql, records)
    return len(records)

def upsert_comunales(engine: Engine, df_com: pd.DataFrame) -> int:
    """
    Inserta o actualiza benchmarks comunales en la tabla `promedio_comunal_simce`.

    Clave única: `(cod_comuna, anio, grado)`.

    Args:
        engine (Engine): Motor SQLAlchemy.
        df_com (pd.DataFrame): DataFrame con promedios comunales.

    Returns:
        int: Número de promedios comunales procesados.
    """
    if df_com.empty:
        return 0
    raw_records = df_com.to_dict(orient="records")
    records = clean_records(raw_records, ["cod_comuna", "anio"])
    sql = text("""
        INSERT INTO promedio_comunal_simce (
            cod_comuna, nom_comuna, anio, grado, promedio_lectura, promedio_matematica,
            promedio_ciencias, promedio_historia
        ) VALUES (
            :cod_comuna, :nom_comuna, :anio, :grado, :promedio_lectura, :promedio_matematica,
            :promedio_ciencias, :promedio_historia
        )
        ON CONFLICT (cod_comuna, anio, grado) DO UPDATE SET
            promedio_lectura = EXCLUDED.promedio_lectura,
            promedio_matematica = EXCLUDED.promedio_matematica,
            promedio_ciencias = EXCLUDED.promedio_ciencias,
            promedio_historia = EXCLUDED.promedio_historia;
    """)
    with engine.begin() as conn:
        conn.execute(sql, records)
    return len(records)

def upsert_regionales(engine: Engine, df_reg: pd.DataFrame) -> int:
    """
    Inserta o actualiza benchmarks regionales en la tabla `promedio_regional_simce`.

    Clave única: `(cod_region, anio, grado)`.

    Args:
        engine (Engine): Motor SQLAlchemy.
        df_reg (pd.DataFrame): DataFrame con promedios regionales.

    Returns:
        int: Número de promedios regionales procesados.
    """
    if df_reg.empty:
        return 0
    raw_records = df_reg.to_dict(orient="records")
    records = clean_records(raw_records, ["cod_region", "anio"])
    sql = text("""
        INSERT INTO promedio_regional_simce (
            cod_region, nom_region, anio, grado, promedio_lectura, promedio_matematica,
            promedio_ciencias, promedio_historia
        ) VALUES (
            :cod_region, :nom_region, :anio, :grado, :promedio_lectura, :promedio_matematica,
            :promedio_ciencias, :promedio_historia
        )
        ON CONFLICT (cod_region, anio, grado) DO UPDATE SET
            promedio_lectura = EXCLUDED.promedio_lectura,
            promedio_matematica = EXCLUDED.promedio_matematica,
            promedio_ciencias = EXCLUDED.promedio_ciencias,
            promedio_historia = EXCLUDED.promedio_historia;
    """)
    with engine.begin() as conn:
        conn.execute(sql, records)
    return len(records)

def run_pipeline(years: List[int] = [2023, 2024, 2025]) -> None:
    """
    Función orquestadora principal de la etapa de carga.

    Itera sobre los años especificados, lee los archivos en staging y ejecuta
    la persistencia ordenada (primero colegios, luego evaluaciones y promedios)
    hacia la base de datos PostgreSQL.

    Args:
        years (List[int]): Lista de años a procesar (ej: [2023, 2024, 2025]).
    """
    db_url = get_database_url()
    print(f"Conectando a la base de datos...")
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        print("[OK] Conexión establecida con éxito.")
    except Exception as e:
        print(f"\n[ERROR de Conexión] No se pudo conectar a PostgreSQL:")
        print(f"Detalle: {e}")
        print("\nVerifica que:")
        print("1. El contenedor PostgreSQL en knossos esté corriendo.")
        print("2. Las credenciales en el archivo .env sean las correctas.")
        sys.exit(1)

    init_schema(engine)

    total_est = 0
    total_eval = 0
    total_com = 0
    total_reg = 0

    for year in years:
        year_path = STAGING_DIR / str(year)
        if not year_path.exists():
            print(f"[!] Directorio staging para año {year} no encontrado.")
            continue
            
        print(f"\n==========================================")
        print(f"  Procesando e ingestando Año {year}")
        print(f"==========================================")

        # 1. Archivos RBD (Establecimientos y Evaluaciones)
        rbd_files = list(year_path.glob("**/*rbd*.csv"))
        for f in rbd_files:
            print(f"-> Parseando RBD: {f.name}...")
            df_est, df_eval = parse_rbd_file(f)
            
            # Cargar primero colegios para satisfacer la clave foránea (FK)
            n_est = upsert_establecimientos(engine, df_est)
            n_eval = upsert_evaluaciones(engine, df_eval)
            total_est += n_est
            total_eval += n_eval
            print(f"   Insertados/Actualizados: {n_est} colegios, {n_eval} evaluaciones.")

        # 2. Archivos Comunales
        com_files = list(year_path.glob("**/*comuna*.csv"))
        for f in com_files:
            print(f"-> Parseando Comunal: {f.name}...")
            df_com = parse_comuna_file(f)
            n_com = upsert_comunales(engine, df_com)
            total_com += n_com
            print(f"   Insertados/Actualizados: {n_com} promedios comunales.")

        # 3. Archivos Regionales
        reg_files = list(year_path.glob("**/*region*.csv"))
        for f in reg_files:
            print(f"-> Parseando Regional: {f.name}...")
            df_reg = parse_region_file(f)
            n_reg = upsert_regionales(engine, df_reg)
            total_reg += n_reg
            print(f"   Insertados/Actualizados: {n_reg} promedios regionales.")

    print("\n==========================================")
    print("  RESUMEN DE INGESTA SIMCE")
    print("==========================================")
    print(f"Total registros Establecimientos procesados: {total_est}")
    print(f"Total registros Evaluaciones SIMCE:         {total_eval}")
    print(f"Total registros Promedios Comunales:       {total_com}")
    print(f"Total registros Promedios Regionales:      {total_reg}")
    print("==========================================")

if __name__ == "__main__":
    run_pipeline([2023, 2024, 2025])
