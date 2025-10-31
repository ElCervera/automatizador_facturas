# utils/config.py
"""
Configuración global del proyecto.
Centraliza exclusiones y parámetros que usan todos los módulos.
"""

# Exclusiones
# NITs temporales a excluir (puedes eliminar/comment cuando ya no quieras excluir).
EXCLUIR_NITS = [
    "79389881",  # ejemplo Humberto Guerrero (temporal)
]

# Productos excluidos permanentemente (no vender nunca)
EXCLUIR_PRODUCTOS = [
    "HUEVO QUEBRADO",
    # Si deseas excluir "HUEVOS" también, agrega aquí.
]

# Carpetas/resultados
CARPETA_RESULTADOS = "resultados"

# Parámetros de simulación / optimización
VENTA_DIARIA_MIN = 5_000_000
VENTA_DIARIA_MAX = 20_000_000

MIN_HUEVOS = 300        # mínimo por factura (10 cubetas)
MAX_HUEVOS = 1500       # máximo por factura (50 cubetas)
MULTIPLE_HUEVOS = 150   # múltiplo requerido (5 cubetas)

# Otros parámetros
# Tolerancia (huevos) para ajuste de rounding/reconciliación
TOLERANCIA_RECONCILIACION = 150
