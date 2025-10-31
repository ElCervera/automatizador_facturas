"""
Módulo para leer y procesar archivos XML de facturas electrónicas de la DIAN.
CORREGIDO: Incluye trazabilidad de conversiones y datos originales.
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

def _to_float(value):
    """Convierte texto a float manejando comas, vacíos y None."""
    if value is None:
        return 0.0
    if isinstance(value, str):
        val = value.strip().replace(',', '.')
    else:
        val = value
    try:
        return float(val)
    except Exception:
        return 0.0

def cargar_reglas_conversion():
    """Carga las reglas de conversión desde el archivo JSON."""
    ruta_reglas = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reglas_conversion.json')
    try:
        with open(ruta_reglas, 'r', encoding='utf-8') as archivo:
            reglas = json.load(archivo)
            print(f"📋 Reglas cargadas: {len(reglas)} proveedores")
            for proveedor, regla in reglas.items():
                print(f"   - {proveedor}: factor {regla.get('factor', 1)}")
            return reglas
    except Exception as e:
        print(f"⚠️ Error cargando reglas: {e}. Usando reglas por defecto.")
        return {}

def procesar_xml(ruta_xml):
    """
    Procesa archivos XML DIAN estándar o anidados en AttachedDocument (CDATA).
    Soporta múltiples namespaces y estructuras diferentes.
    """
    import xml.etree.ElementTree as ET
    from datetime import datetime

    try:
        # === 1️⃣ Parsear XML base ===
        tree = ET.parse(ruta_xml)
        root = tree.getroot()

        # Si el documento es un AttachedDocument, hay un XML dentro del CDATA
        if root.tag.endswith("AttachedDocument"):
            descripcion_node = root.find('.//cbc:Description', namespaces=NAMESPACES)
            if descripcion_node is not None and descripcion_node.text:
                contenido_cdata = descripcion_node.text.strip()

                # A veces el contenido del CDATA tiene caracteres extra antes del XML real
                inicio_xml = contenido_cdata.find("<")
                if inicio_xml > 0:
                    contenido_cdata = contenido_cdata[inicio_xml:]

                try:
                    # Parsear el XML interno dentro del CDATA
                    root = ET.fromstring(contenido_cdata)
                except ET.ParseError as e:
                    print(f"❌ Error parseando XML embebido en {ruta_xml}: {e}")
                    return None

        # === 2️⃣ Extraer datos principales ===
        numero_factura = (
            root.findtext('.//cbc:ID', namespaces=NAMESPACES)
            or root.findtext('.//fe:ID', namespaces=NAMESPACES)
            or "SIN_ID"
        )

        fecha_emision = (
            root.findtext('.//cbc:IssueDate', namespaces=NAMESPACES)
            or root.findtext('.//fe:IssueDate', namespaces=NAMESPACES)
            or datetime.now().strftime('%Y-%m-%d')
        )

        try:
            fecha_obj = datetime.strptime(fecha_emision, '%Y-%m-%d')
        except ValueError:
            try:
                fecha_obj = datetime.strptime(fecha_emision, '%Y/%m/%d')
            except ValueError:
                fecha_obj = datetime.now()

        # === 3️⃣ Extraer datos del proveedor ===
        posibles_nodos = [
            './/cac:AccountingSupplierParty',
            './/fe:AccountingSupplierParty',
            './/cac:SenderParty',
            './/cac:Party'
        ]

        proveedor_node = None
        for path in posibles_nodos:
            proveedor_node = root.find(path, NAMESPACES)
            if proveedor_node is not None:
                break

        nombre_proveedor = None
        nit_proveedor = None

        if proveedor_node is not None:
            posibles_nombre = [
                './/cbc:RegistrationName',
                './/fe:RegistrationName',
                './/cbc:Name'
            ]
            posibles_nit = [
                './/cbc:CompanyID',
                './/fe:CompanyID',
                './/cbc:ID'
            ]
            for p in posibles_nombre:
                nombre_proveedor = proveedor_node.findtext(p, namespaces=NAMESPACES)
                if nombre_proveedor:
                    break
            for p in posibles_nit:
                nit_proveedor = proveedor_node.findtext(p, namespaces=NAMESPACES)
                if nit_proveedor:
                    break

        if not nombre_proveedor:
            nombre_proveedor = "Proveedor desconocido"
        if not nit_proveedor:
            nit_proveedor = "N/A"

        # === 4️⃣ Extraer ítems ===
        items = []
        posibles_items = [
            './/cac:InvoiceLine',
            './/fe:InvoiceLine'
        ]

        for path in posibles_items:
            try:
                nodes = root.findall(path, NAMESPACES)
            except KeyError:
                nodes = []
            for item_node in nodes:
                try:
                    descripcion = (
                        item_node.findtext('.//cbc:Description', namespaces=NAMESPACES)
                        or item_node.findtext('.//fe:Description', namespaces=NAMESPACES)
                        or "Producto desconocido"
                    )

                    descripcion_normalizada = normalizar_producto(descripcion)

                    cantidad_txt = (
                        item_node.findtext('.//cbc:InvoicedQuantity', namespaces=NAMESPACES)
                        or item_node.findtext('.//fe:InvoicedQuantity', namespaces=NAMESPACES)
                        or item_node.findtext('.//cbc:BaseQuantity', namespaces=NAMESPACES)
                        or 0
                    )
                    cantidad = _to_float(cantidad_txt)

                    precio_txt = (
                        item_node.findtext('.//cac:Price/cbc:PriceAmount', namespaces=NAMESPACES)
                        or item_node.findtext('.//fe:PriceAmount', namespaces=NAMESPACES)
                        or item_node.findtext('.//cbc:PriceAmount', namespaces=NAMESPACES)
                        or 0
                    )
                    precio_unitario = _to_float(precio_txt)

                    items.append({
                        'descripcion': descripcion_normalizada,
                        'cantidad_original': cantidad,  # GUARDAR ORIGINAL
                        'precio_unitario_original': precio_unitario,  # GUARDAR ORIGINAL
                        'cantidad': cantidad,  # Mantener para compatibilidad
                        'precio_unitario': precio_unitario  # Mantener para compatibilidad
                    })
                except Exception as e:
                    print(f"⚠️ Error leyendo ítem en {os.path.basename(ruta_xml)}: {e}")

        if not items:
            print(f"⚠️ No se encontraron ítems válidos en {os.path.basename(ruta_xml)}")
            return None

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
    CORREGIDO Y NORMALIZADO: nombres de columnas en minúsculas y consistentes con el optimizador.
    """
    resultado = []
    proveedor = datos_factura['proveedor']
    nit = datos_factura.get('nit_proveedor', 'N/A')

    regla_proveedor = reglas.get(proveedor, {'factor': 1, 'tipo_objetivo': 'Unidad'})
    factor = regla_proveedor.get('factor', 1)
    tipo_objetivo = regla_proveedor.get('tipo_objetivo', 'Unidad')

    print(f"🔧 Aplicando reglas a {proveedor}: factor={factor}, tipo={tipo_objetivo}")

    for item in datos_factura['items']:
        cantidad_original = item.get('cantidad_original', item['cantidad'])
        precio_original = item.get('precio_unitario_original', item['precio_unitario'])
        
        cantidad_convertida = cantidad_original * factor
        precio_convertido = precio_original / factor if factor > 0 else precio_original

        resultado.append({
            # --- Claves estandarizadas ---
            'nit_proveedor': nit,
            'proveedor': proveedor,
            'fecha': datos_factura['fecha'],
            'n_factura': datos_factura['numero_factura'],
            'tipo': item['descripcion'],

            # --- Datos numéricos coherentes con el optimizador ---
            'cantidad_convertida': cantidad_convertida,
            'cantidad': cantidad_convertida,
            'valor unitario': precio_convertido,

            # --- Auditoría opcional ---
            'cantidad_original': cantidad_original,
            'precio_unitario_original': precio_original,
            'factor_aplicado': factor,
            'tipo_conversion': tipo_objetivo,
            'proveedor_especial': 'SI' if factor != 1 else 'NO'
        })

    return resultado


def generar_excel(datos_procesados, ruta_salida):
    """Genera un archivo Excel con los datos procesados."""
    try:
        df = pd.DataFrame(datos_procesados)
        
        # Verificar conversiones especiales
        if 'Factor_Aplicado' in df.columns:
            factores = df['Factor_Aplicado'].unique()
            proveedores_especiales = df[df['Factor_Aplicado'] != 1]['PROVEEDOR'].unique()
            
            print(f"📊 RESUMEN DE CONVERSIONES:")
            print(f"   Factores aplicados: {factores}")
            if len(proveedores_especiales) > 0:
                print(f"   Proveedores con conversión especial: {list(proveedores_especiales)}")
        
        df.to_excel(ruta_salida, index=False)
        print(f"✅ Archivo Excel generado correctamente en: {ruta_salida}")
        return True
    except Exception as e:
        print(f"❌ Error al generar el archivo Excel: {e}")
        return False