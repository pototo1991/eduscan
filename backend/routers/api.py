"""
Endpoints de la API REST de EduScan
====================================
"""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db

router = APIRouter(prefix="/api", tags=["EduScan API"])

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retorna estadísticas globales de la plataforma."""
    total_colegios = db.execute(text("SELECT count(*) FROM establecimiento;")).scalar() or 0
    total_evals = db.execute(text("SELECT count(*) FROM evaluacion_simce;")).scalar() or 0
    total_comunas = db.execute(text("SELECT count(DISTINCT cod_comuna) FROM establecimiento;")).scalar() or 0
    
    # Promedio nacional general
    avg_scores = db.execute(text("""
        SELECT 
            ROUND(AVG(puntaje_lectura)::numeric, 1) as avg_lectura,
            ROUND(AVG(puntaje_matematica)::numeric, 1) as avg_matematica
        FROM evaluacion_simce
        WHERE anio = 2024 AND grado = '4b';
    """)).mappings().first()

    return {
        "total_establecimientos": total_colegios,
        "total_evaluaciones": total_evals,
        "total_comunas": total_comunas,
        "promedio_nacional_4b_2024": {
            "lectura": float(avg_scores["avg_lectura"]) if avg_scores and avg_scores["avg_lectura"] else 260.0,
            "matematica": float(avg_scores["avg_matematica"]) if avg_scores and avg_scores["avg_matematica"] else 250.0
        }
    }

@router.get("/filtros")
def get_filtros(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retorna listas de opciones para los selectores de búsqueda."""
    regiones = db.execute(text("""
        SELECT DISTINCT nom_region, cod_region 
        FROM establecimiento 
        WHERE nom_region IS NOT NULL AND nom_region != ''
        ORDER BY cod_region;
    """)).mappings().all()

    comunas = db.execute(text("""
        SELECT DISTINCT nom_comuna, cod_comuna, nom_region
        FROM establecimiento 
        WHERE nom_comuna IS NOT NULL AND nom_comuna != ''
        ORDER BY nom_comuna;
    """)).mappings().all()

    dependencias = db.execute(text("""
        SELECT DISTINCT dependencia 
        FROM establecimiento 
        WHERE dependencia IS NOT NULL AND dependencia != ''
        ORDER BY dependencia;
    """)).scalars().all()

    return {
        "regiones": [{"codigo": r["cod_region"], "nombre": r["nom_region"]} for r in regiones],
        "comunas": [{"codigo": c["cod_comuna"], "nombre": c["nom_comuna"], "region": c["nom_region"]} for c in comunas],
        "dependencias": dependencias,
        "grados": [
            {"codigo": "4b", "nombre": "4° Básico"},
            {"codigo": "6b", "nombre": "6° Básico"},
            {"codigo": "8b", "nombre": "8° Básico"},
            {"codigo": "2m", "nombre": "II° Medio"}
        ],
        "anios": [2025, 2024, 2023]
    }

@router.get("/colegios")
def buscar_colegios(
    q: Optional[str] = Query(None, description="Búsqueda por nombre o RBD"),
    comuna: Optional[str] = Query(None, description="Nombre de comuna"),
    region: Optional[str] = Query(None, description="Nombre de región"),
    dependencia: Optional[str] = Query(None, description="Dependencia administrativa"),
    grado: str = Query("4b", description="Grado escolar para mostrar puntajes"),
    anio: int = Query(2024, description="Año de evaluación para mostrar puntajes"),
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Buscador multicriterio de colegios con puntajes del grado y año seleccionados."""
    where_clauses = ["1=1"]
    params = {
        "grado": grado,
        "anio": anio,
        "limit": limit,
        "offset": offset
    }

    if q and q.strip():
        q_clean = q.strip()
        if q_clean.isdigit():
            where_clauses.append("(e.rbd = :rbd_exact OR e.nombre ILIKE :q_text)")
            params["rbd_exact"] = int(q_clean)
            params["q_text"] = f"%{q_clean}%"
        else:
            where_clauses.append("unaccent(e.nombre) ILIKE unaccent(:q_text)")
            params["q_text"] = f"%{q_clean}%"

    if comuna and comuna != "todas":
        where_clauses.append("e.nom_comuna = :comuna")
        params["comuna"] = comuna

    if region and region != "todas":
        where_clauses.append("e.nom_region = :region")
        params["region"] = region

    if dependencia and dependencia != "todas":
        where_clauses.append("e.dependencia = :dependencia")
        params["dependencia"] = dependencia

    where_sql = " AND ".join(where_clauses)

    # 1. Conteo total de coincidencias
    count_sql = text(f"SELECT count(*) FROM establecimiento e WHERE {where_sql};")
    total = db.execute(count_sql, params).scalar() or 0

    # 2. Obtener lista paginada junto con puntajes SIMCE del año/grado elegido
    query_sql = text(f"""
        SELECT 
            e.rbd, e.dv_rbd, e.nombre, e.nom_comuna, e.nom_region, e.dependencia, e.es_urbano,
            s.anio, s.grado, s.grupo_nse,
            s.puntaje_lectura, s.puntaje_matematica, s.puntaje_ciencias, s.puntaje_historia,
            s.pct_adecuado_lectura, s.pct_adecuado_matematica,
            c.promedio_lectura as comuna_lectura,
            c.promedio_matematica as comuna_matematica
        FROM establecimiento e
        LEFT JOIN evaluacion_simce s 
            ON e.rbd = s.rbd AND s.anio = :anio AND s.grado = :grado
        LEFT JOIN promedio_comunal_simce c
            ON e.cod_comuna = c.cod_comuna AND c.anio = :anio AND c.grado = :grado
        WHERE {where_sql}
        ORDER BY 
            CASE WHEN s.puntaje_matematica IS NOT NULL THEN 0 ELSE 1 END,
            s.puntaje_matematica DESC NULLS LAST,
            e.nombre ASC
        LIMIT :limit OFFSET :offset;
    """)

    rows = db.execute(query_sql, params).mappings().all()

    colegios = []
    for r in rows:
        colegios.append({
            "rbd": r["rbd"],
            "dv_rbd": r["dv_rbd"],
            "nombre": r["nombre"],
            "comuna": r["nom_comuna"],
            "region": r["nom_region"],
            "dependencia": r["dependencia"],
            "es_urbano": r["es_urbano"],
            "evaluacion": {
                "anio": r["anio"] or anio,
                "grado": r["grado"] or grado,
                "grupo_nse": r["grupo_nse"],
                "puntaje_lectura": float(r["puntaje_lectura"]) if r["puntaje_lectura"] is not None else None,
                "puntaje_matematica": float(r["puntaje_matematica"]) if r["puntaje_matematica"] is not None else None,
                "puntaje_ciencias": float(r["puntaje_ciencias"]) if r["puntaje_ciencias"] is not None else None,
                "puntaje_historia": float(r["puntaje_historia"]) if r["puntaje_historia"] is not None else None,
                "pct_adecuado_lectura": float(r["pct_adecuado_lectura"]) if r["pct_adecuado_lectura"] is not None else None,
                "pct_adecuado_matematica": float(r["pct_adecuado_matematica"]) if r["pct_adecuado_matematica"] is not None else None,
                "comuna_promedio_lectura": float(r["comuna_lectura"]) if r["comuna_lectura"] is not None else None,
                "comuna_promedio_matematica": float(r["comuna_matematica"]) if r["comuna_matematica"] is not None else None
            } if r["puntaje_lectura"] is not None or r["puntaje_matematica"] is not None else None
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "filtros_aplicados": {
            "q": q,
            "comuna": comuna,
            "region": region,
            "dependencia": dependencia,
            "grado": grado,
            "anio": anio
        },
        "resultados": colegios
    }

@router.get("/colegios/{rbd}")
def obtener_ficha_colegio(rbd: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retorna la ficha escolar completa con todo el historial SIMCE y benchmarks comunales/regionales."""
    # 1. Datos del colegio
    colegio = db.execute(text("""
        SELECT * FROM establecimiento WHERE rbd = :rbd;
    """), {"rbd": rbd}).mappings().first()

    if not colegio:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")

    # 2. Historial de evaluaciones SIMCE del colegio
    evaluaciones = db.execute(text("""
        SELECT 
            anio, grado, grupo_nse, alumnos_lectura, alumnos_matematica,
            puntaje_lectura, puntaje_matematica, puntaje_ciencias, puntaje_historia,
            pct_insuficiente_lectura, pct_elemental_lectura, pct_adecuado_lectura,
            pct_insuficiente_matematica, pct_elemental_matematica, pct_adecuado_matematica
        FROM evaluacion_simce
        WHERE rbd = :rbd
        ORDER BY anio ASC, grado ASC;
    """), {"rbd": rbd}).mappings().all()

    # 3. Promedios comunales para comparar
    comunales = db.execute(text("""
        SELECT anio, grado, promedio_lectura, promedio_matematica, promedio_ciencias, promedio_historia
        FROM promedio_comunal_simce
        WHERE cod_comuna = :cod_comuna
        ORDER BY anio ASC, grado ASC;
    """), {"cod_comuna": colegio["cod_comuna"]}).mappings().all()

    # 4. Promedios regionales
    regionales = db.execute(text("""
        SELECT anio, grado, promedio_lectura, promedio_matematica, promedio_ciencias, promedio_historia
        FROM promedio_regional_simce
        WHERE cod_region = :cod_region
        ORDER BY anio ASC, grado ASC;
    """), {"cod_region": colegio["cod_region"]}).mappings().all()

    return {
        "establecimiento": {
            "rbd": colegio["rbd"],
            "dv_rbd": colegio["dv_rbd"],
            "nombre": colegio["nombre"],
            "region": colegio["nom_region"],
            "provincia": colegio["nom_provincia"],
            "comuna": colegio["nom_comuna"],
            "cod_comuna": colegio["cod_comuna"],
            "dependencia": colegio["dependencia"],
            "es_urbano": colegio["es_urbano"],
            "latitud": float(colegio["latitud"]) if colegio["latitud"] else None,
            "longitud": float(colegio["longitud"]) if colegio["longitud"] else None
        },
        "historial_simce": [dict(ev) for ev in evaluaciones],
        "benchmarks_comunales": [dict(c) for c in comunales],
        "benchmarks_regionales": [dict(r) for r in regionales]
    }

@router.get("/comparar")
def comparar_colegios(
    rbds: str = Query(..., description="Códigos RBD separados por coma (ej: 14324,6830)"),
    grado: str = Query("4b", description="Grado para la comparativa"),
    anio: int = Query(2024, description="Año para la comparativa"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Compara lado a lado hasta 3 colegios en un grado y año específicos."""
    rbd_list = [int(r.strip()) for r in rbds.split(",") if r.strip().isdigit()][:3]
    if not rbd_list:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un código RBD válido")

    colegios_data = []
    for rbd in rbd_list:
        data = db.execute(text("""
            SELECT 
                e.rbd, e.nombre, e.nom_comuna, e.nom_region, e.dependencia,
                s.anio, s.grado, s.grupo_nse,
                s.puntaje_lectura, s.puntaje_matematica, s.puntaje_ciencias, s.puntaje_historia,
                s.pct_insuficiente_lectura, s.pct_elemental_lectura, s.pct_adecuado_lectura,
                s.pct_insuficiente_matematica, s.pct_elemental_matematica, s.pct_adecuado_matematica,
                c.promedio_lectura as comuna_lectura,
                c.promedio_matematica as comuna_matematica
            FROM establecimiento e
            LEFT JOIN evaluacion_simce s 
                ON e.rbd = s.rbd AND s.anio = :anio AND s.grado = :grado
            LEFT JOIN promedio_comunal_simce c 
                ON e.cod_comuna = c.cod_comuna AND c.anio = :anio AND c.grado = :grado
            WHERE e.rbd = :rbd;
        """), {"rbd": rbd, "anio": anio, "grado": grado}).mappings().first()

        if data:
            colegios_data.append(dict(data))

    return {
        "anio": anio,
        "grado": grado,
        "colegios": colegios_data
    }
