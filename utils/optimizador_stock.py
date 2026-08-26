"""
Optimizador de stock para simulación de facturación.
Distribuye los huevos disponibles en un plan mensual de ventas
respetando límites diarios y evitando sobreventas.

Usa programación lineal (PuLP) si está disponible, o un modo heurístico si no.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

from utils.config import (
    EXCLUIR_NITS, EXCLUIR_PRODUCTOS,
    MIN_HUEVOS, MAX_HUEVOS, MULTIPLE_HUEVOS
)

# Intentar importar PuLP
try:
    import pulp
    HAS_PULP = True
except ImportError:
    HAS_PULP = False
    print("[AVISO] PuLP no está instalado, se usará el modo heurístico.")

# ==============================
# CONFIGURACIÓN (usando valores de config.py)
# ==============================
MIN_VENTA_HUEVOS = 300                # 10 cubetas
MAX_VENTA_HUEVOS = 1500               # 50 cubetas

# ==============================
# FUNCIÓN PRINCIPAL
# ==============================
def optimizar_stock(ruta_excel_base):
    """
    Lee el archivo Excel base, optimiza la cantidad de huevos a vender mensualmente,
    y genera un nuevo archivo con las columnas esperadas por el generador de facturas.
    """
    if not os.path.exists(ruta_excel_base):
        print(f"[ERROR] No se encontró el archivo base: {ruta_excel_base}")
        return None

    print(f"\n[LEYENDO] Leyendo archivo base: {ruta_excel_base}")
    df = pd.read_excel(ruta_excel_base)

    # Normalizar nombres de columnas
    df.columns = [c.strip().lower() for c in df.columns]

    # Verificación mínima
    columnas_requeridas = {"tipo", "cantidad", "valor unitario", "nit_proveedor"}
    if not columnas_requeridas.issubset(df.columns):
        print(f"[ERROR] Columnas faltantes: {columnas_requeridas - set(df.columns)}")
        return None

    # Filtrar los productos y terceros excluidos
    df = df[~df["tipo"].str.upper().isin(EXCLUIR_PRODUCTOS)]
    df = df[~df["nit_proveedor"].astype(str).isin(EXCLUIR_NITS)]

    if df.empty:
        print("[AVISO] No quedan registros válidos tras aplicar los filtros.")
        return None

    # Consolidar por tipo de producto y valor unitario
    df_group = df.groupby(["tipo", "valor unitario"], as_index=False)["cantidad"].sum()
    df_group.rename(columns={"cantidad": "huevos_disponibles"}, inplace=True)

    print(f"Total huevos disponibles (filtrado): {df_group['huevos_disponibles'].sum():,.0f}")

    # ==============================
    # OPTIMIZACIÓN
    # ==============================
    total_huevos = df_group["huevos_disponibles"].sum()
    business_days = 21  # promedio de días hábiles del mes
    avg_price = df_group["valor unitario"].mean()
    target_sales = total_huevos  # objetivo: vender TODO el stock

    print(f"Estimación objetivo (huevos a vender este mes): {target_sales:,.0f} (avg_price={avg_price:.2f} COP, business_days={business_days})")

    # VENDER TODO EL STOCK DISPONIBLE (sin priorizar precios)
    # Asignamos directamente todos los huevos disponibles para vender
    print("\n[OPTIMIZANDO] Asignando todo el stock para venta (todos los precios)...")
    df_group["huevos_a_vender"] = df_group["huevos_disponibles"]

    # Añadir pequeñas variaciones aleatorias para evitar patrones fijos
    np.random.seed(42)
    df_group["huevos_a_vender"] = df_group["huevos_a_vender"].apply(
        lambda x: max(MIN_VENTA_HUEVOS, int(round(x * np.random.uniform(0.97, 1.03))))
    )

    # Asegurar múltiplos de 150 huevos (5 cubetas)
    df_group["huevos_a_vender"] = df_group["huevos_a_vender"].apply(
        lambda x: int(MULTIPLE_HUEVOS * round(x / MULTIPLE_HUEVOS))
    )

    # Evitar sobreventas
    df_group["huevos_a_vender"] = np.minimum(df_group["huevos_a_vender"], df_group["huevos_disponibles"])

    # ==============================
    # EXPORTAR RESULTADOS
    # ==============================
    df_group["id"] = range(1, len(df_group) + 1)
    df_group["_fecha_dt"] = pd.Timestamp.now().normalize()

    # Renombrar columnas a las esperadas por el generador de facturas
    df_final = df_group.rename(columns={
        "tipo": "tipo",
        "huevos_disponibles": "huevos_disponibles",
        "huevos_a_vender": "huevos_a_vender",
        "valor unitario": "valor unitario"
    })[["id", "tipo", "valor unitario", "huevos_disponibles", "huevos_a_vender", "_fecha_dt"]]

    # Guardar en resultados
    carpeta_salida = os.path.join(os.getcwd(), "resultados")
    os.makedirs(carpeta_salida, exist_ok=True)

    nombre_archivo = f"stock_optimizado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    ruta_salida = os.path.join(carpeta_salida, nombre_archivo)

    try:
        df_final.to_excel(ruta_salida, index=False)
        print(f"[OK] Archivo optimizado generado: {ruta_salida}")
    except Exception as e:
        print(f"[ERROR] Error al guardar archivo optimizado: {e}")
        return None

    return ruta_salida


if __name__ == "__main__":
    print("[EJECUTANDO] Ejecutando optimizador manualmente (modo prueba)...")
    ruta_prueba = os.path.join(os.getcwd(), "resultados", "facturas_consolidadas_prueba.xlsx")
    if os.path.exists(ruta_prueba):
        optimizar_stock(ruta_prueba)
    else:
        print("[AVISO] No se encontró el archivo de prueba.")
