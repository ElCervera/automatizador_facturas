"""
Automatizador de Facturas - Programa Principal

Este script coordina el flujo de trabajo para:
1. Descomprimir archivos ZIP de facturas electrónicas
2. Procesar los archivos XML
3. Aplicar reglas de conversión por proveedor
4. Generar un archivo Excel consolidado
"""
import os
import zipfile
import glob
from datetime import datetime
from utils.lector_xml import procesar_xml, aplicar_reglas_conversion, generar_excel, cargar_reglas_conversion

# Rutas principales
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FACTURAS_ZIP_DIR = os.path.join(BASE_DIR, 'facturas_zip')
FACTURAS_XML_DIR = os.path.join(BASE_DIR, 'facturas_xml')
RESULTADOS_DIR = os.path.join(BASE_DIR, 'resultados')

def descomprimir_facturas():
    """
    Descomprime todos los archivos ZIP en la carpeta facturas_zip
    y los guarda en facturas_xml.
    """
    print("Descomprimiendo archivos ZIP...")
    
    # Obtener todos los archivos ZIP en la carpeta
    archivos_zip = glob.glob(os.path.join(FACTURAS_ZIP_DIR, '*.zip'))
    
    if not archivos_zip:
        print("No se encontraron archivos ZIP para procesar.")
        return False
    
    # Descomprimir cada archivo ZIP
    for archivo_zip in archivos_zip:
        try:
            with zipfile.ZipFile(archivo_zip, 'r') as zip_ref:
                zip_ref.extractall(FACTURAS_XML_DIR)
            print(f"Archivo {os.path.basename(archivo_zip)} descomprimido correctamente.")
        except Exception as e:
            print(f"Error al descomprimir {os.path.basename(archivo_zip)}: {e}")
    
    return True

def procesar_facturas():
    """
    Procesa todos los archivos XML en la carpeta facturas_xml,
    aplica las reglas de conversión y genera un Excel consolidado.
    """
    print("Procesando archivos XML...")
    
    # Cargar reglas de conversión
    reglas = cargar_reglas_conversion()
    
    # Obtener todos los archivos XML en la carpeta
    archivos_xml = glob.glob(os.path.join(FACTURAS_XML_DIR, '*.xml'))
    
    if not archivos_xml:
        print("No se encontraron archivos XML para procesar.")
        return False
    
    # Procesar cada archivo XML
    datos_consolidados = []
    for archivo_xml in archivos_xml:
        try:
            print(f"Procesando {os.path.basename(archivo_xml)}...")
            datos_factura = procesar_xml(archivo_xml)
            
            if datos_factura:
                # Aplicar reglas de conversión
                datos_convertidos = aplicar_reglas_conversion(datos_factura, reglas)
                datos_consolidados.extend(datos_convertidos)
        except Exception as e:
            print(f"Error al procesar {os.path.basename(archivo_xml)}: {e}")
    
    if not datos_consolidados:
        print("No se pudo extraer información de ninguna factura.")
        return False
    
    # Generar archivo Excel con los datos consolidados
    fecha_actual = datetime.now().strftime('%Y%m%d_%H%M%S')
    ruta_excel = os.path.join(RESULTADOS_DIR, f'facturas_consolidadas_{fecha_actual}.xlsx')
    
    if generar_excel(datos_consolidados, ruta_excel):
        print(f"Archivo Excel generado correctamente: {os.path.basename(ruta_excel)}")
        return True
    else:
        print("Error al generar el archivo Excel.")
        return False

def main():
    """
    Función principal que coordina el flujo del programa.
    """
    print("=== AUTOMATIZADOR DE FACTURAS ===")
    
    # Verificar que existan las carpetas necesarias
    for directorio in [FACTURAS_ZIP_DIR, FACTURAS_XML_DIR, RESULTADOS_DIR]:
        if not os.path.exists(directorio):
            os.makedirs(directorio)
            print(f"Carpeta creada: {os.path.basename(directorio)}")
    
    # Paso 1: Descomprimir archivos ZIP
    if descomprimir_facturas():
        # Paso 2: Procesar facturas y generar Excel
        procesar_facturas()
    
    print("Proceso completado.")

if __name__ == "__main__":
    main()