"""
Módulo para leer y procesar archivos XML de facturas electrónicas de la DIAN.
"""
import os
import xml.etree.ElementTree as ET
import json
import pandas as pd
from datetime import datetime

# Namespaces utilizados en los XML de la DIAN
NAMESPACES = {
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'fe': 'dian:gov:co:facturaelectronica:NombreEsquema'
}

def cargar_reglas_conversion():
    """
    Carga las reglas de conversión desde el archivo JSON.
    
    Returns:
        dict: Diccionario con las reglas de conversión por proveedor.
    """
    ruta_reglas = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reglas_conversion.json')
    with open(ruta_reglas, 'r', encoding='utf-8') as archivo:
        return json.load(archivo)

def procesar_xml(ruta_xml):
    """
    Procesa un archivo XML de factura electrónica y extrae la información relevante.
    
    Args:
        ruta_xml (str): Ruta al archivo XML a procesar.
        
    Returns:
        dict: Diccionario con la información extraída del XML.
    """
    try:
        # Parsear el archivo XML
        tree = ET.parse(ruta_xml)
        root = tree.getroot()
        
        # Extraer información básica de la factura
        numero_factura = root.find('.//cbc:ID', NAMESPACES).text
        fecha_emision = root.find('.//cbc:IssueDate', NAMESPACES).text
        fecha_obj = datetime.strptime(fecha_emision, '%Y-%m-%d')
        
        # Extraer información del proveedor
        proveedor_node = root.find('.//cac:AccountingSupplierParty', NAMESPACES)
        nombre_proveedor = proveedor_node.find('.//cbc:RegistrationName', NAMESPACES).text
        
        # Extraer información de los productos
        items = []
        for item_node in root.findall('.//cac:InvoiceLine', NAMESPACES):
            try:
                descripcion = item_node.find('.//cbc:Description', NAMESPACES).text
                cantidad = float(item_node.find('.//cbc:InvoicedQuantity', NAMESPACES).text)
                precio_unitario = float(item_node.find('.//cac:Price/cbc:PriceAmount', NAMESPACES).text)
                
                items.append({
                    'descripcion': descripcion,
                    'cantidad': cantidad,
                    'precio_unitario': precio_unitario
                })
            except (AttributeError, ValueError) as e:
                print(f"Error al procesar ítem en factura {numero_factura}: {e}")
        
        return {
            'proveedor': nombre_proveedor,
            'dia': fecha_obj.day,
            'numero_factura': numero_factura,
            'fecha': fecha_obj,
            'items': items
        }
    
    except Exception as e:
        print(f"Error al procesar el archivo {ruta_xml}: {e}")
        return None

def aplicar_reglas_conversion(datos_factura, reglas):
    """
    Aplica las reglas de conversión a los datos de la factura.
    
    Args:
        datos_factura (dict): Datos extraídos de la factura.
        reglas (dict): Reglas de conversión por proveedor.
        
    Returns:
        list: Lista de diccionarios con los datos convertidos.
    """
    resultado = []
    proveedor = datos_factura['proveedor']
    
    # Verificar si hay reglas específicas para este proveedor
    regla_proveedor = reglas.get(proveedor, {'factor': 1, 'tipo_objetivo': 'Unidad'})
    
    for item in datos_factura['items']:
        # Aplicar factor de conversión si existe
        cantidad_convertida = item['cantidad'] * regla_proveedor.get('factor', 1)
        tipo = regla_proveedor.get('tipo_objetivo', 'Unidad')
        
        resultado.append({
            'PROVEEDOR': proveedor,
            'Dia': datos_factura['dia'],
            'N factura': datos_factura['numero_factura'],
            'Tipo': tipo,
            'Cantidad': cantidad_convertida,
            'Valor Unitario': item['precio_unitario'] / regla_proveedor.get('factor', 1) if regla_proveedor.get('factor', 1) > 0 else item['precio_unitario']
        })
    
    return resultado

def generar_excel(datos_procesados, ruta_salida):
    """
    Genera un archivo Excel con los datos procesados.
    
    Args:
        datos_procesados (list): Lista de diccionarios con los datos procesados.
        ruta_salida (str): Ruta donde se guardará el archivo Excel.
        
    Returns:
        bool: True si se generó correctamente, False en caso contrario.
    """
    try:
        df = pd.DataFrame(datos_procesados)
        df.to_excel(ruta_salida, index=False)
        return True
    except Exception as e:
        print(f"Error al generar el archivo Excel: {e}")
        return False