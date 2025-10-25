"""
Automatizador de Facturas — Fase 1:
Descomprime ZIPs, extrae XMLs y muestra su contenido por consola.
"""
import os
import zipfile
from utils.lector_xml import procesar_xml, aplicar_reglas_conversion, cargar_reglas_conversion

def extraer_zips(carpeta_zip, carpeta_xml):
    """Extrae todos los ZIP y deja solo los archivos XML en facturas_xml."""
    if not os.path.exists(carpeta_zip):
        print(f"⚠️ La carpeta {carpeta_zip} no existe.")
        return

    os.makedirs(carpeta_xml, exist_ok=True)
    zips_encontrados = False

    for archivo in os.listdir(carpeta_zip):
        if archivo.lower().endswith(".zip"):
            zips_encontrados = True
            ruta_zip = os.path.join(carpeta_zip, archivo)
            with zipfile.ZipFile(ruta_zip, "r") as zip_ref:
                for nombre in zip_ref.namelist():
                    if nombre.lower().endswith(".xml"):
                        zip_ref.extract(nombre, carpeta_xml)
                        print(f"📦 Extraído XML: {nombre}")
                    elif nombre.lower().endswith(".pdf"):
                        # Si prefieres eliminar los PDF tras extraerlos, puedes omitir esta línea:
                        print(f"📄 Ignorado PDF: {nombre}")
            print(f"✅ ZIP procesado: {archivo}")

    if not zips_encontrados:
        print("⚠️ No se encontraron archivos ZIP en la carpeta de entrada.")

def main():
    print("=== AUTOMATIZADOR DE FACTURAS — FASE 1 ===")

    carpeta_zip = os.path.join(os.getcwd(), "facturas_zip")
    carpeta_xml = os.path.join(os.getcwd(), "facturas_xml")

    # Paso 1: Descomprimir ZIPs
    extraer_zips(carpeta_zip, carpeta_xml)

    # Paso 2: Leer y mostrar los XML procesados
    print("\n📄 Leyendo XMLs extraídos...")
    archivos_xml = [f for f in os.listdir(carpeta_xml) if f.lower().endswith(".xml")]

    if not archivos_xml:
        print("⚠️ No se encontraron XML para procesar.")
        return

    reglas = cargar_reglas_conversion()

    for archivo in archivos_xml:
        ruta = os.path.join(carpeta_xml, archivo)
        print(f"\n🔍 Procesando XML: {archivo}")
        factura = procesar_xml(ruta)
        if factura:
            datos_convertidos = aplicar_reglas_conversion(factura, reglas)
            for item in datos_convertidos:
                print(item)
        else:
            print(f"❌ Error al procesar {archivo}")

if __name__ == "__main__":
    main()
