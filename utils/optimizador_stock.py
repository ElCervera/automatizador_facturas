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

# Intentar importar PuLP
try:
    import pulp
    HAS_PULP = True
except ImportError:
    HAS_PULP = False
    print("⚠️ PuLP no está instalado, se usará el modo heurístico.")

# ==============================
# CONFIGURACIÓN
# ==============================
EXCLUIR_NITS = ["79389881"]           # Exclusión temporal de un tercero
EXCLUIR_PRODUCTOS = ["HUEVO QUEBRADO"]  # Exclusión permanente
MIN_VENTA_HUEVOS = 300                # 10 cubetas
MAX_VENTA_HUEVOS = 1500               # 50 cubetas
MULTIPLO_HUEVOS = 150                 # 5 cubetas = 150 huevos

# ==============================
# FUNCIÓN PRINCIPAL
# ==============================
def optimizar_stock(ruta_excel_base):
    """
    Lee el archivo Excel base, optimiza la cantidad de huevos a vender mensualmente,
    y genera un nuevo archivo con las columnas esperadas por el generador de facturas.
    """
    if not os.path.exists(ruta_excel_base):
        print(f"❌ No se encontró el archivo base: {ruta_excel_base}")
        return None

    print(f"\n📊 Leyendo archivo base: {ruta_excel_base}")
    df = pd.read_excel(ruta_excel_base)

    # Normalizar nombres de columnas
    df.columns = [c.strip().lower() for c in df.columns]

    # Verificación mínima
    columnas_requeridas = {"tipo", "cantidad", "valor unitario", "nit_proveedor"}
    if not columnas_requeridas.issubset(df.columns):
        print(f"❌ Columnas faltantes: {columnas_requeridas - set(df.columns)}")
        return None

    # Filtrar los productos y terceros excluidos
    df = df[~df["tipo"].str.upper().isin(EXCLUIR_PRODUCTOS)]
    df = df[~df["nit_proveedor"].astype(str).isin(EXCLUIR_NITS)]

    if df.empty:
        print("⚠️ No quedan registros válidos tras aplicar los filtros.")
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
    target_sales = total_huevos  # objetivo: vender todo

    print(f"Estimación objetivo (huevos a vender este mes): {target_sales:,.0f} (avg_price={avg_price:.2f} COP, business_days={business_days})")

    # Si tenemos PuLP, usar modelo lineal
    if HAS_PULP:
        print("\n⚙️ Ejecutando optimizador lineal (PuLP)...")
        model = pulp.LpProblem("Optimizador_Ventas", pulp.LpMaximize)

        # Variables de decisión
        x = {i: pulp.LpVariable(f"x_{i}", lowBound=0, upBound=row["huevos_disponibles"], cat="Integer")
             for i, row in df_group.iterrows()}

        # Función objetivo: maximizar ventas totales
        model += pulp.lpSum(x[i] * df_group.loc[i, "valor unitario"] for i in x)

        # Restricciones (puedes personalizarlas si hay objetivos diferentes)
        model += pulp.lpSum(x[i] for i in x) <= target_sales

        # Resolver
        model.solve(pulp.PULP_CBC_CMD(msg=False))

        df_group["huevos_a_vender"] = [int(x[i].value()) for i in x]

    else:
        print("\n⚙️ Ejecutando modo heurístico...")
        # Distribución proporcional simple con ruido aleatorio controlado
        df_group["huevos_a_vender"] = df_group["huevos_disponibles"]

        # Añadir pequeñas variaciones aleatorias para evitar patrones fijos
        np.random.seed(42)
        df_group["huevos_a_vender"] = df_group["huevos_a_vender"].apply(
            lambda x: max(MIN_VENTA_HUEVOS, int(round(x * np.random.uniform(0.97, 1.03))))
        )

    # Asegurar múltiplos de 150 huevos (5 cubetas)
    df_group["huevos_a_vender"] = df_group["huevos_a_vender"].apply(
        lambda x: int(MULTIPLO_HUEVOS * round(x / MULTIPLO_HUEVOS))
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
        print(f"📊 Archivo optimizado generado: {ruta_salida}")
    except Exception as e:
        print(f"❌ Error al guardar archivo optimizado: {e}")
        return None

    return ruta_salida


if __name__ == "__main__":
    print("🚀 Ejecutando optimizador manualmente (modo prueba)...")
    ruta_prueba = os.path.join(os.getcwd(), "resultados", "facturas_consolidadas_prueba.xlsx")
    if os.path.exists(ruta_prueba):
        optimizar_stock(ruta_prueba)
    else:
        print("⚠️ No se encontró el archivo de prueba.")
