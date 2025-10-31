# utils/generador_facturas.py
"""
Generador de facturas: toma el archivo generado por optimizador_stock (stock_optimo_*.xlsx)
y reparte las cantidades por día (business days) siguiendo reglas:
- Min/Max por factura en huevos, múltiplos requeridos
- Dias fuertes (martes, viernes) con mayor probabilidad/volumen
- No vende fines de semana
Genera un Excel con hojas por mes y un resumen.
"""

import os
import math
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from utils.config import (
    CARPETA_RESULTADOS, MIN_HUEVOS, MAX_HUEVOS, MULTIPLE_HUEVOS,
    VENTA_DIARIA_MIN, VENTA_DIARIA_MAX, EXCLUIR_NITS, EXCLUIR_PRODUCTOS
)

def _business_days_between(start, end):
    return np.busday_count(start.date(), (end + pd.Timedelta(days=1)).date())

def fragmentar_cantidad_en_facturas(total_qty, min_unit=MIN_HUEVOS, max_unit=MAX_HUEVOS, multiple=MULTIPLE_HUEVOS):
    """
    Fragmenta total_qty (huevos) en una lista de cantidades por factura,
    cada cantidad es múltiplo, >= min_unit y <= max_unit (si es posible).
    Heurística: intenta usar valores variados, prefiriendo min_unit..max_unit.
    """
    partes = []
    remaining = int(total_qty)
    # si remaining < min_unit, devolver [remaining] (remanente) para vender en fase remanente
    if remaining <= 0:
        return partes

    # transform units into multiples
    def to_multiple(x):
        return max(multiple, (x // multiple) * multiple)

    # while remain >= min_unit, create chunks
    while remaining >= min_unit:
        # choose a chunk size biased: 30% large, 50% medium, 20% small
        r = random.random()
        if r < 0.3:
            candidate = min(remaining, max_unit)
        elif r < 0.8:
            candidate = min(remaining, int((min_unit + max_unit) / 2))
        else:
            candidate = min(remaining, min_unit)
        candidate = to_multiple(candidate)
        # safeguard
        if candidate == 0:
            break
        # if candidate > remaining, reduce to the largest multiple <= remaining
        if candidate > remaining:
            candidate = (remaining // multiple) * multiple
            if candidate == 0:
                break
        partes.append(int(candidate))
        remaining -= candidate

    # if small remainder remains (< min_unit), keep as remanente (will be sold in remanentes phase)
    if remaining > 0:
        # keep as leftover
        partes.append(int(remaining))  # will be treated as remanente if < min_unit by caller

    return partes

def generar_facturas_desde_optimo(ruta_stock_optimo):
    """
    Lee stock_optimo_xxx.xlsx y genera facturas distribuidas por días del mes.
    """
    if not os.path.exists(ruta_stock_optimo):
        raise FileNotFoundError(ruta_stock_optimo)

    df = pd.read_excel(ruta_stock_optimo)
    # asegurar nombres
    df.columns = [c.strip().lower() for c in df.columns]

    # validar columnas
    required = {'id', 'tipo', 'valor unitario', 'huevos_disponibles', 'huevos_a_vender', '_fecha_dt'}
    if not required.issubset(set(df.columns)):
        raise ValueError(f"El stock_optimo debe tener {required}")

    # convertir tipos
    df['huevos_a_vender'] = pd.to_numeric(df['huevos_a_vender'], errors='coerce').fillna(0).astype(int)
    df['huevos_disponibles'] = pd.to_numeric(df['huevos_disponibles'], errors='coerce').fillna(0).astype(int)
    df['valor unitario'] = pd.to_numeric(df['valor unitario'], errors='coerce').fillna(0.0)

    # agrupar por mes de la fecha de referencia
    df['_fecha_dt'] = pd.to_datetime(df['_fecha_dt'])
    df['mes'] = df['_fecha_dt'].dt.month_name()

    os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
    fecha_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_salida = os.path.join(CARPETA_RESULTADOS, f"facturas_generadas_{fecha_hora}.xlsx")
    writer = pd.ExcelWriter(ruta_salida, engine='xlsxwriter')

    total_global = 0
    todas_facturas = []

    for mes, datos_mes in df.groupby('mes'):
        print(f"\nGenerando facturas para {mes}...")
        # date window: from min date's month start to month end
        fecha_inicio = datos_mes['_fecha_dt'].min()
        month_start = fecha_inicio.replace(day=1)
        next_month = (month_start + pd.Timedelta(days=32)).replace(day=1)
        month_end = next_month - pd.Timedelta(days=1)

        # business days list
        bdays = pd.bdate_range(start=month_start, end=month_end).to_pydatetime().tolist()
        # prefer Tue(1) and Fri(4): give them higher weight
        day_weights = []
        for d in bdays:
            if d.weekday() in [1, 4]:
                day_weights.append(3)  # heavier
            else:
                day_weights.append(1)
        # normalized weights
        total_w = sum(day_weights)
        day_probs = [w/total_w for w in day_weights]

        facturas_mes = []
        numero_factura = 7000

        # For each row in datos_mes, fragmenta la cantidad a vender en facturas y asigna días
        for _, row in datos_mes.iterrows():
            qty_total = int(row['huevos_a_vender'])
            if qty_total <= 0:
                continue
            tipo = row['tipo']
            precio_base = float(row['valor unitario'])
            # fragmenta en facturas (múltiplos)
            partes = fragmentar_cantidad_en_facturas(qty_total, min_unit=MIN_HUEVOS, max_unit=MAX_HUEVOS, multiple=MULTIPLE_HUEVOS)
            # if last part < MIN_HUEVOS -> that's remanente; we will try to sell in remanente phase
            for p in partes:
                # if p < MIN_HUEVOS, treat as remanente later; here we still can create a small invoice if business rule allows
                # choose day weighted by day_probs
                chosen_day = np.random.choice(bdays, p=day_probs)
                # margin per egg random 3-5 COP
                margen = random.randint(3,5)
                precio_venta_huevo = precio_base + margen
                valor_total = p * precio_venta_huevo
                factura = {
                    'Fecha': chosen_day.strftime('%d/%m/%Y'),
                    'N factura': f"LSFE {numero_factura}",
                    'Tipo': tipo,
                    'Precio base (COP/huevo)': round(precio_base,2),
                    'Huevos vendidos': int(p),
                    'Cubetas vendidas': int(p // 30),
                    'Precio venta (COP/huevo)': round(precio_venta_huevo,2),
                    'Precio venta (COP/cubeta)': round(precio_venta_huevo*30,2),
                    'Valor Total (COP)': round(valor_total,2),
                    'ID_Stock': int(row['id'])
                }
                facturas_mes.append(factura)
                todas_facturas.append(factura)
                numero_factura += 1
                total_global += valor_total

        # AFTER processing all rows: write sheet
        df_out = pd.DataFrame(facturas_mes)
        if not df_out.empty:
            df_out.sort_values('Fecha', inplace=True)
            df_out.to_excel(writer, sheet_name=mes[:31], index=False)
            print(f"  {mes}: {len(df_out)} facturas, total ${int(df_out['Valor Total (COP)'].sum()):,}")

    # write global summary sheet
    if todas_facturas:
        df_all = pd.DataFrame(todas_facturas)
        df_all.to_excel(writer, sheet_name='all_facturas', index=False)

    writer.close()
    print(f"\nArchivo final generado: {ruta_salida}")
    print(f"Total facturado simulado global: ${int(total_global):,}")
    return ruta_salida
