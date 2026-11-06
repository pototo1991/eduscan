import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from etl.config import get_database_url
from etl.normalizador import parse_rbd_file, parse_comuna_file, parse_region_file

BASE_DIR = Path(__file__).resolve().parent.parent
STAGING_DIR = BASE_DIR / "data" / "staging" / "simce"
INIT_SQL_PATH = BASE_DIR / "deploy" / "knossos" / "init_db.sql"

def init_schema(engine):
    """Ejecuta el script SQL inicial si las tablas no existen."""
    print("Verificando esquema relacional en la base de datos...")
    if not INIT_SQL_PATH.exists():
        print(f"[!] No se encontró el archivo {INIT_SQL_PATH}")
        return
        
    with open(INIT_SQL_PATH, "r", encoding="utf-8") as f:
        sql_content = f.read()
        
    with engine.begin() as conn:
        # Ejecutar sentencia por sentencia separadas por ;
        for statement in sql_content.split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(text(stmt))
    print("[OK] Tablas e índices inicializados correctamente.")

def upsert_establecimientos(engine, df_est: pd.DataFrame):
    if df_est.empty:
        return 0
    records = df_est.to_dict(orient="records")
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

def upsert_evaluaciones(engine, df_eval: pd.DataFrame):
    if df_eval.empty:
        return 0
    records = df_eval.to_dict(orient="records")
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

def upsert_comunales(engine, df_com: pd.DataFrame):
    if df_com.empty:
        return 0
    records = df_com.to_dict(orient="records")
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

def upsert_regionales(engine, df_reg: pd.DataFrame):
    if df_reg.empty:
        return 0
    records = df_reg.to_dict(orient="records")
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

def run_pipeline(years=[2023, 2024, 2025]):
    db_url = get_database_url()
    print(f"Conectando a la base de datos...")
    
    try:
        engine = create_engine(db_url)
        # Probar conexión
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

        # 1. Archivos RBD (Establecimientos y Notas)
        rbd_files = list(year_path.glob("**/*rbd*.csv"))
        for f in rbd_files:
            print(f"-> Parseando RBD: {f.name}...")
            df_est, df_eval = parse_rbd_file(f)
            
            # Cargar primero establecimientos para respetar la FK
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
