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
    # si remaining <= 0, no hay nada que fragmentar
    if remaining <= 0:
        return partes

    # transform units into multiples (redondear al múltiplo más cercano por debajo)
    def to_multiple(x):
        # Si x es menor que el múltiplo mínimo, devolvemos el múltiplo mínimo
        # pero luego validamos contra remaining
        val = (x // multiple) * multiple
        return max(multiple, val)

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
        
        # if candidate > remaining, reduce to the largest multiple <= remaining
        if candidate > remaining:
            candidate = (remaining // multiple) * multiple
            if candidate == 0:
                # Si no queda ni para un múltiplo, salimos para tratar el resto como remanente
                break
        
        partes.append(int(candidate))
        remaining -= candidate

    # Si queda un remanente pequeño (> 0), lo agregamos al final
    # (Este remanente no será múltiplo de 5 cubetas, lo cual es aceptable según la regla)
    if remaining > 0:
        partes.append(int(remaining))

    return partes

def generar_facturas_desde_optimo(ruta_stock_optimo, num_dias_distribucion, numero_inicio=7000):
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
    numero_factura = numero_inicio

    for mes, datos_mes in df.groupby('mes'):
        print(f"\nGenerando facturas para {mes}...")
        # date window: from min date's month start to month end
        fecha_inicio = datos_mes['_fecha_dt'].min()
        month_start = fecha_inicio.replace(day=1)
        next_month = (month_start + pd.Timedelta(days=32)).replace(day=1)
        month_end = next_month - pd.Timedelta(days=1)

        # business days list
        all_bdays = pd.bdate_range(start=month_start, end=month_end).to_pydatetime().tolist()
        # Select num_dias_distribucion unique business days
        bdays = random.sample(all_bdays, min(num_dias_distribucion, len(all_bdays)))
        bdays.sort() # Ensure days are in chronological order

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

        # 1. Generar todas las LINEAS de productos para este mes primero
        lineas_mes = []
        for _, row in datos_mes.iterrows():
            qty_total = int(row['huevos_a_vender'])
            if qty_total <= 0:
                continue
            tipo = row['tipo']
            precio_base = float(row['valor unitario'])
            # fragmenta en partes
            partes = fragmentar_cantidad_en_facturas(qty_total, min_unit=MIN_HUEVOS, max_unit=MAX_HUEVOS, multiple=MULTIPLE_HUEVOS)
            for p in partes:
                chosen_day = np.random.choice(bdays, p=day_probs)
                # margin per egg random 3-5 COP
                margen = random.randint(3, 5)
                precio_venta_huevo = precio_base + margen
                valor_total = p * precio_venta_huevo
                linea = {
                    'Fecha': chosen_day,
                    'Tipo': tipo,
                    'Precio base (COP/huevo)': round(precio_base, 2),
                    'Huevos vendidos': int(p),
                    'Cubetas vendidas': int(p // 30),
                    'Precio venta (COP/huevo)': round(precio_venta_huevo, 2),
                    'Precio venta (COP/cubeta)': round(precio_venta_huevo * 30, 2),
                    'Valor Total (COP)': round(valor_total, 2),
                    'ID_Stock': int(row['id'])
                }
                lineas_mes.append(linea)

        # 2. AGRUPAR LINEAS EN FACTURAS (1-3 productos, max 3M, no repetir tipo)
        facturas_mes = []
        df_lineas = pd.DataFrame(lineas_mes)
        if not df_lineas.empty:
            # Agrupar por fecha
            for fecha, group in df_lineas.groupby('Fecha'):
                items_dia = group.to_dict('records')
                random.shuffle(items_dia)
                
                while items_dia:
                    # Intentar armar una factura con 1-3 productos
                    n_objetivo = random.randint(1, 3)
                    factura_actual_items = []
                    tipos_en_factura = set()
                    valor_factura_actual = 0
                    
                    # Intentar agregar hasta n_objetivo items
                    i = 0
                    while i < len(items_dia) and len(factura_actual_items) < n_objetivo:
                        item = items_dia[i]
                        # Reglas: no repetir tipo y no pasar de 3M COP
                        if item['Tipo'] not in tipos_en_factura and (valor_factura_actual + item['Valor Total (COP)']) <= 3_000_000:
                            factura_actual_items.append(items_dia.pop(i))
                            tipos_en_factura.add(item['Tipo'])
                            valor_factura_actual += item['Valor Total (COP)']
                        else:
                            i += 1
                    
                    # Si no pudimos agregar nada más pero aún quedan items, 
                    # cerramos esta factura y pasamos a la siguiente. 
                    # Si no se pudo agregar ni uno solo (ej: el item individual > 3M), 
                    # forzamos el primero para no entrar en loop infinito.
                    if not factura_actual_items and items_dia:
                        factura_actual_items.append(items_dia.pop(0))
                        valor_factura_actual = factura_actual_items[0]['Valor Total (COP)']
                    
                    if factura_actual_items:
                        id_factura_str = f"LSFE {numero_factura}"
                        fecha_str = fecha.strftime('%d/%m/%Y')
                        for it in factura_actual_items:
                            it['N factura'] = id_factura_str
                            it['Fecha'] = fecha_str
                            facturas_mes.append(it)
                            todas_facturas.append(it)
                        
                        numero_factura += 1
                        total_global += valor_factura_actual

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
