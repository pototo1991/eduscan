import re
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

DEPENDENCIA_MAP = {
    1: "Municipal",
    2: "Particular Subvencionado",
    3: "Particular Pagado",
    4: "Administración Delegada",
    5: "Servicio Local de Educación Pública (SLEP)"
}

def clean_numeric(val):
    """Convierte cadenas con comas o vacíos a números flotantes limpios."""
    if pd.isna(val) or val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val) if not np.isnan(val) else None
    
    val_str = str(val).strip().replace(",", ".")
    try:
        return float(val_str)
    except ValueError:
        return None

def clean_int(val):
    num = clean_numeric(val)
    return int(num) if num is not None else None

def parse_rbd_file(file_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Lee un archivo de establecimientos (RBD) del SIMCE y retorna:
    - df_establecimientos: catálogo maestro actualizado
    - df_evaluaciones: registros de puntajes para la tabla evaluacion_simce
    """
    df_raw = pd.read_csv(file_path, sep=";", encoding="latin-1", low_memory=False)
    
    # Normalizar nombres de columnas a minúsculas
    df_raw.columns = [c.strip().lower() for c in df_raw.columns]
    
    # Detectar grado y año
    if "grado" in df_raw.columns and not df_raw["grado"].isna().all():
        grado = str(df_raw["grado"].dropna().iloc[0]).lower().strip()
    else:
        # Extraer del nombre del archivo (ej: simce4b2024 -> 4b)
        m = re.search(r"simce([0-9][bm])", file_path.name.lower())
        grado = m.group(1) if m else "4b"
        
    if "agno" in df_raw.columns and not df_raw["agno"].isna().all():
        anio = int(df_raw["agno"].dropna().iloc[0])
    else:
        m = re.search(r"20[12][0-9]", file_path.name)
        anio = int(m.group(0)) if m else 2024

    # 1. Extraer Establecimientos (Master)
    est_cols = {
        "rbd": "rbd",
        "dvrbd": "dv_rbd",
        "nom_rbd": "nombre",
        "cod_reg_rbd": "cod_region",
        "nom_reg_rbd": "nom_region",
        "cod_pro_rbd": "cod_provincia",
        "nom_pro_rbd": "nom_provincia",
        "cod_com_rbd": "cod_comuna",
        "nom_com_rbd": "nom_comuna",
        "cod_deprov_rbd": "cod_deprov",
        "nom_deprov_rbd": "nom_deprov",
        "cod_depe1": "cod_depe1",
        "cod_depe2": "cod_depe2",
        "cod_rural_rbd": "cod_rural"
    }
    
    est_data = []
    for _, row in df_raw.iterrows():
        rbd_val = clean_int(row.get("rbd"))
        if not rbd_val:
            continue
            
        depe2 = clean_int(row.get("cod_depe2"))
        est_data.append({
            "rbd": rbd_val,
            "dv_rbd": str(row.get("dvrbd", "")).strip(),
            "nombre": str(row.get("nom_rbd", "")).strip().title(),
            "cod_region": clean_int(row.get("cod_reg_rbd")),
            "nom_region": str(row.get("nom_reg_rbd", "")).strip().title(),
            "cod_provincia": clean_int(row.get("cod_pro_rbd")),
            "nom_provincia": str(row.get("nom_pro_rbd", "")).strip().title(),
            "cod_comuna": clean_int(row.get("cod_com_rbd")),
            "nom_comuna": str(row.get("nom_com_rbd", "")).strip().title(),
            "cod_deprov": clean_int(row.get("cod_deprov_rbd")),
            "nom_deprov": str(row.get("nom_deprov_rbd", "")).strip().title(),
            "cod_depe1": clean_int(row.get("cod_depe1")),
            "cod_depe2": depe2,
            "dependencia": DEPENDENCIA_MAP.get(depe2, "Otro"),
            "cod_rural": clean_int(row.get("cod_rural_rbd"))
        })
        
    df_est = pd.DataFrame(est_data).drop_duplicates(subset=["rbd"])

    # 2. Extraer Evaluaciones SIMCE
    eval_data = []
    for _, row in df_raw.iterrows():
        rbd_val = clean_int(row.get("rbd"))
        if not rbd_val:
            continue
            
        # Buscar dinámicamente columnas de lectura, matemática, ciencias, historia
        p_lect = clean_numeric(row.get(f"prom_lect{grado}_rbd", row.get("prom_lect_rbd")))
        p_mate = clean_numeric(row.get(f"prom_mate{grado}_rbd", row.get("prom_mate_rbd")))
        p_cien = clean_numeric(row.get(f"prom_csnat{grado}_rbd", row.get(f"prom_cien{grado}_rbd")))
        p_hist = clean_numeric(row.get(f"prom_soc{grado}_rbd", row.get(f"prom_hist{grado}_rbd")))
        
        n_lect = clean_int(row.get(f"nalu_lect{grado}_rbd", row.get("nalu_lect_rbd")))
        n_mate = clean_int(row.get(f"nalu_mate{grado}_rbd", row.get("nalu_mate_rbd")))
        
        # Estándares de aprendizaje
        ins_lect = clean_numeric(row.get(f"palu_eda_ins_lect{grado}_rbd"))
        ele_lect = clean_numeric(row.get(f"palu_eda_ele_lect{grado}_rbd"))
        ade_lect = clean_numeric(row.get(f"palu_eda_ade_lect{grado}_rbd"))
        
        ins_mate = clean_numeric(row.get(f"palu_eda_ins_mate{grado}_rbd"))
        ele_mate = clean_numeric(row.get(f"palu_eda_ele_mate{grado}_rbd"))
        ade_mate = clean_numeric(row.get(f"palu_eda_ade_mate{grado}_rbd"))

        eval_data.append({
            "rbd": rbd_val,
            "anio": anio,
            "grado": grado,
            "grupo_nse": str(row.get("cod_grupo", "")).strip(),
            "alumnos_lectura": n_lect,
            "alumnos_matematica": n_mate,
            "puntaje_lectura": p_lect,
            "puntaje_matematica": p_mate,
            "puntaje_ciencias": p_cien,
            "puntaje_historia": p_hist,
            "pct_insuficiente_lectura": ins_lect,
            "pct_elemental_lectura": ele_lect,
            "pct_adecuado_lectura": ade_lect,
            "pct_insuficiente_matematica": ins_mate,
            "pct_elemental_matematica": ele_mate,
            "pct_adecuado_matematica": ade_mate
        })
        
    df_eval = pd.DataFrame(eval_data).drop_duplicates(subset=["rbd", "anio", "grado"])
    return df_est, df_eval

def parse_comuna_file(file_path: Path) -> pd.DataFrame:
    """Lee y normaliza promedios comunales precalculados."""
    df_raw = pd.read_csv(file_path, sep=";", encoding="latin-1", low_memory=False)
    df_raw.columns = [c.strip().lower() for c in df_raw.columns]
    
    # Detectar grado y año
    if "grado" in df_raw.columns and not df_raw["grado"].isna().all():
        grado = str(df_raw["grado"].dropna().iloc[0]).lower().strip()
    else:
        m = re.search(r"simce([0-9][bm])", file_path.name.lower())
        grado = m.group(1) if m else "4b"
        
    if "agno" in df_raw.columns and not df_raw["agno"].isna().all():
        anio = int(df_raw["agno"].dropna().iloc[0])
    else:
        m = re.search(r"20[12][0-9]", file_path.name)
        anio = int(m.group(0)) if m else 2024
        
    comuna_data = []
    for _, row in df_raw.iterrows():
        cod_com = clean_int(row.get("cod_com", row.get("cod_com_rbd", row.get("cod_comuna"))))
        if not cod_com:
            continue
            
        nom_com = str(row.get("nom_com", row.get("nom_com_rbd", row.get("nom_comuna", "")))).strip().title()
        p_lect = clean_numeric(row.get(f"prom_lect{grado}_com", row.get(f"prom_lect{grado}_rbd", row.get("prom_lect_com"))))
        p_mate = clean_numeric(row.get(f"prom_mate{grado}_com", row.get(f"prom_mate{grado}_rbd", row.get("prom_mate_com"))))
        p_cien = clean_numeric(row.get(f"prom_csnat{grado}_com", row.get(f"prom_cien{grado}_com")))
        p_hist = clean_numeric(row.get(f"prom_soc{grado}_com", row.get(f"prom_hist{grado}_com")))
        
        comuna_data.append({
            "cod_comuna": cod_com,
            "nom_comuna": nom_com,
            "anio": anio,
            "grado": grado,
            "promedio_lectura": p_lect,
            "promedio_matematica": p_mate,
            "promedio_ciencias": p_cien,
            "promedio_historia": p_hist
        })
        
    return pd.DataFrame(comuna_data).drop_duplicates(subset=["cod_comuna", "anio", "grado"])

def parse_region_file(file_path: Path) -> pd.DataFrame:
    """Lee y normaliza promedios regionales precalculados."""
    df_raw = pd.read_csv(file_path, sep=";", encoding="latin-1", low_memory=False)
    df_raw.columns = [c.strip().lower() for c in df_raw.columns]
    
    if "grado" in df_raw.columns and not df_raw["grado"].isna().all():
        grado = str(df_raw["grado"].dropna().iloc[0]).lower().strip()
    else:
        m = re.search(r"simce([0-9][bm])", file_path.name.lower())
        grado = m.group(1) if m else "4b"
        
    if "agno" in df_raw.columns and not df_raw["agno"].isna().all():
        anio = int(df_raw["agno"].dropna().iloc[0])
    else:
        m = re.search(r"20[12][0-9]", file_path.name)
        anio = int(m.group(0)) if m else 2024
        
    reg_data = []
    for _, row in df_raw.iterrows():
        cod_reg = clean_int(row.get("cod_reg", row.get("cod_reg_rbd", row.get("cod_region"))))
        if not cod_reg:
            continue
            
        nom_reg = str(row.get("nom_reg", row.get("nom_reg_rbd", row.get("nom_region", "")))).strip().title()
        p_lect = clean_numeric(row.get(f"prom_lect{grado}_reg", row.get(f"prom_lect{grado}_rbd", row.get("prom_lect_reg"))))
        p_mate = clean_numeric(row.get(f"prom_mate{grado}_reg", row.get(f"prom_mate{grado}_rbd", row.get("prom_mate_reg"))))
        p_cien = clean_numeric(row.get(f"prom_csnat{grado}_reg", row.get(f"prom_cien{grado}_reg")))
        p_hist = clean_numeric(row.get(f"prom_soc{grado}_reg", row.get(f"prom_hist{grado}_reg")))
        
        reg_data.append({
            "cod_region": cod_reg,
            "nom_region": nom_reg,
            "anio": anio,
            "grado": grado,
            "promedio_lectura": p_lect,
            "promedio_matematica": p_mate,
            "promedio_ciencias": p_cien,
            "promedio_historia": p_hist
        })
        
    return pd.DataFrame(reg_data).drop_duplicates(subset=["cod_region", "anio", "grado"])
