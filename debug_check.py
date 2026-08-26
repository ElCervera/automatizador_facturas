import os
import sys
from utils.config import CARPETA_RESULTADOS

print("=== DIAGNÓSTICO DE RUTAS Y ARCHIVOS ===")
print(f"CWD (Directorio actual): {os.getcwd()}")
print(f"CARPETA_RESULTADOS (desde config): {CARPETA_RESULTADOS}")

if os.path.exists(CARPETA_RESULTADOS):
    print(f"[OK] La carpeta existe.")
    archivos = os.listdir(CARPETA_RESULTADOS)
    print(f"Contenido de la carpeta ({len(archivos)} archivos):")
    for f in archivos:
        ruta_completa = os.path.join(CARPETA_RESULTADOS, f)
        es_archivo = os.path.isfile(ruta_completa)
        print(f" - {f} [{'ARCHIVO' if es_archivo else 'DIR'}]")
        if "consolidado" in f:
            print(f"   -> ¡Este archivo debería ser detectado por el filtro!")
else:
    print(f"[ERROR] La carpeta NO existe.")

print("=======================================")
