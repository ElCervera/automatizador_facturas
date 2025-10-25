"""
Módulo para leer y procesar archivos XML de facturas electrónicas de la DIAN.
Actualizado: incluye NIT del proveedor, normalización de productos y fecha completa.
"""
import os
import xml.etree.ElementTree as ET
import json
import pandas as pd
from datetime import datetime
from utils.normalizador import normalizar_producto

# Namespaces utilizados en los XML de la DIAN
NAMESPACES = {
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'fe': 'dian:gov:co:facturaelectronica:NombreEsquema'
}

def cargar_reglas_conversion():
    """Carga las reglas de conversión desde el archivo JSON."""
    ruta_reglas = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reglas_conversion.json')
    with open(ruta_reglas, 'r', encoding='utf-8') as archivo:
        return json.load(archivo)

def procesar_xml(ruta_xml):
    """
    Procesa un archivo XML de factura electrónica y extrae la información relevante.
    Devuelve un diccionario con los datos de la factura.
    """
    try:
        tree = ET.parse(ruta_xml)
        root = tree.getroot()

        # Extraer información básica
        numero_factura = root.findtext('.//cbc:ID', namespaces=NAMESPACES)
        fecha_emision = root.findtext('.//cbc:IssueDate', namespaces=NAMESPACES)
        fecha_obj = datetime.strptime(fecha_emision, '%Y-%m-%d')

        # Extraer información del proveedor
        proveedor_node = root.find('.//cac:AccountingSupplierParty', NAMESPACES)
        nombre_proveedor = proveedor_node.findtext('.//cbc:RegistrationName', namespaces=NAMESPACES)
        nit_proveedor = proveedor_node.findtext('.//cbc:CompanyID', namespaces=NAMESPACES)

        # Extraer información de los productos
        items = []
        for item_node in root.findall('.//cac:InvoiceLine', NAMESPACES):
            try:
                descripcion = item_node.findtext('.//cbc:Description', namespaces=NAMESPACES)
                descripcion_normalizada = normalizar_producto(descripcion)
                cantidad = float(item_node.findtext('.//cbc:InvoicedQuantity', namespaces=NAMESPACES))
                precio_unitario = float(item_node.findtext('.//cac:Price/cbc:PriceAmount', namespaces=NAMESPACES))

                items.append({
                    'descripcion': descripcion_normalizada,
                    'cantidad': cantidad,
                    'precio_unitario': precio_unitario
                })
            except (AttributeError, ValueError) as e:
                print(f"⚠️ Error al procesar ítem en factura {numero_factura}: {e}")

        return {
            'nit_proveedor': nit_proveedor,
            'proveedor': nombre_proveedor,
            'fecha': fecha_obj.strftime('%d/%m/%Y'),
            'numero_factura': numero_factura,
            'items': items
        }

    except Exception as e:
        print(f"❌ Error al procesar el archivo {ruta_xml}: {e}")
        return None

def aplicar_reglas_conversion(datos_factura, reglas):
    """
    Aplica las reglas de conversión (por proveedor) a los datos de la factura.
    Devuelve una lista de diccionarios listos para exportar a Excel.
    """
    resultado = []
    proveedor = datos_factura['proveedor']
    nit = datos_factura.get('nit_proveedor', 'N/A')

    # Cargar la regla específica del proveedor, si existe
    regla_proveedor = reglas.get(proveedor, {'factor': 1, 'tipo_objetivo': 'Unidad'})

    for item in datos_factura['items']:
        cantidad_convertida = item['cantidad'] * regla_proveedor.get('factor', 1)
        tipo = regla_proveedor.get('tipo_objetivo', 'Unidad')

        resultado.append({
            'NIT_PROVEEDOR': nit,
            'PROVEEDOR': proveedor,
            'Fecha': datos_factura['fecha'],
            'N factura': datos_factura['numero_factura'],
            'Tipo': item['descripcion'],
            'Cantidad': cantidad_convertida,
            'Valor Unitario': (
                item['precio_unitario'] / regla_proveedor.get('factor', 1)
                if regla_proveedor.get('factor', 1) > 0 else item['precio_unitario']
            )
        })

    return resultado

def generar_excel(datos_procesados, ruta_salida):
    """Genera un archivo Excel con los datos procesados."""
    try:
        df = pd.DataFrame(datos_procesados)
        df.to_excel(ruta_salida, index=False)
        print(f"✅ Archivo Excel generado correctamente en: {ruta_salida}")
        return True
    except Exception as e:
        print(f"❌ Error al generar el archivo Excel: {e}")
        return False
