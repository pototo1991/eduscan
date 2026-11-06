"""
Módulo Extractor de Archivos Comprimidos del SIMCE (Etapa 'Extract' del ETL)
=============================================================================

Este script se encarga de la extracción automatizada y recursiva de los paquetes
de datos publicados por la Agencia de Calidad de la Educación de Chile.

Particularidad de los archivos oficiales:
------------------------------------------
1. Los archivos anuales vienen en formato .rar (ej: 'Simce+2024.rar').
2. Dentro de cada año existen sub-archivos .rar específicos por cada grado escolar
   evaluado (ej: 'Simce 4to basico 2024.rar', 'Simce 2do medio 2024.rar').
3. Dentro de cada grado se encuentran los archivos .csv planos finales:
   - *_rbd_final.csv      -> Resultados a nivel de colegio (RBD)
   - *_comuna_final.csv   -> Promedios comunales oficiales
   - *_region_final.csv   -> Promedios regionales oficiales
   - *_GLOSAS_*.xlsx      -> Diccionario de variables oficial

Compatibilidad multiplataforma (Linux / WSL / Windows):
-------------------------------------------------------
Detecta herramientas de descompresión nativas de Linux (`7z`, `7za`, `unrar`) y,
en caso de ejecutarse dentro de WSL 2, es capaz de invocar de forma transparente
la instalación de `7z.exe` o `WinRAR` ubicada en el sistema anfitrión Windows
convirtiendo las rutas de archivo con `wslpath`.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "simce"
STAGING_DIR = BASE_DIR / "data" / "staging" / "simce"

def find_7z_binary() -> Optional[str]:
    """
    Localiza el binario ejecutable disponible para descomprimir archivos .rar.

    Búsqueda secuencial:
    1. PATH nativo de Linux (`7z`, `7za`, `unrar`).
    2. Rutas estándar en Windows montadas bajo WSL (/mnt/c/Program Files/...).

    Returns:
        Optional[str]: Ruta absoluta hacia el ejecutable encontrado, o None si no existe.
    """
    # 1. Búsqueda en PATH del entorno actual
    for binary in ["7z", "7za", "unrar"]:
        path = shutil.which(binary)
        if path:
            return path
            
    # 2. Búsqueda en Windows (entornos WSL 2)
    windows_paths = [
        "/mnt/c/Program Files/7-Zip/7z.exe",
        "/mnt/c/Program Files (x86)/7-Zip/7z.exe",
        "/mnt/c/Program Files/WinRAR/unrar.exe"
    ]
    for win_path in windows_paths:
        if os.path.exists(win_path):
            return win_path
            
    return None

def run_extraction(archive_path: Path, dest_dir: Path, tool_bin: str) -> bool:
    """
    Ejecuta el comando de descompresión de un archivo individual hacia un directorio destino.

    Si se utiliza un binario de Windows (.exe) desde WSL, se traduce la ruta de archivo
    a formato Windows (UNC o letra de unidad con backslashes) mediante `wslpath -w`.

    Args:
        archive_path (Path): Ruta del archivo comprimido (.rar, .zip, etc.).
        dest_dir (Path): Directorio donde se almacenarán los archivos extraídos.
        tool_bin (str): Ruta del ejecutable de descompresión.

    Returns:
        bool: True si la descompresión fue exitosa (código 0), False en caso de error.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    is_windows_exe = tool_bin.endswith(".exe")
    
    if is_windows_exe:
        def to_win_path(p: Path) -> str:
            res = subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True, check=True)
            return res.stdout.strip()
        
        src_arg = to_win_path(archive_path)
        dest_arg = f"-o{to_win_path(dest_dir)}"
    else:
        src_arg = str(archive_path)
        dest_arg = f"-o{dest_dir}"
        
    cmd = [tool_bin, "x", src_arg, dest_arg, "-y"]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return result.returncode == 0

def extract_year_archives(years: List[int] = [2023, 2024, 2025]) -> List[Path]:
    """
    Procesa recursivamente los archivos comprimidos correspondientes a los años especificados.

    Flujo de ejecución:
    1. Descomprime el archivo .rar principal de cada año en `data/staging/simce/<año>/`.
    2. Identifica los archivos .rar internos por cada grado escolar y los descomprime.
    3. Descubre y retorna la lista de todos los archivos .csv extraídos y listos para normalizar.

    Args:
        years (List[int]): Lista de años a descomprimir (ej: [2023, 2024, 2025]).

    Returns:
        List[Path]: Lista de rutas hacia los archivos CSV encontrados.

    Raises:
        RuntimeError: Si no se encuentra instalado 7-Zip o unrar en el sistema.
    """
    tool_bin = find_7z_binary()
    if not tool_bin:
        raise RuntimeError(
            "No se encontró 7-Zip ni unrar para descomprimir los archivos .rar. "
            "Asegúrate de tener 7-Zip instalado en tu equipo."
        )

    extracted_csvs: List[Path] = []
    
    print(f"Herramienta de descompresión detectada: {tool_bin}")
    print(f"Años a procesar: {years}")
    
    for year in years:
        year_staging = STAGING_DIR / str(year)
        
        # Buscar el archivo del año en data/raw/simce/
        candidates = list(RAW_DIR.glob(f"*{year}*.rar"))
        if not candidates:
            print(f"[!] No se encontró archivo .rar para el año {year}")
            continue
            
        outer_rar = candidates[0]
        print(f"\n--- Descomprimiendo contenedor principal {year}: {outer_rar.name} ---")
        run_extraction(outer_rar, year_staging, tool_bin)
        
        # Buscar y extraer archivos .rar anidados (por grado escolar)
        inner_rars = list(year_staging.glob("*.rar"))
        for inner_rar in inner_rars:
            print(f"  -> Extrayendo grado: {inner_rar.name}")
            run_extraction(inner_rar, year_staging, tool_bin)
            
        # Recolectar todos los CSVs generados para este año
        csvs = list(year_staging.rglob("*.csv"))
        print(f"  [OK] Año {year}: {len(csvs)} archivos CSV encontrados.")
        extracted_csvs.extend(csvs)
        
    return extracted_csvs

if __name__ == "__main__":
    csvs = extract_year_archives([2023, 2024, 2025])
    print(f"\nTotal de archivos CSV disponibles para ingesta: {len(csvs)}")
