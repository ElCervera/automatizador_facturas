# Automatizador de Facturas

Herramienta para automatizar la lectura de facturas electrónicas de la DIAN en formato XML, aplicar reglas de conversión por proveedor y generar un archivo Excel consolidado.

## Estructura del Proyecto

```
automatizador_facturas/
├── facturas_zip/             # Carpeta donde se guardarán los archivos ZIP descargados de la DIAN
├── facturas_xml/             # Carpeta donde se descomprimirán los XML automáticamente
├── resultados/               # Carpeta donde se guardarán los Excel generados
├── reglas_conversion.json    # Archivo JSON con las reglas especiales por proveedor
├── main.py                   # Archivo principal que coordina el flujo
└── utils/
    └── lector_xml.py         # Módulo auxiliar para leer y procesar los XML
```

## Requisitos

- Python 3.6 o superior
- Bibliotecas requeridas:
  - pandas
  - openpyxl (para soporte de Excel)

Para instalar las dependencias:

```bash
pip install pandas openpyxl
```

## Uso

1. Coloca los archivos ZIP de facturas electrónicas descargados de la DIAN en la carpeta `facturas_zip/`.
2. Ejecuta el programa principal:

```bash
python main.py
```

3. El programa descomprimirá automáticamente los archivos ZIP, procesará los XML y generará un archivo Excel en la carpeta `resultados/`.

## Reglas de Conversión

Las reglas de conversión se definen en el archivo `reglas_conversion.json`. Cada proveedor puede tener reglas específicas para convertir unidades. Por ejemplo:

```json
{
  "Granja San Pedro": {"factor": 30, "tipo_objetivo": "Huevo"}
}
```

Esto significa que para el proveedor "Granja San Pedro", cada unidad en la factura (por ejemplo, una cubeta) se convertirá a 30 huevos.

## Personalización

Para agregar nuevas reglas de conversión, simplemente edita el archivo `reglas_conversion.json` y agrega nuevos proveedores con sus respectivos factores de conversión y tipos objetivo.

## Formato del Excel Generado

El archivo Excel generado contendrá las siguientes columnas:
- PROVEEDOR: Nombre del proveedor
- Día: Día de emisión de la factura
- N factura: Número de factura
- Tipo: Tipo de producto (según reglas de conversión)
- Cantidad: Cantidad convertida según reglas
- Valor Unitario: Precio unitario ajustado según factor de conversión