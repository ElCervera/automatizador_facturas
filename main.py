"""
Automatizador de Facturas — Fase 3 Optimizada:
Incluye análisis de stock, optimización y generación automática de facturas simuladas.
"""

import os
import zipfile
import shutil
import datetime
import re
import xml.etree.ElementTree as ET
from utils.database import inicializar_db

# Inicializar base de datos al arrancar
inicializar_db()

from utils.lector_xml import procesar_xml, aplicar_reglas_conversion, cargar_reglas_conversion
from utils.optimizador_stock import optimizar_stock
from utils.generador_facturas import generar_facturas_desde_optimo
from utils.config import CARPETA_RESULTADOS, EXCLUIR_NITS, EXCLUIR_PRODUCTOS

# Namespaces para XML DIAN
NAMESPACES = {
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
    'sts': 'dian:gov:co:facturaelectronica:Structures-2-1'
}


# ---------------------------------------------------------------------------
# UTILIDADES DE ORGANIZACIÓN DE ZIP/XML/PDF
# ---------------------------------------------------------------------------
def crear_estructura_carpetas(ruta_base, año, mes):
    ruta_completa = os.path.join(ruta_base, str(año), mes)
    os.makedirs(ruta_completa, exist_ok=True)
    return ruta_completa


def extraer_datos_desde_xml(ruta_xml):
    try:
        tree = ET.parse(ruta_xml)
        root = tree.getroot()

        numero_factura = root.findtext('.//cbc:ID', namespaces=NAMESPACES)
        if not numero_factura:
            qr_code = root.findtext('.//sts:QRCode', namespaces=NAMESPACES)
            if qr_code:
                for linea in qr_code.split('\n'):
                    if linea.startswith('NumFac:'):
                        numero_factura = linea.replace('NumFac:', '').strip()
                        break

        fecha_emision = root.findtext('.//cbc:IssueDate', namespaces=NAMESPACES)
        if not fecha_emision and qr_code:
            for linea in qr_code.split('\n'):
                if linea.startswith('FecFac:'):
                    fecha_emision = linea.replace('FecFac:', '').strip()
                    break

        if fecha_emision:
            fecha = datetime.datetime.strptime(fecha_emision, '%Y-%m-%d')
            año = str(fecha.year)
            mes_nombre = fecha.strftime("%B").capitalize()
            if not numero_factura:
                numero_factura = f"FACT_{fecha.strftime('%Y%m%d')}"
            return año, mes_nombre, numero_factura

    except Exception as e:
        print(f"[AVISO] Error extrayendo datos del XML {ruta_xml}: {e}")

    return obtener_datos_desde_nombre(os.path.basename(ruta_xml))


def obtener_datos_desde_nombre(nombre_archivo):
    meses = {
        "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
        "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
        "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
    }

    nombre_base = os.path.splitext(nombre_archivo)[0]
    patrones = [r'FV[_-]?(\d+)', r'FE[_-]?(\d+)', r'FACT[_-]?(\d+)', r'(\d{4}[-_]?\d{2}[-_]?\d{2})']
    numero_factura = nombre_base

    for patron in patrones:
        match = re.search(patron, nombre_archivo, re.IGNORECASE)
        if match:
            numero_factura = match.group(1)
            break

    fecha_match = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', nombre_archivo)
    if fecha_match:
        año = fecha_match.group(1)
        mes_num = fecha_match.group(2)
        mes_nombre = meses.get(mes_num, "Desconocido")
        return año, mes_nombre, numero_factura

    hoy = datetime.datetime.now()
    return str(hoy.year), meses[str(hoy.month).zfill(2)], numero_factura


def procesar_archivos_zip(carpeta_zip, carpeta_xml, carpeta_pdf):
    if not os.path.exists(carpeta_zip):
        print(f"[AVISO] Carpeta no encontrada: {carpeta_zip}")
        return []

    os.makedirs(carpeta_xml, exist_ok=True)
    os.makedirs(carpeta_pdf, exist_ok=True)
    carpeta_temp = os.path.join(os.getcwd(), "temp_extraction")
    os.makedirs(carpeta_temp, exist_ok=True)

    archivos_xml_procesados = []
    archivos_existentes = set()

    for root, _, files in os.walk(carpeta_xml):
        for file in files:
            if file.lower().endswith(".xml"):
                archivos_existentes.add(file)

    for archivo_zip in os.listdir(carpeta_zip):
        if not archivo_zip.lower().endswith(".zip"):
            continue

        ruta_zip = os.path.join(carpeta_zip, archivo_zip)
        try:
            with zipfile.ZipFile(ruta_zip, "r") as zip_ref:
                contenido = zip_ref.namelist()
                archivos_validos = [f for f in contenido if f.lower().endswith((".xml", ".pdf"))]
                zip_ref.extractall(carpeta_temp)

                xml_files = [f for f in archivos_validos if f.lower().endswith(".xml")]
                if xml_files:
                    ruta_xml_temp = os.path.join(carpeta_temp, xml_files[0])
                    datos_factura = extraer_datos_desde_xml(ruta_xml_temp)
                else:
                    datos_factura = obtener_datos_desde_nombre(archivo_zip)

                año, mes, numero_factura = datos_factura

                for nombre_archivo in archivos_validos:
                    ruta_temp = os.path.join(carpeta_temp, nombre_archivo)
                    if not os.path.exists(ruta_temp):
                        continue
                    nombre_limpio = re.sub(r'[<>:"/\\|?*]', '_', nombre_archivo)

                    if nombre_archivo.lower().endswith(".xml"):
                        carpeta_destino = crear_estructura_carpetas(carpeta_xml, año, mes)
                        nuevo_nombre = f"{numero_factura}.xml"
                        ruta_destino = os.path.join(carpeta_destino, nuevo_nombre)
                        shutil.move(ruta_temp, ruta_destino)
                        archivos_xml_procesados.append(ruta_destino)
                    elif nombre_archivo.lower().endswith(".pdf"):
                        carpeta_destino = crear_estructura_carpetas(carpeta_pdf, año, mes)
                        nuevo_nombre = f"{numero_factura}.pdf"
                        ruta_destino = os.path.join(carpeta_destino, nuevo_nombre)
                        shutil.move(ruta_temp, ruta_destino)

            shutil.rmtree(carpeta_temp)
            os.makedirs(carpeta_temp, exist_ok=True)
            os.remove(ruta_zip)
            print(f"[OK] ZIP procesado: {archivo_zip}")

        except Exception as e:
            print(f"[ERROR] Error procesando {archivo_zip}: {e}")

    shutil.rmtree(carpeta_temp, ignore_errors=True)
    return archivos_xml_procesados


# ---------------------------------------------------------------------------
# PROCESAMIENTO DE XML Y GENERACIÓN DE EXCEL
# ---------------------------------------------------------------------------
def procesar_archivos_xml(rutas_xml):
    reglas = cargar_reglas_conversion()
    resultados = []
    for ruta in rutas_xml:
        nombre_archivo = os.path.basename(ruta)
        print(f"\n[BUSCANDO] Procesando XML: {nombre_archivo}")
        factura = procesar_xml(ruta)
        if factura:
            datos_convertidos = aplicar_reglas_conversion(factura, reglas)
            resultados.extend(datos_convertidos)
        else:
            print(f"[ERROR] Error al procesar {nombre_archivo}")
    return resultados


def generar_excel(resultados):
    import pandas as pd
    os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
    
    # Filtrar productos excluidos
    df = pd.DataFrame(resultados)
    if 'tipo' in df.columns:
        df = df[~df["tipo"].str.upper().isin(EXCLUIR_PRODUCTOS)]
    
    fecha_hora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_excel = os.path.join(CARPETA_RESULTADOS, f"facturas_consolidadas_{fecha_hora}.xlsx")
    df.to_excel(ruta_excel, index=False)
    print(f"[EXCEL] Excel generado: {ruta_excel}")
    return ruta_excel


# ---------------------------------------------------------------------------
# MAIN PRINCIPAL
# ---------------------------------------------------------------------------
def main():
    print("=== AUTOMATIZADOR DE FACTURAS — FASE 3 OPTIMIZADA ===")

    carpeta_zip = os.path.join(os.getcwd(), "facturas_zip")
    carpeta_xml = os.path.join(os.getcwd(), "facturas_xml")
    carpeta_pdf = os.path.join(os.getcwd(), "facturas_pdf")

    # [1] Procesar ZIPs
    archivos_procesados = procesar_archivos_zip(carpeta_zip, carpeta_xml, carpeta_pdf)

    # [2] Buscar XMLs existentes si no se procesaron nuevos
    if not archivos_procesados:
        print("[BUSCANDO] Buscando XMLs existentes...")
        for root, _, files in os.walk(carpeta_xml):
            for f in files:
                if f.lower().endswith(".xml"):
                    archivos_procesados.append(os.path.join(root, f))

    if not archivos_procesados:
        print("[AVISO] No se encontraron archivos XML.")
        return

    # [3] Procesar XMLs → generar Excel base
    resultados = procesar_archivos_xml(archivos_procesados)
    if not resultados:
        print("[AVISO] No se obtuvieron datos válidos.")
        return

    ruta_excel = generar_excel(resultados)

    # [4] Optimización de stock
    print("\n[OPTIMIZANDO] Ejecutando optimizador de stock...")
    ruta_optimo = optimizar_stock(ruta_excel)

    # [5] Generar facturas simuladas desde optimización
    print("\n[FACTURANDO] Generando facturas simuladas de venta...")
    generar_facturas_desde_optimo(ruta_optimo)

    print("\n[OK] Proceso completo finalizado correctamente.")


if __name__ == "__main__":
    main()
