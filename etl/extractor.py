import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "simce"
STAGING_DIR = BASE_DIR / "data" / "staging" / "simce"

def find_7z_binary() -> Optional[str]:
    """Detecta el ejecutable de 7-Zip o unrar disponible."""
    # 1. PATH nativo
    for binary in ["7z", "7za", "unrar"]:
        path = shutil.which(binary)
        if path:
            return path
            
    # 2. WSL con 7-Zip instalado en Windows
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
    """Extrae un archivo comprimido hacia el directorio destino."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Si estamos invocando un binario de Windows (.exe) desde WSL, convertimos las rutas con wslpath
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
    """Extrae recursivamente los archivos de los años seleccionados."""
    tool_bin = find_7z_binary()
    if not tool_bin:
        raise RuntimeError("No se encontró 7-Zip ni unrar para descomprimir los archivos .rar")

    extracted_csvs: List[Path] = []
    
    print(f"Herramienta de descompresión detectada: {tool_bin}")
    print(f"Años a procesar: {years}")
    
    for year in years:
        year_staging = STAGING_DIR / str(year)
        
        # Buscar el archivo del año
        candidates = list(RAW_DIR.glob(f"*{year}*.rar"))
        if not candidates:
            print(f"[!] No se encontró archivo .rar para el año {year}")
            continue
            
        outer_rar = candidates[0]
        print(f"\n--- Descomprimiendo contenedor principal {year}: {outer_rar.name} ---")
        run_extraction(outer_rar, year_staging, tool_bin)
        
        # Buscar archivos .rar anidados (por grado)
        inner_rars = list(year_staging.glob("*.rar"))
        for inner_rar in inner_rars:
            print(f"  -> Extrayendo grado: {inner_rar.name}")
            run_extraction(inner_rar, year_staging, tool_bin)
            
        # Recolectar todos los CSVs generados
        csvs = list(year_staging.rglob("*.csv"))
        print(f"  [OK] Año {year}: {len(csvs)} archivos CSV encontrados.")
        extracted_csvs.extend(csvs)
        
    return extracted_csvs

if __name__ == "__main__":
    csvs = extract_year_archives([2023, 2024, 2025])
    print(f"\nTotal de archivos CSV disponibles para ingesta: {len(csvs)}")
