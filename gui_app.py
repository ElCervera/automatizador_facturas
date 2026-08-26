# gui_app.py — Interfaz Streamlit Reestructurada y Funcional
import os
import time
import shutil
import pandas as pd
import streamlit as st
import traceback
from datetime import datetime
import calendar
import threading
import queue
import logging

class QueueLogHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)


# ==============================================================================
# CONFIGURACIÓN Y DEPENDENCIAS
# ==============================================================================
st.set_page_config(
    page_title="Automatizador de Facturas", 
    page_icon="🧾", 
    layout="wide"
)

# Intentar importar dependencias de visualización
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    import altair as alt
    HAS_PLOTLY = False

# Importar lógica del backend
try:
    import sys
    import importlib
    import importlib.util

    # ── PASO 1: Limpiar sys.path ──
    # Versiones anteriores del worker insertaban siigo_automation/ en sys.path.
    # Esa entrada persiste en memoria mientras el proceso de Streamlit siga vivo
    # y provoca que `from main import ...` resuelva al main.py equivocado.
    _siigo_dir = os.path.join(os.getcwd(), "siigo_automation")
    sys.path[:] = [p for p in sys.path if os.path.normcase(os.path.abspath(p)) != os.path.normcase(os.path.abspath(_siigo_dir))]

    # ── PASO 2: Purgar módulos contaminados de sys.modules ──
    # Si en una ejecución previa 'main' o 'utils' quedaron apuntando a
    # siigo_automation, los eliminamos para forzar una reimportación limpia.
    for _mod_name in list(sys.modules.keys()):
        _mod = sys.modules[_mod_name]
        _mod_file = str(getattr(_mod, "__file__", "") or "")
        if _mod_name in ("main", "utils") or _mod_name.startswith("utils."):
            if "siigo_automation" in _mod_file:
                del sys.modules[_mod_name]

    # ── PASO 3: Importar main.py de la raíz con garantía absoluta ──
    _root_main_path = os.path.join(os.getcwd(), "main.py")
    _spec = importlib.util.spec_from_file_location("main", _root_main_path)
    _root_main = importlib.util.module_from_spec(_spec)
    sys.modules["main"] = _root_main
    _spec.loader.exec_module(_root_main)

    procesar_archivos_zip = _root_main.procesar_archivos_zip
    procesar_archivos_xml = _root_main.procesar_archivos_xml
    generar_excel = _root_main.generar_excel

    from utils.optimizador_stock import optimizar_stock
    from utils.generador_facturas import generar_facturas_desde_optimo
    from utils.database import (
        insertar_ventas_from_dataframe,
        query_ventas,
        guess_month_year_from_filename,
        inicializar_db
    )
    from utils.config import CARPETA_RESULTADOS

except ImportError as e:
    st.error(f"❌ Error crítico importando módulos: {e}")
    st.stop()


# Definición de carpetas
BASE_DIR = os.getcwd()
CARPETA_ZIP = os.path.join(BASE_DIR, "facturas_zip")
CARPETA_XML = os.path.join(BASE_DIR, "facturas_xml")
CARPETA_PDF = os.path.join(BASE_DIR, "facturas_pdf")

# Definición global de nombres de meses
month_names = {
    1: "Enero", 
    2: "Febrero", 
    3: "Marzo", 
    4: "Abril", 
    5: "Mayo", 
    6: "Junio",
    7: "Julio", 
    8: "Agosto", 
    9: "Septiembre", 
    10: "Octubre", 
    11: "Noviembre", 
    12: "Diciembre"
}

# Asegurar existencia de carpetas
for carpeta in [CARPETA_ZIP, CARPETA_XML, CARPETA_PDF, CARPETA_RESULTADOS]:
    os.makedirs(carpeta, exist_ok=True)

def get_monthly_sales_from_db(year, month_num):
    """
    # Obtiene el total de ventas de la DB para un mes y año específicos.
    """
    try:
        # Convertir número de mes a nombre para la consulta
        month_name = month_names[month_num]
        
        df_ventas = query_ventas(
            "SELECT SUM(valor_total) FROM ventas_reales "
            "WHERE anio = ? AND mes = ?",
            (year, month_name)
        )
        total_ventas = 0.0
        if not df_ventas.empty and df_ventas.iloc[0, 0] is not None:
            total_ventas = df_ventas.iloc[0, 0]
        return total_ventas
    except Exception as e:
        st.error(f"Error al obtener ventas mensuales de la DB: {e}")
        return 0.0

def get_product_metrics_from_db(year, month_num):
    """
    # Obtiene métricas por producto (cantidad, valor total, precio promedio) de la DB
    para un mes y año específicos.
    """
    try:
        month_name = month_names[month_num]
        
        sql_query = """
            SELECT 
                tipo,
                SUM(cantidad_huevos) AS total_cantidad,
                SUM(valor_total) AS total_valor,
                AVG(precio_unitario) AS precio_unitario_promedio
            FROM 
                ventas_reales 
            WHERE 
                anio = ? AND mes = ?
            GROUP BY 
                tipo
            ORDER BY
                total_cantidad DESC
        """
        df_productos = query_ventas(sql_query, (year, month_name))
        return df_productos
    except Exception as e:
        st.error(f"Error al obtener métricas de producto de la DB: {e}")
        return pd.DataFrame()

# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def guardar_archivo_subido(uploaded_file, carpeta_destino):
    try:
        ruta_destino = os.path.join(carpeta_destino, uploaded_file.name)
        with open(ruta_destino, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True, ruta_destino
    except Exception as e:
        return False, str(e)

def eliminar_archivo(ruta_archivo):
    try:
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
            return True, "Archivo eliminado"
        return False, "El archivo no existe"
    except Exception as e:
        return False, str(e)

def get_files_info(carpeta, extensiones=None, year=None, month=None):
    files = []
    if not os.path.exists(carpeta):
        return []
    
    for f in os.listdir(carpeta):
        if f.startswith("~$"): # Ignorar archivos temporales de Excel abiertos
            continue
            
        if extensiones and not f.lower().endswith(tuple(extensiones)):
            continue
        
        ruta_completa = os.path.join(carpeta, f)
        if os.path.isfile(ruta_completa):
            stats = os.stat(ruta_completa)
            mtime = datetime.fromtimestamp(stats.st_mtime) # Extraer año y mes

            # Aplicar filtros de año y mes
            if year and mtime.year != year:
                continue
            if month and mtime.month != month:
                continue

            files.append({
                "Nombre": f,
                "Ruta": ruta_completa,
                "Fecha": mtime.strftime("%Y-%m-%d %H:%M:%S"), # Formato legible
                "Año": mtime.year,
                "Mes": mtime.month,
                "Tamaño (KB)": round(stats.st_size / 1024, 2),
                "Timestamp": stats.st_mtime
            })
    return sorted(files, key=lambda x: x["Timestamp"], reverse=True)

def get_excel_column_sum(file_path, column_name):
    if not os.path.exists(file_path):
        return 0.0
    try:
        df = pd.read_excel(file_path)
        if column_name in df.columns:
            # Asegurarse de que la columna sea numérica antes de sumar
            return df[column_name].sum()
        else:
            st.warning(
                f"Columna '{column_name}' no encontrada en "
                f"{os.path.basename(file_path)}"
            )
            return 0.0
    except Exception as e:
        st.error(f"Error leyendo {os.path.basename(file_path)}: {e}")
        return 0.0

def calculate_optimized_stock_value(file_path):
    if not os.path.exists(file_path):
        return 0.0
    try:
        df = pd.read_excel(file_path)
        if "valor unitario" in df.columns and "huevos_a_vender" in df.columns:
            # Asegurarse de que las columnas sean numéricas
            df["valor unitario"] = pd.to_numeric(
                df["valor unitario"], errors='coerce'
            ).fillna(0)
            df["huevos_a_vender"] = pd.to_numeric(
                df["huevos_a_vender"], errors='coerce'
            ).fillna(0)
            return (df["valor unitario"] * df["huevos_a_vender"]).sum()
        else:
            st.warning(
                "Columnas 'valor unitario' o 'huevos_a_vender' "
                f"no encontradas en {os.path.basename(file_path)}"
            )
            return 0.0
    except Exception as e:
        st.error(
            f"Error calculando valor de stock optimizado en "
            f"{os.path.basename(file_path)}: {e}"
        )
        return 0.0

# ==============================================================================
# NAVEGACIÓN LATERAL
# ==============================================================================
st.sidebar.title("Navegación")
opcion_principal = st.sidebar.radio(
    "Ir a:",
    [
        "🏠 Inicio / Dashboard", 
        "⚙️ Pasos Individuales",
        "🚀 Proceso Completo (ZIP)",
        "💾 Gestión de Resultados",
        "📈 4. Ventas Reales (BD)",
        "🔍 5. Análisis por Producto",
        "🤖 Facturación Siigo POS"
    ]
)

if opcion_principal == "⚙️ Pasos Individuales":
    opcion = st.sidebar.selectbox(
        "Selecciona un paso:",
        [
            "1. Procesamiento (ZIP/XML)", 
            "2. Optimización y Facturación"
        ]
    )
else:
    opcion = opcion_principal

st.sidebar.markdown("---")
st.sidebar.info("v3.0 - Reestructurada")

# ==============================================================================
# PÁGINA: INICIO / DASHBOARD
# ==============================================================================
if opcion == "🏠 Inicio / Dashboard":
    st.title("📊 Panel de Control")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Métricas en tiempo real
    num_zips = len([f for f in os.listdir(CARPETA_ZIP) if f.endswith('.zip')])
    num_xmls = sum(
        [len(files) for r, d, files in os.walk(CARPETA_XML) 
         if any(f.endswith('.xml') for f in files)]
    )
    num_resultados = len(
        [f for f in os.listdir(CARPETA_RESULTADOS) 
         if os.path.isfile(os.path.join(CARPETA_RESULTADOS, f))]
    )
    
    col1.metric(
        "ZIPs Pendientes", 
        num_zips, 
        help="Archivos en la carpeta facturas_zip"
    )
    col2.metric("Total XMLs", num_xmls, help="Total de facturas XML extraídas")
    col3.metric("Reportes Generados", num_resultados)
    
    # Estado de la DB
    try:
        df_ventas = query_ventas(
            "SELECT COUNT(*) as total, "
            "SUM(valor_total) as dinero FROM ventas_reales"
        )
        total_ventas = df_ventas.iloc[0]['total']
        total_dinero = (
            df_ventas.iloc[0]['dinero']
            if df_ventas.iloc[0]['dinero']
            else 0
        )
        col4.metric(
            "Ventas Históricas", 
            f"${total_dinero:,.0f}", 
            f"{total_ventas} registros"
        )
    except:
        col4.metric("Base de Datos", "Sin conexión")

    st.markdown("---")
    st.subheader("💡 Estado del Sistema")
    if num_zips > 0:
        st.warning(
            f"Tienes **{num_zips} archivos ZIP** esperando ser procesados. "
            f"Ve a la pestaña 'Procesamiento'."
        )
    elif num_xmls == 0:
        st.info("El sistema está limpio. Sube archivos ZIP para comenzar.")
    else:
        st.success("Sistema listo. Genera reportes o carga más archivos.")

    st.markdown("---")
    st.subheader("🗓️ Filtros de Fecha")
    
    # Obtener todos los archivos para los filtros de fecha
    all_files_info = get_files_info(CARPETA_RESULTADOS, [".xlsx"])
    
    available_years = sorted(
        list(set([f["Año"] for f in all_files_info])), 
        reverse=True
    )
    if not available_years:
        available_years = [datetime.now().year] # Año actual si no hay archivos
    
    selected_year = st.selectbox(
        "Selecciona el Año:",
        available_years,
        index=(
            available_years.index(datetime.now().year)
            if datetime.now().year in available_years
            else 0
        )
    )

    available_months = sorted(
        list(set([f["Mes"] for f in all_files_info 
                   if f["Año"] == selected_year]))
    )
    available_month_names = [month_names[m] for m in available_months]
    
    selected_month_name = st.selectbox(
        "Selecciona el Mes:", ["Todos los meses"] + available_month_names
    )
    
    selected_month = None
    if selected_month_name != "Todos los meses":
        selected_month = {v: k for k, v in month_names.items()}[
            selected_month_name
        ]

    st.markdown("---")
    st.subheader("💰 Métricas Financieras Clave")
    col_opt_val, col_fac_val = st.columns(2)

    # Obtener el archivo de stock optimizado más reciente
    archivos_resultados_filtrados = get_files_info(
        CARPETA_RESULTADOS, [".xlsx"], selected_year, selected_month
    )
    
    ruta_ultimo_optimo = None
    for f in archivos_resultados_filtrados:
        if "stock_optimizado" in f["Nombre"].lower():
            ruta_ultimo_optimo = f["Ruta"]
            break # El primero es el más reciente

    # Obtener el archivo de facturas simuladas más reciente
    ruta_ultimas_facturas = None
    for f in archivos_resultados_filtrados:
        if "facturas_generadas" in f["Nombre"].lower():  # Busca 'facturas_generadas'
            ruta_ultimas_facturas = f["Ruta"]
            break # El primero es el más reciente

    # Aquí se calcularán y mostrarán los valores (próximos pasos)
    valor_stock_optimizado = 0.0
    if ruta_ultimo_optimo:
        valor_stock_optimizado = calculate_optimized_stock_value(
            ruta_ultimo_optimo
        )
    
    valor_a_facturar = 0.0
    if ruta_ultimas_facturas:
        valor_a_facturar = get_excel_column_sum(
            ruta_ultimas_facturas, "Valor Total (COP)"
        )

    col_opt_val.metric(
        "Valor Stock Optimizado", 
        f"${valor_stock_optimizado:,.0f}"
    )
    col_fac_val.metric("Valor a Facturar", f"${valor_a_facturar:,.0f}")

    # Nueva métrica: Utilidad Estimada
    utilidad_estimada = valor_a_facturar - valor_stock_optimizado
    st.metric(
        "Utilidad Estimada", 
        f"${utilidad_estimada:,.0f}", 
        help="Valor a Facturar - Valor Stock Optimizado"
    )

    st.markdown("---")
    st.subheader("📈 Análisis Mensual de Utilidad Estimada")

    monthly_data = []
    for month_num in range(1, 13):
        # Obtener el archivo de stock optimizado más reciente para el mes
        monthly_stock_files = get_files_info(
            CARPETA_RESULTADOS, [".xlsx"], selected_year, month_num
        )
        monthly_ruta_optimo = None
        for f in monthly_stock_files:
            if "stock_optimizado" in f["Nombre"].lower():
                monthly_ruta_optimo = f["Ruta"]
                break

        # Obtener el archivo de facturas simuladas más reciente para el mes
        monthly_factura_files = get_files_info(
            CARPETA_RESULTADOS, [".xlsx"], selected_year, month_num
        )
        monthly_ruta_facturas = None
        for f in monthly_factura_files:
            if "facturas_generadas" in f["Nombre"].lower():
                monthly_ruta_facturas = f["Ruta"]
                break
        
        monthly_valor_stock_optimizado = 0.0
        if monthly_ruta_optimo:
            monthly_valor_stock_optimizado = calculate_optimized_stock_value(
                monthly_ruta_optimo
            )
        
        monthly_valor_a_facturar = 0.0
        if monthly_ruta_facturas:
            monthly_valor_a_facturar = get_excel_column_sum(
                monthly_ruta_facturas, "Valor Total (COP)"
            )
        
        monthly_utilidad_estimada = (
            monthly_valor_a_facturar - monthly_valor_stock_optimizado
        )
        
        monthly_data.append({
            "Mes": month_names[month_num],
            "Utilidad Estimada": monthly_utilidad_estimada
        })
    
    df_monthly = pd.DataFrame(monthly_data)

    if HAS_PLOTLY:
        fig = px.bar(
            df_monthly, 
            x="Mes", 
            y="Utilidad Estimada", 
            title=f"Utilidad Estimada Mensual para {selected_year}",
            labels={"Utilidad Estimada": "Utilidad Estimada (COP)"},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig, width='stretch')
    else:
        chart = alt.Chart(df_monthly).mark_bar().encode(
            x=alt.X("Mes", sort=list(month_names.values())),
            y="Utilidad Estimada",
            tooltip=["Mes", "Utilidad Estimada"]
        ).properties(
            title=f"Utilidad Estimada Mensual para {selected_year}"
        )
        st.altair_chart(chart, width='stretch')

    st.markdown("---")
    st.subheader("📈 Análisis Mensual de Valor Stock Optimizado")

    monthly_stock_value_data = []
    for month_num in range(1, 13):
        monthly_stock_files = get_files_info(
            CARPETA_RESULTADOS, [".xlsx"], selected_year, month_num
        )
        monthly_ruta_optimo = None
        for f in monthly_stock_files:
            if "stock_optimizado" in f["Nombre"].lower():
                monthly_ruta_optimo = f["Ruta"]
                break
        
        monthly_valor_stock_optimizado = 0.0
        if monthly_ruta_optimo:
            monthly_valor_stock_optimizado = calculate_optimized_stock_value(
                monthly_ruta_optimo
            )
        
        monthly_stock_value_data.append({
            "Mes": month_names[month_num],
            "Valor Stock Optimizado": monthly_valor_stock_optimizado
        })
    
    df_monthly_stock = pd.DataFrame(monthly_stock_value_data)

    if HAS_PLOTLY:
        fig_stock = px.bar(
            df_monthly_stock, 
            x="Mes", 
            y="Valor Stock Optimizado", 
            title=f"Valor Stock Optimizado Mensual para {selected_year}",
            labels={"Valor Stock Optimizado": "Valor (COP)"},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_stock, width='stretch')
    else:
        chart_stock = alt.Chart(df_monthly_stock).mark_bar().encode(
            x=alt.X("Mes", sort=list(month_names.values())),
            y="Valor Stock Optimizado",
            tooltip=["Mes", "Valor Stock Optimizado"]
        ).properties(
            title=f"Valor Stock Optimizado Mensual para {selected_year}"
        )
        st.altair_chart(chart_stock, width='stretch')

    st.markdown("---")
    st.subheader("📈 Análisis Mensual de Valor a Facturar")

    monthly_facturar_data = []
    for month_num in range(1, 13):
        monthly_factura_files = get_files_info(
            CARPETA_RESULTADOS, [".xlsx"], selected_year, month_num
        )
        monthly_ruta_facturas = None
        for f in monthly_factura_files:
            if "facturas_generadas" in f["Nombre"].lower():
                monthly_ruta_facturas = f["Ruta"]
                break
        
        monthly_valor_a_facturar = 0.0
        if monthly_ruta_facturas:
            monthly_valor_a_facturar = get_excel_column_sum(
                monthly_ruta_facturas, "Valor Total (COP)"
            )
        
        monthly_facturar_data.append({
            "Mes": month_names[month_num],
            "Valor a Facturar": monthly_valor_a_facturar
        })
    
    df_monthly_facturar = pd.DataFrame(monthly_facturar_data)

    if HAS_PLOTLY:
        fig_facturar = px.bar(
            df_monthly_facturar, 
            x="Mes", 
            y="Valor a Facturar", 
            title=f"Valor a Facturar Mensual para {selected_year}",
            labels={"Valor a Facturar": "Valor (COP)"},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_facturar, width='stretch')
    else:
        chart_facturar = alt.Chart(df_monthly_facturar).mark_bar().encode(
            x=alt.X("Mes", sort=list(month_names.values())),
            y="Valor a Facturar",
            tooltip=["Mes", "Valor a Facturar"]
        ).properties(
            title=f"Valor a Facturar Mensual para {selected_year}"
        )
        st.altair_chart(chart_facturar, width='stretch')

    st.markdown("---")
    st.subheader("📈 Análisis Mensual de Ventas Generadas (Desde DB)")

    monthly_ventas_data = []
    for month_num in range(1, 13):
        monthly_valor_ventas = get_monthly_sales_from_db(
            selected_year, month_num
        )
        
        monthly_ventas_data.append({
            "Mes": month_names[month_num],
            "Ventas Generadas": monthly_valor_ventas
        })
    
    df_monthly_ventas = pd.DataFrame(monthly_ventas_data)

    if HAS_PLOTLY:
        fig_ventas = px.bar(
            df_monthly_ventas, 
            x="Mes", 
            y="Ventas Generadas", 
            title=(f"Ventas Generadas Mensuales para {selected_year} "
                   f"(Desde DB)"),
            labels={"Ventas Generadas": "Valor (COP)"},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_ventas, width='stretch')
    else:
        chart_ventas = alt.Chart(df_monthly_ventas).mark_bar().encode(
            x=alt.X("Mes", sort=list(month_names.values())),
            y="Ventas Generadas",
            tooltip=["Mes", "Ventas Generadas"]
        ).properties(
            title=f"Ventas Generadas Mensuales para {selected_year} (Desde DB)"
        )
        st.altair_chart(chart_ventas, width='stretch')

    # --- DIAGNÓSTICO FINANCIERO (Errores o valores en 0 inesperados) ---
    with st.expander("🔍 Detalles del Cálculo Financiero"):
        st.write("**Archivo Stock Optimizado:**")
        st.code(ruta_ultimo_optimo if ruta_ultimo_optimo else "No encontrado")
        
        st.write("**Archivo Facturas Generadas:**")
        st.code(
            ruta_ultimas_facturas if ruta_ultimas_facturas else "No encontrado"
        )
        
        if ruta_ultimas_facturas and os.path.exists(ruta_ultimas_facturas):
            try:
                df_debug = pd.read_excel(ruta_ultimas_facturas)
                st.write(
                    "**Columnas detectadas en Facturas:**",
                    df_debug.columns.tolist()
                )
                if "Valor Total (COP)" not in df_debug.columns:
                    st.error(
                        "⚠️ Columna 'Valor Total (COP)' no encontrada. "
                        "Verifica el nombre exacto arriba."
                    )
            except Exception as e:
                st.error(f"Error leyendo archivo de facturas: {e}")

# ==============================================================================
# PÁGINA: PROCESAMIENTO
# ==============================================================================
elif opcion == "1. Procesamiento (ZIP/XML)":
    st.title("📂 Procesamiento de Archivos")
    st.markdown(
        "Sube tus archivos comprimidos o XMLs sueltos "
        "para convertirlos en datos."
    )

    tab_zip, tab_xml, tab_excel = st.tabs(
        ["📦 Paso 1: ZIPs", "📄 Paso 2: XMLs", "📊 Paso 3: Generar Excel Base"]
    )

    # --- TAB ZIP ---
    with tab_zip:
        st.subheader("Gestión de Archivos ZIP")
        uploaded_zips = st.file_uploader(
            "Subir archivos .zip", type="zip", accept_multiple_files=True
        )
        
        if uploaded_zips:
            if st.button(f"Guardar {len(uploaded_zips)} archivos ZIP"):
                for f in uploaded_zips:
                    ok, msg = guardar_archivo_subido(f, CARPETA_ZIP)
                    if ok: st.toast(f"✅ Guardado: {f.name}")
                    else: st.error(f"Error guardando {f.name}: {msg}")
                time.sleep(1)
                st.rerun()

        # Listado y Acción
        zips_existentes = get_files_info(CARPETA_ZIP, [".zip"])
        if zips_existentes:
            st.write(f"**{len(zips_existentes)} archivos ZIP en carpeta:**")
            st.dataframe(
                pd.DataFrame(zips_existentes)[
                    ["Nombre", "Tamaño (KB)", "Fecha"]
                ],
                width='stretch'
            )
            
            if st.button("🚀 Procesar TODOS los ZIPs", type="primary"):
                with st.spinner("Descomprimiendo y organizando..."):
                    nuevos_xmls = procesar_archivos_zip(
                        CARPETA_ZIP, CARPETA_XML, CARPETA_PDF
                    )
                    st.success(
                        f"✅ Proceso completado. "
                        f"Se extrajeron {len(nuevos_xmls)} "
                        "XMLs nuevos."
                    )
                    time.sleep(2)
                    st.rerun()
        else:
            st.info("No hay archivos ZIP pendientes.")

    # --- TAB XML ---
    with tab_xml:
        st.subheader("Gestión de XMLs (Opcional)")
        st.markdown(
            "Aquí puedes ver los XMLs extraídos "
            "o subir XMLs sueltos manualmente."
        )
        
        uploaded_xmls = st.file_uploader(
            "Subir XMLs sueltos", type="xml", accept_multiple_files=True
        )
        if uploaded_xmls:
            if st.button(f"Guardar {len(uploaded_xmls)} XMLs"):
                for f in uploaded_xmls:
                    ok, msg = guardar_archivo_subido(f, CARPETA_XML)
                st.success("Archivos guardados correctamente.")
        
        if st.button("🔍 Escanear carpeta de XMLs"):
            total_xml = sum(
                [len(files) for r, d, files in os.walk(CARPETA_XML)
                 if any(f.endswith('.xml') for f in files)]
            )
            st.info(
                f"Se encontraron **{total_xml}** archivos XML en la estructura "
                "de carpetas."
            )

    # --- TAB EXCEL ---
    with tab_excel:
        st.subheader("Generación de Reporte Consolidado")
        st.markdown(
            "Este proceso leerá **todos** los XMLs disponibles y creará un único "
            "archivo Excel."
        )
        
        if st.button("📊 Generar Excel Consolidado", type="primary"):
            with st.spinner("Leyendo XMLs y consolidando datos..."):
                rutas_xml = []
                for root, _, files in os.walk(CARPETA_XML):
                    for f in files:
                        if f.lower().endswith(".xml"):
                            rutas_xml.append(os.path.join(root, f))
                
                if not rutas_xml:
                    st.error("❌ No hay XMLs para procesar.")
                else:
                    resultados = procesar_archivos_xml(rutas_xml)
                    if resultados:
                        ruta_excel = generar_excel(resultados)
                        st.success(
                            f"✅ Excel generado exitosamente: "
                            f"**{os.path.basename(ruta_excel)}**"
                        )
                        st.session_state['last_excel'] = ruta_excel
                        
                        # Botón de descarga inmediata
                        with open(ruta_excel, "rb") as f:
                            st.download_button(
                                label="⬇️ Descargar Excel Consolidado",
                                data=f,
                                file_name=os.path.basename(ruta_excel),
                                mime="application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet"
                            )
                        st.rerun() # Forzar recarga para que el nuevo archivo aparezca en el selector
                    else:
                        st.warning("⚠️ No se pudo extraer información válida de los XMLs.")

# ==============================================================================
# PÁGINA: OPTIMIZACIÓN
# ==============================================================================
elif opcion == "2. Optimización y Facturación":
    st.title("🧠 Optimización de Stock y Facturación")
    
    st.info("Paso 1: Selecciona el archivo Excel base (generado en el paso anterior).")
    
    # --- SECCIÓN DE DEBUGGING ---
    with st.expander("🕵️ Diagnóstico de Archivos (Clic para ver detalles)"):
        st.write(f"**Directorio de trabajo (CWD):** `{os.getcwd()}`")
        st.write(f"**Carpeta de Resultados:** `{CARPETA_RESULTADOS}`")
        
        if os.path.exists(CARPETA_RESULTADOS):
            archivos_crudos = os.listdir(CARPETA_RESULTADOS)
            st.write(f"**Archivos en carpeta (sin filtrar):** {archivos_crudos}")
        else:
            st.error("¡La carpeta de resultados NO existe!")
    # ---------------------------

    # Selector de archivo - Lógica robusta
    archivos_info = get_files_info(CARPETA_RESULTADOS) # Obtener todos sin filtrar extensión primero
    
    # Filtrar manualmente para ver qué pasa
    opciones_validas = []
    for f in archivos_info:
        # Filtro laxo: que sea xlsx y tenga 'consolidado' o 'facturas' en el nombre
        if f["Nombre"].lower().endswith(".xlsx") and ("consolidado" in f["Nombre"].lower() or "facturas" in f["Nombre"].lower()):
            opciones_validas.append(f["Nombre"])
            
    if not opciones_validas:
        st.warning(f"No se encontraron archivos que coincidan con el criterio (xlsx + 'consolidado'/'facturas'). Archivos disponibles: {[f['Nombre'] for f in archivos_info]}")

    archivo_seleccionado = st.selectbox("Seleccionar archivo Excel Base:", options=opciones_validas, key="excel_base_selector")
    
    col_opt, col_fac = st.columns(2)
    
    ruta_optimo = None
    
    with col_opt:
        st.subheader("1. Optimizar Stock")
        if archivo_seleccionado:
            ruta_base = os.path.join(CARPETA_RESULTADOS, archivo_seleccionado)
            st.info(f"Ruta base para optimización: {ruta_base}") # DEBUG
            if st.button("⚙️ Ejecutar Optimización"):
                with st.spinner("Optimizando..."):
                    ruta_optimo = optimizar_stock(ruta_base)
                    if ruta_optimo:
                        st.success("✅ Stock optimizado generado.")
                        st.session_state['last_optimo'] = ruta_optimo
                    else:
                        st.error("Falló la optimización.")
        else:
            st.warning(
                "No hay archivos consolidados disponibles."
            )

    with col_fac:
        st.subheader("2. Generar Facturas")
        # Intentar recuperar el último óptimo de la sesión o buscar en carpeta
        archivos_optimos = [f["Nombre"] for f in get_files_info(CARPETA_RESULTADOS, [".xlsx"]) if "stock_optimizado" in f["Nombre"]]
        optimo_seleccionado = st.selectbox("Seleccionar archivo Stock Optimizado:", options=archivos_optimos, key="stock_optimo_selector")
        
        if optimo_seleccionado:
            # Calcular días hábiles del mes actual
            today = datetime.now()
            cal = calendar.Calendar()
            dias_habiles_mes_actual = len([
                day for day in cal.itermonthdates(today.year, today.month)
                if day.weekday() < 5 and day.month == today.month
            ])

            num_dias_distribucion = st.number_input(
                "Número de días para distribuir las facturas:",
                min_value=1,
                value=dias_habiles_mes_actual,
                step=1,
                key="num_dias_distribucion"
            )
            
            numero_inicio = st.number_input(
                "Número de factura inicial:",
                min_value=1,
                value=7000,
                step=1,
                key="numero_inicio_individual"
            )

            if st.button("🧾 Generar Facturas Simuladas", type="primary"):
                ruta_input = os.path.join(CARPETA_RESULTADOS, optimo_seleccionado)
                with st.spinner("Distribuyendo ventas..."):
                    try:
                        ruta_facturas = generar_facturas_desde_optimo(
                            ruta_input, num_dias_distribucion, numero_inicio=numero_inicio
                        )
                        st.success(f"✅ ¡Facturas generadas: {os.path.basename(ruta_facturas)}!")
                        
                        with open(ruta_facturas, "rb") as f:
                            st.download_button(
                                label="⬇️ Descargar Facturas Simuladas",
                                data=f,
                                file_name=os.path.basename(ruta_facturas),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    except Exception as e:
                        st.error(f"Error: {e}")

# ==============================================================================
# PÁGINA: GESTIÓN DE RESULTADOS
# ==============================================================================
elif opcion == "🚀 Proceso Completo (ZIP)":
    st.title("🚀 Proceso Completo (ZIP)")
    st.markdown(
        "Sube tus archivos ZIP para ejecutar el flujo completo: "
        "procesamiento, optimización y generación de facturas simuladas."
    )

    # Inicializar el estado de sesión para los mensajes
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    def log_message(type, message):
        st.session_state.messages.append({'type': type, 'message': message})

    # Mostrar mensajes persistentes
    for msg in st.session_state.messages:
        if msg['type'] == 'success':
            st.success(msg['message'])
        elif msg['type'] == 'info':
            st.info(msg['message'])
        elif msg['type'] == 'error':
            st.error(msg['message'])
        elif msg['type'] == 'warning':
            st.warning(msg['message'])

    if st.session_state.messages:
        if st.button("Limpiar Mensajes"):
            st.session_state.messages = []
            st.rerun() # Rerun para limpiar los mensajes mostrados


    uploaded_files = st.file_uploader(
        "Sube uno o varios archivos ZIP", 
        type=["zip"], 
        accept_multiple_files=True
    )

    if uploaded_files:
        numero_inicio_full = st.number_input(
            "Número de factura inicial para el proceso:",
            min_value=1,
            value=7000,
            step=1,
            key="numero_inicio_full"
        )
        
        if st.button("Iniciar Proceso Completo"):
            with st.spinner("Procesando archivos ZIP... Esto puede tardar un poco."):
                # 1. Guardar todos los ZIPs
                total_guardados = 0
                for uploaded_file in uploaded_files:
                    ok, msg = guardar_archivo_subido(uploaded_file, CARPETA_ZIP)
                    if ok:
                        log_message('success', f"ZIP '{uploaded_file.name}' guardado en {CARPETA_ZIP}")
                        total_guardados += 1
                    else:
                        log_message('error', f"Error al guardar ZIP '{uploaded_file.name}': {msg}")
                log_message('info', f"Se guardaron {total_guardados} ZIP(s). Iniciando extracción...")

                # 2. Extraer y organizar todos los ZIPs de la carpeta
                nuevos_xmls = []
                try:
                    nuevos_xmls = procesar_archivos_zip(
                        CARPETA_ZIP, CARPETA_XML, CARPETA_PDF
                    )
                    log_message('success',
                        f"XMLs y PDFs extraídos y organizados. Nuevos XMLs: {len(nuevos_xmls)}"
                    )
                except Exception as e:
                    log_message('error', f"Error al procesar ZIPs: {e}")

                # 3. Consolidar todos los XMLs encontrados en un solo Excel
                log_message('info', "Generando Excel consolidado a partir de los XMLs...")
                try:
                    rutas_xml = list(nuevos_xmls)
                    if not rutas_xml:
                        for root, _, files in os.walk(CARPETA_XML):
                            for f in files:
                                if f.lower().endswith(".xml"):
                                    rutas_xml.append(os.path.join(root, f))
                    if rutas_xml:
                        resultados = procesar_archivos_xml(rutas_xml)
                        if resultados:
                            ruta_excel_consolidado = generar_excel(resultados)
                            log_message('success',
                                f"Excel consolidado generado: "
                                f"{os.path.basename(ruta_excel_consolidado)}"
                            )
                            # 4. Optimización de stock sobre el Excel consolidado
                            log_message('info', "Optimizando stock...")
                            try:
                                ruta_optimo = optimizar_stock(ruta_excel_consolidado)
                                if ruta_optimo:
                                    log_message('success', f"Stock optimizado y guardado: {os.path.basename(ruta_optimo)}")
                                    # 5. Generación de facturas simuladas
                                    log_message('info', "Generando facturas simuladas...")
                                    try:
                                        today = datetime.now()
                                        cal = calendar.Calendar()
                                        dias_habiles_mes_actual = len([
                                            day for day in cal.itermonthdates(today.year, today.month)
                                            if day.weekday() < 5 and day.month == today.month
                                        ])
                                        ruta_facturas = generar_facturas_desde_optimo(
                                            ruta_optimo, dias_habiles_mes_actual, numero_inicio=numero_inicio_full
                                        )
                                        log_message('success', f"Facturas simuladas generadas y guardadas: {os.path.basename(ruta_facturas)}")
                                    except Exception as e:
                                        log_message('error', f"Error al generar facturas simuladas: {e}")
                                else:
                                    log_message('error', "Error en optimización de stock.")
                            except Exception as e:
                                log_message('error', f"Error al optimizar stock: {e}")
                        else:
                            log_message('warning', "No se obtuvieron datos válidos del procesamiento de XMLs.")
                    else:
                        log_message('warning', "No se encontraron XMLs para procesar.")
                except Exception as e:
                    log_message('error', f"Error al procesar XMLs o generar Excel: {e}")
            log_message('success', "¡Proceso completo finalizado!")
            st.balloons()
            st.rerun() # Recargar la página para actualizar el dashboard

elif opcion == "💾 Gestión de Resultados":
    st.title("💾 Archivos y Resultados")
    st.markdown("Gestiona, descarga o elimina los reportes generados.")
    
    archivos = get_files_info(CARPETA_RESULTADOS)
    
    if not archivos:
        st.info("La carpeta de resultados está vacía.")
    else:
        # Convertir a DataFrame para visualización limpia
        df_display = pd.DataFrame(archivos)
        st.dataframe(df_display[["Nombre", "Fecha", "Tamaño (KB)"]], width='stretch')
        
        st.subheader("Acciones sobre archivos")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            file_to_act = st.selectbox("Selecciona un archivo:", [f["Nombre"] for f in archivos])
        
        with col2:
            st.write("") # Espaciador
            st.write("") 
            
            ruta_completa = os.path.join(CARPETA_RESULTADOS, file_to_act) if file_to_act else None
            
            if file_to_act:
                # Botón de Descarga
                with open(ruta_completa, "rb") as f:
                    st.download_button(
                        label="⬇️ Descargar",
                        data=f,
                        file_name=file_to_act,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                # Botón de Eliminar
                if st.button("🗑️ Eliminar Archivo", type="secondary"):
                    ok, msg = eliminar_archivo(ruta_completa)
                    if ok:
                        st.success(f"Archivo eliminado: {file_to_act}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Error eliminando: {msg}")

# ==============================================================================
# PÁGINA: VENTAS REALES
# ==============================================================================
elif opcion == "📈 4. Ventas Reales (BD)":
    st.title("📈 Base de Datos de Ventas")
    
    tab_import, tab_analisis = st.tabs(["📤 Importar Datos", "📊 Análisis Gráfico"])
    
    with tab_import:
        uploaded_real = st.file_uploader("Subir Excel de ventas reales", type=["xlsx"])
        if uploaded_real:
            df_preview = pd.read_excel(uploaded_real)
            st.dataframe(df_preview.head(3))
            
            if st.button("📥 Importar a Base de Datos"):
                try:
                    count = insertar_ventas_from_dataframe(df_preview, uploaded_real.name)
                    st.success(f"✅ {count} registros importados.")
                except Exception as e:
                    st.error(f"Error: {e}")

    with tab_analisis:
        try:
            df_ventas = query_ventas("SELECT * FROM ventas_reales ORDER BY fecha DESC")
            if not df_ventas.empty:
                # Filtros
                col_filt1, col_filt2 = st.columns(2)
                anios = sorted(df_ventas['anio'].unique(), reverse=True)
                sel_anio = col_filt1.selectbox("Año", anios)
                
                df_filtered = df_ventas[df_ventas['anio'] == sel_anio]
                
                # Gráficos
                agrupado = df_filtered.groupby("mes")[["valor_total"]].sum().reset_index()
                
                if HAS_PLOTLY:
                    fig = px.bar(agrupado, x="mes", y="valor_total", title=f"Ventas {sel_anio}")
                    st.plotly_chart(fig, width='stretch')
                else:
                    st.bar_chart(agrupado.set_index("mes"))
            else:
                st.info("No hay datos para analizar.")
        except Exception as e:
            st.error(f"Error consultando DB: {e}")

# ==============================================================================
# PÁGINA: ANÁLISIS POR PRODUCTO
# ==============================================================================
elif opcion == "🔍 5. Análisis por Producto":
    st.title("🔍 Análisis de Ventas por Producto")
    st.markdown("Explora las métricas de ventas desglosadas por tipo de producto.")

    # Filtros de Año y Mes para el análisis por producto
    available_years_db = sorted(
        list(set(query_ventas("SELECT anio FROM ventas_reales").iloc[:,0])),
        reverse=True
    )
    if not available_years_db:
        available_years_db = [datetime.now().year] # Default to current year if no data

    col_year_prod, col_month_prod = st.columns(2)
    with col_year_prod:
        selected_year_prod = st.selectbox(
            "Selecciona el Año",
            available_years_db,
            index=(
                available_years_db.index(datetime.now().year)
                if datetime.now().year in available_years_db
                else 0
            ),
            key="year_filter_prod"
        )
    with col_month_prod:
        selected_month_prod = st.selectbox(
            "Selecciona el Mes",
            ["Todos los meses"] + list(month_names.values()),
            key="month_filter_prod"
        )
    
    month_num_prod = None
    if selected_month_prod != "Todos los meses":
        month_num_prod = list(month_names.keys())[list(month_names.values()).index(selected_month_prod)]

    # Obtener métricas de producto
    df_product_metrics = pd.DataFrame()
    if month_num_prod:
        df_product_metrics = get_product_metrics_from_db(selected_year_prod, month_num_prod)
    else: # Si se seleccionan "Todos los meses", sumar los datos de todos los meses
        all_months_data = []
        for m_num in range(1, 13):
            monthly_df = get_product_metrics_from_db(selected_year_prod, m_num)
            if not monthly_df.empty:
                all_months_data.append(monthly_df)
        
        if all_months_data:
            df_product_metrics = pd.concat(all_months_data).groupby('tipo').agg(
                total_cantidad=('total_cantidad', 'sum'),
                total_valor=('total_valor', 'sum'),
                precio_unitario_promedio=('precio_unitario_promedio', 'mean')
            ).reset_index()
            df_product_metrics = df_product_metrics.sort_values(by='total_cantidad', ascending=False)

    if not df_product_metrics.empty:
        st.markdown("---")
        st.subheader("📊 Resumen de Métricas por Producto")
        st.dataframe(df_product_metrics.style.format({
            "total_cantidad": "{:,.0f}",
            "total_valor": "COP {:,.2f}",
            "precio_unitario_promedio": "COP {:,.2f}"
        }), width='stretch')

        st.markdown("---")
        st.subheader("📈 Cantidad de Huevos Vendidos por Tipo de Producto")
        if HAS_PLOTLY:
            fig_cantidad = px.bar(df_product_metrics, x="tipo", y="total_cantidad",
                                  title=f"Cantidad de Huevos Vendidos por Tipo ({selected_month_prod} {selected_year_prod})",
                                  labels={"tipo": "Tipo de Producto", "total_cantidad": "Cantidad Vendida"},
                                  color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_cantidad, width='stretch')
        else:
            chart_cantidad = alt.Chart(df_product_metrics).mark_bar().encode(
                x=alt.X("tipo", sort="-y"),
                y="total_cantidad",
                tooltip=["tipo", "total_cantidad"]
            ).properties(
                title=f"Cantidad de Huevos Vendidos por Tipo ({selected_month_prod} {selected_year_prod})"
            )
            st.altair_chart(chart_cantidad, width='stretch')

        st.markdown("---")
        st.subheader("💰 Valor Total de Ventas por Tipo de Producto")
        if HAS_PLOTLY:
            fig_valor = px.bar(df_product_metrics, x="tipo", y="total_valor",
                               title=f"Valor Total de Ventas por Tipo ({selected_month_prod} {selected_year_prod})",
                               labels={"tipo": "Tipo de Producto", "total_valor": "Valor Total (COP)"},
                               color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_valor, width='stretch')
        else:
            chart_valor = alt.Chart(df_product_metrics).mark_bar().encode(
                x=alt.X("tipo", sort="-y"),
                y="total_valor",
                tooltip=["tipo", "total_valor"]
            ).properties(
                title=f"Valor Total de Ventas por Tipo ({selected_month_prod} {selected_year_prod})"
            )
            st.altair_chart(chart_valor, width='stretch')

    else:
        st.info("No hay datos de ventas por producto para el período seleccionado.")

# ==============================================================================
# PÁGINA: 🤖 FACTURACIÓN SIIGO POS (MÓDULO #7)
# ==============================================================================
elif opcion == "🤖 Facturación Siigo POS":
    st.title("🤖 Facturación Automática en Siigo POS")
    st.markdown("Automatiza el ingreso de facturas en Siigo POS de manera robusta y multiplataforma.")

    # 1. Selección de archivo
    st.subheader("📄 1. Selección de Archivo de Facturas")
    
    CARPETA_SIIGO_DATA = os.path.join(BASE_DIR, "siigo_automation", "data")
    os.makedirs(CARPETA_SIIGO_DATA, exist_ok=True)
    
    archivos_siigo_data = get_files_info(CARPETA_SIIGO_DATA, [".xlsx"])
    archivos_resultados = get_files_info(CARPETA_RESULTADOS, [".xlsx"])
    
    opciones_dict = {}
    for f in archivos_siigo_data:
        label = f"📁 siigo_automation/data/{f['Nombre']}"
        opciones_dict[label] = f["Ruta"]
        
    for f in archivos_resultados:
        label = f"📊 resultados/{f['Nombre']}"
        opciones_dict[label] = f["Ruta"]
    
    col_sel1, col_sel2 = st.columns(2)
    
    with col_sel1:
        if opciones_dict:
            opciones_lista = list(opciones_dict.keys())
            archivo_auto_sel = st.selectbox(
                "Seleccionar archivo de facturas:",
                opciones_lista,
                index=0,
                help="Por defecto se selecciona automáticamente el archivo diario en siigo_automation/data/."
            )
            ruta_excel_auto = opciones_dict[archivo_auto_sel]
        else:
            st.info("No se encontraron archivos .xlsx en siigo_automation/data/ ni en resultados/.")
            ruta_excel_auto = None


    with col_sel2:
        uploaded_siigo_file = st.file_uploader(
            "O subir un archivo Excel manualmente:",
            type=["xlsx"],
            key="siigo_excel_uploader"
        )
        if uploaded_siigo_file:
            ok_subida, ruta_subida = guardar_archivo_subido(uploaded_siigo_file, CARPETA_RESULTADOS)
            if ok_subida:
                st.success(f"Archivo subido: {uploaded_siigo_file.name}")
                ruta_excel_final = ruta_subida
            else:
                st.error(f"Error subiendo archivo: {ruta_subida}")
                ruta_excel_final = ruta_excel_auto
        else:
            ruta_excel_final = ruta_excel_auto

    st.markdown("---")

    # 2. Opciones de ejecución
    st.subheader("⚙️ 2. Opciones de Ejecución")
    col_opt1, col_opt2 = st.columns(2)

    import sys
    so_actual = "Windows" if sys.platform.startswith("win") else "Linux Mint / Linux"

    with col_opt1:
        browser_choice = st.selectbox(
            "Navegador Web:",
            ["Auto-detectar", "Edge", "Firefox"],
            index=0,
            help=f"Sistema Operativo detectado: {so_actual}. Auto-detectar usará Edge en Windows y Firefox en Linux."
        )
        limit_invoices = st.number_input(
            "Límite de Facturas a procesar (0 = todas):",
            min_value=0,
            value=0,
            step=1,
            help="Permite procesar únicamente las primeras N facturas para realizar pruebas."
        )

    with col_opt2:
        dry_run = st.checkbox(
            "🧪 Modo Ensayo (Dry Run)",
            value=True,
            help="Simula el llenado en Siigo POS sin hacer clic en 'Cobrar' ni enviar a la DIAN."
        )
        manual_config = st.checkbox(
            "⏳ Configuración Manual",
            value=False,
            help="Abre el navegador y espera a que el usuario valide la sesión en Siigo POS."
        )

    st.markdown("---")

    # 3. Control de Ejecución e Hilos
    st.subheader("🚀 3. Estado del Proceso y Logs en Vivo")

    if "siigo_status" not in st.session_state:
        st.session_state["siigo_status"] = {"current": 0, "total": 0, "inv_num": "", "finished": False, "exit_code": None, "error": None}
    if "siigo_logs" not in st.session_state:
        st.session_state["siigo_logs"] = []
    if "siigo_running" not in st.session_state:
        st.session_state["siigo_running"] = False

    if "siigo_queue" in st.session_state and st.session_state["siigo_queue"] is not None:
        q = st.session_state["siigo_queue"]
        while not q.empty():
            try:
                msg = q.get_nowait()
                st.session_state["siigo_logs"].append(msg)
            except queue.Empty:
                break

    is_running = False
    if "siigo_thread" in st.session_state and st.session_state["siigo_thread"] is not None:
        if st.session_state["siigo_thread"].is_alive():
            is_running = True
        else:
            st.session_state["siigo_running"] = False

    def _run_siigo_worker(excel_path, browser, is_dry_run, is_manual, limit_val, status_dict, log_q, ready_event):
        try:
            from siigo_automation.main import run_robusto
            from siigo_automation.utils.logger import get_logger

            logger = get_logger("robo_facturador_2.0")
            handler = QueueLogHandler(log_q)
            handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S"))
            logger.addHandler(handler)

            def progress_cb(curr, tot, inv_num):
                status_dict["current"] = curr
                status_dict["total"] = tot
                status_dict["inv_num"] = inv_num

            code = run_robusto(
                dry_run=is_dry_run,
                limit=limit_val if limit_val > 0 else None,
                excel_path=excel_path,
                browser_type=browser.lower(),
                wait_for_manual_setup=is_manual,
                progress_callback=progress_cb,
                custom_logger=logger,
                manual_ready_event=ready_event if is_manual else None,
            )
            status_dict["exit_code"] = code
            status_dict["finished"] = True
        except Exception as exc:
            status_dict["error"] = str(exc)
            status_dict["finished"] = True

    col_btn1, col_btn2 = st.columns([2, 1])

    # Inicializar el evento de confirmación manual en session_state
    if "siigo_manual_event" not in st.session_state:
        st.session_state["siigo_manual_event"] = None

    with col_btn1:
        start_disabled = is_running or not ruta_excel_final
        if st.button("🚀 Iniciar Facturación Automática", type="primary", disabled=start_disabled):
            if not ruta_excel_final or not os.path.exists(ruta_excel_final):
                st.error("No hay un archivo de facturas válido seleccionado.")
            else:
                st.session_state["siigo_logs"] = []
                st.session_state["siigo_status"] = {"current": 0, "total": 0, "inv_num": "", "finished": False, "exit_code": None, "error": None}
                st.session_state["siigo_running"] = True

                log_q = queue.Queue()
                st.session_state["siigo_queue"] = log_q

                ready_event = threading.Event()
                st.session_state["siigo_manual_event"] = ready_event

                t = threading.Thread(
                    target=_run_siigo_worker,
                    args=(
                        ruta_excel_final,
                        browser_choice,
                        dry_run,
                        manual_config,
                        limit_invoices,
                        st.session_state["siigo_status"],
                        log_q,
                        ready_event,
                    ),
                    daemon=True
                )
                t.start()
                st.session_state["siigo_thread"] = t
                st.rerun()

    with col_btn2:
        if is_running:
            st.warning("⚠️ Ejecución en curso...")

    # Botón de confirmación manual: aparece cuando el worker espera señal de la GUI
    if is_running and manual_config and st.session_state.get("siigo_manual_event") is not None:
        event = st.session_state["siigo_manual_event"]
        if not event.is_set():
            st.markdown("---")
            st.warning("⏳ **El navegador está abierto.** Configura Siigo POS con la sesión iniciada y el turno abierto.")
            if st.button("✅ Siigo POS está listo — Continuar con la facturación", type="primary"):
                event.set()
                st.rerun()

    status = st.session_state["siigo_status"]
    curr = status.get("current", 0)
    tot = status.get("total", 0)
    inv_n = status.get("inv_num", "")

    if tot > 0:
        pct = min(1.0, curr / tot)
        st.progress(pct, text=f"Procesando factura {curr} de {tot} ({inv_n})")
    elif is_running:
        st.progress(0.0, text="Iniciando navegador y cargando archivo...")

    if is_running:
        st.info("🤖 Automatización de Siigo POS ejecutándose en segundo plano...")
    elif status.get("finished"):
        if status.get("exit_code") == 0:
            st.success("🎉 Facturación automatizada completada con éxito.")
        elif status.get("error"):
            st.error(f"❌ Error en la ejecución: {status.get('error')}")
        elif status.get("exit_code") is not None:
            st.error(f"⚠️ El proceso finalizó con código de salida: {status.get('exit_code')}")

    st.subheader("📋 Consola de Logs en Vivo")
    logs_text = "\n".join(st.session_state["siigo_logs"]) if st.session_state["siigo_logs"] else "Esperando inicio del proceso..."
    st.code(logs_text, language="text")

    if is_running:
        time.sleep(1)
        st.rerun()

