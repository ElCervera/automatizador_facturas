"""
Automatizador de Facturas — Fase 2 Corregido:
Descomprime ZIPs, organiza PDFs y XMLs por año/mes usando datos reales del XML.
"""
import os
import zipfile
import shutil
import datetime
import re
import xml.etree.ElementTree as ET
from utils.lector_xml import procesar_xml, aplicar_reglas_conversion, cargar_reglas_conversion

# Namespaces para XML DIAN
NAMESPACES = {
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
    'sts': 'dian:gov:co:facturaelectronica:Structures-2-1'
}

def crear_estructura_carpetas(ruta_base, año, mes):
    """Crea la estructura de carpetas por año y mes si no existen."""
    ruta_completa = os.path.join(ruta_base, str(año), mes)
    os.makedirs(ruta_completa, exist_ok=True)
    return ruta_completa

def extraer_datos_desde_xml(ruta_xml):
    """
    Extrae fecha y número de factura desde el contenido XML real de facturas DIAN.
    Basado en la estructura real del XML proporcionado.
    """
    try:
        tree = ET.parse(ruta_xml)
        root = tree.getroot()

        # Extraer número de factura (ID)
        numero_factura = root.findtext('.//cbc:ID', namespaces=NAMESPACES)
        if not numero_factura:
            # Intentar extraer del QR code en las extensiones DIAN
            qr_code = root.findtext('.//sts:QRCode', namespaces=NAMESPACES)
            if qr_code:
                for linea in qr_code.split('\n'):
                    if linea.startswith('NumFac:'):
                        numero_factura = linea.replace('NumFac:', '').strip()
                        break

        # Extraer fecha de emisión
        fecha_emision = root.findtext('.//cbc:IssueDate', namespaces=NAMESPACES)
        if not fecha_emision:
            # Intentar extraer del QR code
            qr_code = root.findtext('.//sts:QRCode', namespaces=NAMESPACES)
            if qr_code:
                for linea in qr_code.split('\n'):
                    if linea.startswith('FecFac:'):
                        fecha_emision = linea.replace('FecFac:', '').strip()
                        break

        # Procesar fecha
        if fecha_emision:
            try:
                # Formato: YYYY-MM-DD
                fecha = datetime.datetime.strptime(fecha_emision, '%Y-%m-%d')
                año = str(fecha.year)
                mes_num = fecha.strftime("%m")
                
                meses = {
                    "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
                    "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
                    "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
                }
                mes_nombre = meses.get(mes_num, "Desconocido")
                
                # Si no hay número de factura, usar parte de la fecha como fallback
                if not numero_factura:
                    numero_factura = f"FACT_{fecha.strftime('%Y%m%d')}"
                
                return año, mes_nombre, numero_factura
                
            except ValueError as e:
                print(f"⚠️ Error procesando fecha {fecha_emision}: {e}")
    
    except Exception as e:
        print(f"⚠️ Error extrayendo datos del XML {ruta_xml}: {e}")
    
    # Fallback: usar fecha actual y nombre del archivo
    return obtener_datos_desde_nombre(os.path.basename(ruta_xml))

def obtener_datos_desde_nombre(nombre_archivo):
    """Función auxiliar para extraer datos del nombre cuando no hay XML o falla la extracción."""
    meses = {
        "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
        "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
        "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
    }
    
    # Extraer nombre base sin extensión
    nombre_base = os.path.splitext(nombre_archivo)[0]
    
    # Patrones comunes en nombres de archivos de factura
    patrones = [
        r'FV[_-]?(\d+)',  # FV-12345, FV_12345, FV12345
        r'FE[_-]?(\d+)',  # FE-12345, FE_12345, FE12345
        r'FACT[_-]?(\d+)',  # FACT-12345, FACT_12345
        r'(\d{4}[-_]?\d{2}[-_]?\d{2})',  # Fechas YYYY-MM-DD
    ]
    
    numero_factura = nombre_base  # Valor por defecto
    
    for patron in patrones:
        match = re.search(patron, nombre_archivo, re.IGNORECASE)
        if match:
            numero_factura = match.group(1)
            break
    
    # Buscar fecha en el nombre del archivo
    fecha_match = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', nombre_archivo)
    if fecha_match:
        año = fecha_match.group(1)
        mes_num = fecha_match.group(2)
        mes_nombre = meses.get(mes_num, "Desconocido")
        return año, mes_nombre, numero_factura
    
    # Fallback: usar fecha actual
    hoy = datetime.datetime.now()
    año_default = str(hoy.year)
    mes_default = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }[hoy.month]
    
    return año_default, mes_default, numero_factura

def procesar_archivos_zip(carpeta_zip, carpeta_xml, carpeta_pdf):
    """
    Procesa ZIPs y organiza PDFs y XMLs correlacionándolos.
    Extrae datos reales del XML para nombrar y organizar ambos archivos.
    """
    if not os.path.exists(carpeta_zip):
        print(f"⚠️ La carpeta {carpeta_zip} no existe.")
        return []

    os.makedirs(carpeta_xml, exist_ok=True)
    os.makedirs(carpeta_pdf, exist_ok=True)
    
    carpeta_temp = os.path.join(os.getcwd(), "temp_extraction")
    os.makedirs(carpeta_temp, exist_ok=True)
    
    zips_encontrados = False
    archivos_xml_procesados = []  # Solo XMLs para procesamiento posterior
    archivos_existentes = set()

    # Recopilar archivos existentes
    for root, _, files in os.walk(carpeta_xml):
        for file in files:
            if file.lower().endswith(".xml"):
                archivos_existentes.add(file)
    
    for root, _, files in os.walk(carpeta_pdf):
        for file in files:
            if file.lower().endswith(".pdf"):
                archivos_existentes.add(file)

    for archivo_zip in os.listdir(carpeta_zip):
        if not archivo_zip.lower().endswith(".zip"):
            continue
            
        zips_encontrados = True
        ruta_zip = os.path.join(carpeta_zip, archivo_zip)
        
        try:
            with zipfile.ZipFile(ruta_zip, "r") as zip_ref:
                contenido = zip_ref.namelist()
                archivos_validos = [f for f in contenido if f.lower().endswith((".xml", ".pdf"))]
                
                if not archivos_validos:
                    print(f"⚠️ ZIP sin facturas válidas: {archivo_zip}")
                    continue
                
                # Extraer todo primero
                zip_ref.extractall(carpeta_temp)
                
                # Buscar XML para extraer datos reales
                xml_files = [f for f in archivos_validos if f.lower().endswith(".xml")]
                datos_factura = None
                ruta_xml_temp = None
                
                if xml_files:
                    # Procesar el primer XML encontrado para obtener datos
                    ruta_xml_temp = os.path.join(carpeta_temp, xml_files[0])
                    if os.path.exists(ruta_xml_temp):
                        print(f"📄 Extrayendo datos del XML: {xml_files[0]}")
                        datos_factura = extraer_datos_desde_xml(ruta_xml_temp)
                
                # Si no hay XML o no se pudieron extraer datos, usar nombre del archivo
                if not datos_factura:
                    print(f"⚠️ No se pudieron extraer datos del XML, usando nombre del archivo")
                    año, mes, numero_factura = obtener_datos_desde_nombre(archivo_zip)
                else:
                    año, mes, numero_factura = datos_factura
                
                print(f"📋 Datos extraídos: Año={año}, Mes={mes}, Factura={numero_factura}")
                
                # Procesar cada archivo en el ZIP
                for nombre_archivo in archivos_validos:
                    ruta_temp = os.path.join(carpeta_temp, nombre_archivo)
                    
                    if not os.path.exists(ruta_temp):
                        continue
                    
                    # Limpiar nombre del archivo para evitar problemas
                    nombre_limpio = re.sub(r'[<>:"/\\|?*]', '_', nombre_archivo)
                    
                    if nombre_limpio in archivos_existentes:
                        print(f"⚠️ Archivo repetido: {nombre_limpio}")
                        os.remove(ruta_temp)
                        continue
                    
                    if nombre_archivo.lower().endswith(".xml"):
                        carpeta_destino = crear_estructura_carpetas(carpeta_xml, año, mes)
                        # Renombrar XML con número de factura
                        nuevo_nombre = f"{numero_factura}.xml"
                        ruta_destino = os.path.join(carpeta_destino, nuevo_nombre)
                        
                        if os.path.exists(ruta_destino):
                            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                            nuevo_nombre = f"{numero_factura}_{timestamp}.xml"
                            ruta_destino = os.path.join(carpeta_destino, nuevo_nombre)
                            print(f"⚠️ Renombrando XML existente: {nuevo_nombre}")
                        
                        shutil.move(ruta_temp, ruta_destino)
                        print(f"📦 XML organizado: {nombre_archivo} → {os.path.join(año, mes, nuevo_nombre)}")
                        archivos_xml_procesados.append(ruta_destino)
                        archivos_existentes.add(nuevo_nombre)
                        
                    elif nombre_archivo.lower().endswith(".pdf"):
                        carpeta_destino = crear_estructura_carpetas(carpeta_pdf, año, mes)
                        # Renombrar PDF con número de factura
                        nuevo_nombre = f"{numero_factura}.pdf"
                        ruta_destino = os.path.join(carpeta_destino, nuevo_nombre)
                        
                        if os.path.exists(ruta_destino):
                            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                            nuevo_nombre = f"{numero_factura}_{timestamp}.pdf"
                            ruta_destino = os.path.join(carpeta_destino, nuevo_nombre)
                            print(f"⚠️ Renombrando PDF existente: {nuevo_nombre}")
                        
                        shutil.move(ruta_temp, ruta_destino)
                        print(f"📄 PDF organizado: {nombre_archivo} → {os.path.join(año, mes, nuevo_nombre)}")
                        archivos_existentes.add(nuevo_nombre)
                
            # Limpiar carpeta temporal y eliminar ZIP procesado
            if os.path.exists(carpeta_temp):
                shutil.rmtree(carpeta_temp)
                os.makedirs(carpeta_temp, exist_ok=True)
            
            os.remove(ruta_zip)
            print(f"✅ ZIP procesado y eliminado: {archivo_zip}")
            
        except zipfile.BadZipFile:
            print(f"❌ Archivo ZIP corrupto o inválido: {archivo_zip}")
        except Exception as e:
            print(f"❌ Error procesando ZIP {archivo_zip}: {str(e)}")

    # Limpieza final
    if os.path.exists(carpeta_temp):
        shutil.rmtree(carpeta_temp)

    if not zips_encontrados:
        print("⚠️ No se encontraron archivos ZIP en la carpeta de entrada.")
        
    return archivos_xml_procesados

def procesar_archivos_xml(rutas_xml):
    """Procesa una lista de archivos XML y aplica las reglas de conversión."""
    reglas = cargar_reglas_conversion()
    resultados = []
    
    for ruta in rutas_xml:
        nombre_archivo = os.path.basename(ruta)
        print(f"\n🔍 Procesando XML: {nombre_archivo}")
        
        factura = procesar_xml(ruta)
        if factura:
            datos_convertidos = aplicar_reglas_conversion(factura, reglas)
            for item in datos_convertidos:
                print(f"  ✅ Item: {item['Tipo']} - Cantidad: {item['Cantidad']}")
                resultados.append(item)
        else:
            print(f"❌ Error al procesar {nombre_archivo}")
    
    return resultados

def buscar_xmls_existentes(carpeta_xml):
    """Busca archivos XML en la estructura de carpetas por año/mes."""
    archivos_encontrados = []
    
    for año in os.listdir(carpeta_xml):
        ruta_año = os.path.join(carpeta_xml, año)
        if os.path.isdir(ruta_año):
            for mes in os.listdir(ruta_año):
                ruta_mes = os.path.join(ruta_año, mes)
                if os.path.isdir(ruta_mes):
                    for archivo in os.listdir(ruta_mes):
                        if archivo.lower().endswith(".xml"):
                            ruta_completa = os.path.join(ruta_mes, archivo)
                            archivos_encontrados.append(ruta_completa)
    
    return archivos_encontrados

def generar_excel(resultados, carpeta_resultados):
    """Genera un archivo Excel con los resultados procesados."""
    try:
        import pandas as pd
        from datetime import datetime
        
        os.makedirs(carpeta_resultados, exist_ok=True)
        
        df = pd.DataFrame(resultados)
        
        fecha_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"facturas_consolidadas_{fecha_hora}.xlsx"
        ruta_excel = os.path.join(carpeta_resultados, nombre_archivo)
        
        df.to_excel(ruta_excel, index=False)
        
        print(f"📊 Excel generado: {nombre_archivo}")
        return ruta_excel
    except ImportError:
        print("❌ Error: Se requiere pandas para generar el Excel.")
        return None
    except Exception as e:
        print(f"❌ Error al generar Excel: {str(e)}")
        return None

def main():
    print("=== AUTOMATIZADOR DE FACTURAS — FASE 2 CORREGIDO ===")

    carpeta_zip = os.path.join(os.getcwd(), "facturas_zip")
    carpeta_xml = os.path.join(os.getcwd(), "facturas_xml")
    carpeta_pdf = os.path.join(os.getcwd(), "facturas_pdf")
    carpeta_resultados = os.path.join(os.getcwd(), "resultados")

    # Paso 1: Descomprimir ZIPs y organizar archivos
    print("\n📦 Procesando archivos ZIP...")
    archivos_procesados = procesar_archivos_zip(carpeta_zip, carpeta_xml, carpeta_pdf)

    # Paso 2: Si no hay archivos recién procesados, buscar XMLs existentes
    if not archivos_procesados:
        print("\n🔍 Buscando XMLs existentes en la estructura de carpetas...")
        archivos_procesados = buscar_xmls_existentes(carpeta_xml)

    # Paso 3: Procesar los XMLs encontrados
    if archivos_procesados:
        print(f"\n📄 Procesando {len(archivos_procesados)} archivos XML...")
        resultados = procesar_archivos_xml(archivos_procesados)
        
        # Paso 4: Generar Excel con los resultados
        if resultados:
            ruta_excel = generar_excel(resultados, carpeta_resultados)
            if ruta_excel:
                print(f"\n✅ Procesamiento completado: {len(resultados)} items procesados y guardados en {ruta_excel}")
            else:
                print(f"\n⚠️ Procesamiento completado: {len(resultados)} items procesados, pero no se pudo generar el Excel.")
        else:
            print("\n⚠️ No se obtuvieron resultados del procesamiento de XMLs.")
    else:
        print("\n⚠️ No se encontraron archivos XML para procesar.")

if __name__ == "__main__":
    main()