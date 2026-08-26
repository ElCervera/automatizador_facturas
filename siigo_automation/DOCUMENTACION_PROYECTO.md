# 📋 Documentación Completa - Automatizador de Facturas

> **Autor**: Sebastián Cortes (@ElCervera)  
> **Versión**: v3.0 (Fase 3 Optimizada)  
> **Año**: 2025

---

## 🎯 1. Visión General

El **Automatizador de Facturas** es un sistema desarrollado en **Python** que automatiza el procesamiento de **facturas electrónicas DIAN** (Colombia) en formato XML. El proyecto va más allá de la simple lectura de facturas: integra optimización de inventario, generación de facturas simuladas de venta, análisis de ventas históricas y una interfaz gráfica web completa para gestión de todo el flujo.

### Objetivos principales:
1. 📦 Descomprimir y organizar archivos ZIP de facturas (XML + PDF)
2. 📄 Extraer información estructurada de los XML de la DIAN
3. 📊 Consolidar datos y generar reportes Excel
4. 🧠 Optimizar la distribución del stock disponible
5. 🧾 Generar facturas de venta simuladas basadas en el stock óptimo
6. 💾 Persistir ventas reales en base de datos para análisis históricos
7. 📈 Proveer dashboard interactivo con visualizaciones y métricas

---

## 🛠️ 2. Tecnologías Utilizadas

| Tecnología | Versión/Type | Uso en el Proyecto |
|---|---|---|
| **Python** | 3.13+/3.14 | Lenguaje principal del backend |
| **Streamlit** | Última | Framework de interfaz gráfica web |
| **Pandas** | Última | Manipulación y análisis de datos (DataFrames) |
| **NumPy** | - | Cálculos numéricos y aleatoriedad |
| **OpenPyXL / XlsxWriter** | Última | Lectura y escritura de archivos Excel |
| **PuLP** | Última | **Programación Lineal** para optimización de stock (modo heurístico como fallback) |
| **Plotly** | Última | Visualizaciones gráficas interactivas (dashboard) |
| **Altair** | Última | Visualizaciones declarativas (fallback si no hay Plotly) |
| **SQLite3** | Integrado en Python | Base de datos embebida para ventas y auditoría |
| **XML (ElementTree)** | Librería estándar | Parseo de facturas electrónicas DIAN |
| **JSON** | Librería estándar | Archivos de configuración y diccionarios |
| **Regex (re)** | Librería estándar | Extracción de patrones en nombres de archivos |

### Instalación de dependencias:
```bash
pip install -r requirements.txt
```

---

## 🏗️ 3. Arquitectura del Sistema

El proyecto sigue una **arquitectura modular por capas**:

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFAZ DE USUARIO                      │
│                    (Streamlit - GUI)                         │
│                  gui_app.py                                  │
├─────────────────────────────────────────────────────────────┤
│                    ORQUESTACIÓN PRINCIPAL                    │
│                  main.py (Controlador)                       │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐  │
│  │ Lector XML │ │ Optim.     │ │ Generador  │ │ BD SQL   │  │
│  │ (utils)    │ │ Stock      │ │ Facturas   │ │ (utils)  │  │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘  │
│  ┌────────────┐ ┌────────────┐                               │
│  │ Normaliz.  │ │ Config     │  MÓDULOS / UTILS              │
│  │ Productos  │ │ Global     │                               │
│  └────────────┘ └────────────┘                               │
├─────────────────────────────────────────────────────────────┤
│  Archivos XML │ Excel Reports │ JSON Config │ SQLite DB      │
│  (Persistencia - File System)                               │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Datos (Pipeline completo):
1. **Entrada**: Archivos ZIP con XML/PDF de facturas de proveedores
2. **Extracción**: Descompresión → Organización por Año/Mes
3. **Parseo XML**: Lectura estructurada de la factura DIAN
4. **Normalización**: Homogeneización de nombres de productos
5. **Conversión**: Aplicación de reglas por proveedor (factor de conversión)
6. **Consolidación**: Generación de Excel base consolidado
7. **Optimización**: Cálculo de stock óptimo a vender
8. **Simulación**: Generación de facturas de venta distribuidas por días hábiles
9. **Persistencia**: Carga de ventas reales a SQLite + Auditoría
10. **Visualización**: Dashboard Streamlit con métricas y gráficos

---

## 📁 4. Estructura Completa de Carpetas

```
automatizador_facturas/
│
├── 📄 main.py                      # Punto de entrada CLI (orquestación completa)
├── 📄 gui_app.py                   # Aplicación Streamlit (interfaz web)
├── 📄 requirements.txt             # Dependencias del proyecto
├── 📄 README.md                    # Readme básico
│
├── 📄 check_prices.py              # Script auxiliar: verifica precios en stock
├── 📄 debug_check.py               # Script auxiliar: diagnóstico de rutas
├── 📄 limpiar_db.py                # Script auxiliar: vacía tablas de la BD
│
├── 📄 normalizacion_productos.json # Diccionario de normalización de productos
├── 📄 reglas_conversion.json       # Reglas de conversión por proveedor
│
├── 📄 automatizador.db             # Base de datos SQLite principal
├── 📄 ventas.db                    # (Referencia) Otra BD potencial
│
├── 📁 utils/                       # MÓDULOS CORE (paquete Python)
│   ├── __init__.py                 # (Implícito - paquete)
│   ├── 📄 config.py                # Configuración global y constantes
│   ├── 📄 database.py              # Operaciones SQLite (CRUD + conexiones)
│   ├── 📄 lector_xml.py            # Parseo de XML DIAN + reglas de conversión
│   ├── 📄 normalizador.py          # Normalización de nombres de productos
│   ├── 📄 optimizador_stock.py     # Optimización de inventario
│   └── 📄 generador_facturas.py    # Generador de facturas simuladas
│
├── 📁 facturas_zip/                # [ENTRADA] ZIPs pendientes de procesar
│
├── 📁 facturas_xml/                # [ALMACENAMIENTO] XMLs organizados
│   └── 📁 2025/
│       ├── 📁 Enero/
│       ├── 📁 Febrero/
│       └── ...
│
├── 📁 facturas_pdf/                # [ALMACENAMIENTO] PDFs organizados
│   └── 📁 [Año]/[Mes]/
│
└── 📁 resultados/                  # [SALIDA] Reportes Excel generados
    ├── facturas_consolidadas_YYYYMMDD_HHMMSS.xlsx
    ├── stock_optimizado_YYYYMMDD_HHMMSS.xlsx
    └── facturas_generadas_YYYYMMDD_HHMMSS.xlsx
```

---

## 🔍 5. Descripción Detallada de Módulos y Archivos

---

### 5.1 Puntos de Entrada

#### [main.py](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/main.py) — Orquestador CLI
**Propósito**: Ejecutar el flujo completo desde línea de comandos.

**Funciones clave**:
| Función | Ubicación | Descripción |
|---|---|---|
| `crear_estructura_carpetas()` | [L34-L37](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/main.py#L34-L37) | Crea estructura `Año/Mes` |
| `extraer_datos_desde_xml()` | [L40-L72](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/main.py#L40-L72) | Extrae N° factura + fecha desde XML (o QR fallback) |
| `obtener_datos_desde_nombre()` | [L75-L100](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/main.py#L75-L100) | Fallback: parsea el nombre del archivo si XML falla |
| `procesar_archivos_zip()` | [L103-L168](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/main.py#L103-L168) | Descomprime ZIPs, extrae XML/PDF, organiza en carpetas |
| `procesar_archivos_xml()` | [L174-L186](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/main.py#L174-L186) | Recorre XMLs y aplica parsing + reglas |
| `generar_excel()` | [L189-L202](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/main.py#L189-L202) | Genera Excel consolidado desde lista de resultados |
| `main()` | [L208-L246](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/main.py#L208-L246) | **Pipeline completo**: ZIP → XML → Excel → Optimización → Facturas |

**Namespaces XML DIAN** (líneas [23-28](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/main.py#L23-L28)):
- `cbc`: UBL Common Basic Components
- `cac`: UBL Common Aggregate Components
- `ext`: Common Extension Components
- `sts`: Estructura DIAN colombiana

---

#### [gui_app.py](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/gui_app.py) — Interfaz Streamlit
**Propósito**: Aplicación web interactiva con 6 secciones principales.

**Secciones de navegación**:
| Opción de Menú | Líneas | Funcionalidad |
|---|---|---|
| 🏠 **Dashboard** | [L258-L625](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/gui_app.py#L258-L625) | Métricas, filtros fecha, gráficos mensuales (utilidad, stock, ventas) |
| ⚙️ **Pasos Individuales** | [L629-L856](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/gui_app.py#L629-L856) | Tabs: Subir ZIP → Subir XML → Generar Excel |
| 🚀 **Proceso Completo** | [L860-L982](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/gui_app.py#L860-L982) | Flujo end-to-end en un click |
| 💾 **Gestión Resultados** | [L983-L1027](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/gui_app.py#L983-L1027) | Listar, descargar, eliminar archivos Excel |
| 📈 **Ventas Reales (BD)** | [L1031-L1072](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/gui_app.py#L1031-L1072) | Importar Excel ventas → Analizar en DB |
| 🔍 **Análisis por Producto** | [L1076-L1176](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/gui_app.py#L1076-L1176) | Métricas desglosadas por tipo de huevo |

**Funciones auxiliares** en GUI:
- `get_monthly_sales_from_db()` — Ventas totales por mes/año
- `get_product_metrics_from_db()` — Métricas por producto
- `guardar_archivo_subido()` / `eliminar_archivo()` — Gestión de archivos
- `get_files_info()` — Listado con metadatos (tamaño, fecha)
- `calculate_optimized_stock_value()` — Valor monetario del stock óptimo
- `get_excel_column_sum()` — Suma una columna específica de Excel

---

### 5.2 Módulo Utils (Paquete Core)

#### [utils/config.py](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/config.py) — Configuración Global
**Constantes críticas**:
| Constante | Valor | Significado |
|---|---|---|
| `EXCLUIR_NITS` | `[]` | NITs de proveedores a filtrar |
| `EXCLUIR_PRODUCTOS` | `["HUEVO QUEBRADO", "HUEVO ROJO P"]` | Productos NO comercializables |
| `CARPETA_RESULTADOS` | `./resultados` | Directorio de salida |
| `VENTA_DIARIA_MIN/MAX` | `5M / 20M COP` | Límites de venta diaria |
| `MIN_HUEVOS` | `300` | Mínimo por factura (10 cubetas × 30) |
| `MAX_HUEVOS` | `1500` | Máximo por factura (50 cubetas) |
| `MULTIPLE_HUEVOS` | `150` | Múltiplo obligatorio (5 cubetas) |
| `TOLERANCIA_RECONCILIACION` | `150` | Margen para ajustes de redondeo |

---

#### [utils/database.py](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/database.py) — SQLite Operations
**Base de Datos**: `automatizador.db` (SQLite embebido)

**Tablas**:
1. **`ventas_reales`** — Ventas históricas reales
2. **`clientes`** — Catálogo de clientes (unicidad por nombre)
3. **`auditoria`** — Log de acciones del sistema

```sql
-- Estructura ventas_reales:
id (PK), fecha (TEXT), anio (INT), mes (TEXT), dia (INT),
n_factura (TEXT), tipo (TEXT), cantidad_huevos (INT),
precio_unitario (REAL), valor_total (REAL),
cliente (TEXT), observaciones (TEXT)
```

**Funciones API expuestas**:
| Función | Descripción |
|---|---|
| `get_conn()` | Conexión SQLite thread-safe |
| `inicializar_db()` | Crea tablas si no existen |
| `log_accion(accion, detalle)` | Inserta en tabla `auditoria` |
| `safe_float() / safe_int()` | Parseo robusto de números |
| `guess_month_year_from_filename()` | Extrae mes/año del nombre de archivo |
| `insertar_ventas_from_dataframe(df, filename)` | Importa ventas reales desde Excel |
| `query_ventas(sql, params)` | Consulta SQL → DataFrame Pandas |

---

#### [utils/lector_xml.py](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/lector_xml.py) — Parseo XML DIAN
**Maneja XML estándar UBL + AttachedDocument con CDATA embebido**.

**Funciones clave**:
| Función | Ubicación | Descripción |
|---|---|---|
| `cargar_reglas_conversion()` | [L32-L44](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/lector_xml.py#L32-L44) | Carga `reglas_conversion.json` |
| `procesar_xml(ruta_xml)` | [L46-L202](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/lector_xml.py#L46-L202) | **Core parseo**: detecta AttachedDocument, extrae proveedor, ítems, cantidades, precios. Guarda valores ORIGINALES y convertidos |
| `aplicar_reglas_conversion()` | [L204-L247](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/lector_xml.py#L204-L247) | Multiplica cantidad por factor, divide precio por factor, estandariza columnas minúsculas |

**Proceso de extracción de una factura XML**:
1. Detecta si es `AttachedDocument` → parsea CDATA interno
2. Busca `ID` (N° factura) y `IssueDate` (fecha emisión)
3. Busca nodo proveedor en múltiples paths posibles (AccountingSupplierParty, etc.)
4. Extrae RegistrationName + CompanyID (NIT)
5. Itera `InvoiceLine` → descripcion + InvoicedQuantity + PriceAmount
6. Aplica `normalizar_producto()` a cada descripción
7. Retorna dict estructurado con items, valores originales y convertidos

**Columnas estandarizadas** (para que el optimizador las entienda):
- `nit_proveedor`, `proveedor`, `fecha`, `n_factura`, `tipo`
- `cantidad_convertida`, `cantidad`, `valor unitario`
- `cantidad_original`, `precio_unitario_original` (auditoría)
- `factor_aplicado`, `tipo_conversion`, `proveedor_especial`

---

#### [utils/normalizador.py](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/normalizador.py) — Diccionario de Productos
**Normaliza nombres de huevos a códigos estándar**.

| Función | Descripción |
|---|---|
| `cargar_diccionario()` | Carga `normalizacion_productos.json` |
| `normalizar_producto(nombre)` | `strip().upper()` → lookup en diccionario |

---

#### [utils/optimizador_stock.py](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/optimizador_stock.py) — Optimización de Inventario
**Toma el Excel consolidado y calcula cuántos huevos vender de cada tipo**.

**Modo actual**: Heurístico directo (vender TODO el stock disponible, con pequeñas variaciones aleatorias ±3%).
- Importa `PuLP` opcionalmente (Programación Lineal) — se deja como fallback estructural
- Seed aleatorio fijo `42` para reproducibilidad

**Pipeline interno**:
1. Lee Excel base → normaliza columnas a lowercase
2. Verifica columnas requeridas: `tipo, cantidad, valor unitario, nit_proveedor`
3. Filtra productos excluidos + NITs excluidos
4. **Consolida** por `(tipo, valor unitario)` → suma cantidades → `huevos_disponibles`
5. **Asigna** `huevos_a_vender = huevos_disponibles` (venta total)
6. Aplica variación aleatoria ±3% → redondea al múltiplo 150
7. Clampa para no sobrepasar `huevos_disponibles`
8. Agrega `id` autoincremental + `_fecha_dt` referencia
9. Exporta `stock_optimizado_YYYYMMDD_HHMMSS.xlsx`

**Columnas de salida** (obligatorias para el generador):
`id, tipo, valor unitario, huevos_disponibles, huevos_a_vender, _fecha_dt`

---

#### [utils/generador_facturas.py](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/generador_facturas.py) — Simulación de Ventas
**Genera facturas de venta simuladas distribuidas por días hábiles**.

**Función principal**: `generar_facturas_desde_optimo(ruta_stock_optimo, num_dias_distribucion, numero_inicio=7000)`

**Algoritmo paso a paso**:
1. **Fragmentación**: `fragmentar_cantidad_en_facturas()` divide el total de huevos de cada producto en porciones:
   - 30% chance fragmento grande (hasta MAX_HUEVOS)
   - 50% chance mediano
   - 20% chance pequeño (MIN_HUEVOS)
   - Todos múltiplos de 150 (salvo remanente final)

2. **Distribución por día**:
   - Selecciona N días hábiles aleatorios del mes
   - Martes (weekday=1) y Viernes (weekday=4) tienen **peso 3×** (días fuertes)
   - Resto días hábiles tienen peso 1×

3. **Construcción de facturas**:
   - Por cada día, mezcla items aleatoriamente
   - Arma facturas de **1 a 3 productos** sin repetir tipo
   - Tope máximo por factura: **3.000.000 COP**
   - Fallback: si un item > 3M, se emite factura individual

4. **Precios**:
   - Precio base desde optimizador
   - Margen aleatorio por huevo: **+3 a +5 COP** (utilidad)
   - Calcula precio por cubeta = 30 × precio_huevo

5. **Nomenclatura factura**: `LSFE {numero_inicio++}`

6. **Salida Excel**:
   - 1 hoja por cada mes (nombre mes inglés → español en nombre?)
   - Hoja `all_facturas` consolidada
   - Columnas: `Fecha, Tipo, Precio base (COP/huevo), Huevos vendidos, Cubetas vendidas, Precio venta (COP/huevo), Precio venta (COP/cubeta), Valor Total (COP), ID_Stock, N factura`

---

### 5.3 Archivos de Configuración JSON

#### [normalizacion_productos.json](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/normalizacion_productos.json) — Diccionario de Equivalencias
Mapea variantes de nombres → **código canónico de tipo de huevo**:

| Código Canónico | Variantes normalizadas |
|---|---|
| `AA` | HUEVO AA, AA, HUEVO A.A, HUEVOS AA, HUEVO ROJO TIPO AA, etc. |
| `AAA` | HUEVO EXTRA, HUEVO E, HUEVO ROJO EXTRA, etc. |
| `YUMBO` | HUEVO JUMBO, HUEVO YUMBO, JUMBO, HUEVO Y, etc. |
| `A` | HUEVO A, HUEVO TIPO A, HUEVO ROJO A, HUEVOS EN GENERAL, etc. |
| `B` | HUEVO TIPO B, HUEVO ROJO B, HUEVO B, etc. |
| `C` | HUEVO ROJO C, HUEVO C, HUEVO TIPO C, etc. |
| `BL` | HUEVO BL, HUEVO BLANCO, HUEV BCO STAN GRUESO, HUEVO B/C BLANCO, etc. |
| `AA BL` | HUEVO AA BLANCO |
| `A BL` | HUEVO A BLANCO |
| `AAA BL` | HUEVO EXTRA BLANCO |

**Ubicación de uso**: [normalizador.py L15-L20](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/normalizador.py#L15-L20)

---

#### [reglas_conversion.json](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/reglas_conversion.json) — Factores por Proveedor
**Algunos proveedores facturan en cubetas (×30) y no en unidades. Aquí se corrige**.

```json
{
  "PARDO DIAZ IVAN": {"factor": 30, "tipo_objetivo": "Huevo"}
}
```

**Lógica aplicada en**: [lector_xml.py L204-L247](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/lector_xml.py#L204-L247)
```python
cantidad_convertida = cantidad_original * factor          # 1 cubeta → 30 huevos
precio_convertido   = precio_unitario_original / factor   # precio cubeta → precio huevo
```

---

### 5.4 Scripts Auxiliares

| Script | Propósito | Uso |
|---|---|---|
| [check_prices.py](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/check_prices.py) | Verifica el último `stock_optimizado_*.xlsx` | `python check_prices.py` |
| [debug_check.py](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/debug_check.py) | Diagnóstico: rutas, carpeta resultados, archivos detectados | `python debug_check.py` |
| [limpiar_db.py](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/limpiar_db.py) | **⚠️ Borra TODOS** los registros de `ventas_reales, clientes, auditoria` + VACUUM | `python limpiar_db.py` |

---

## 🔄 6. Flujo Principal Completo (Pipeline End-to-End)

```
USUARIO
  │
  ▼
┌───────────────────────────┐
│ 1. Subir ZIP a facturas_zip │  ← GUI o manual
└─────────────┬─────────────┘
              │ procesar_archivos_zip() [main.py L103]
              ▼
┌────────────────────────────────────────────────────┐
│ 2. EXTRACCIÓN Y ORGANIZACIÓN                        │
│   • Descomprime ZIP a temp/                         │
│   • extraer_datos_desde_xml() → año, mes, N° fact. │
│   • Mueve XML → facturas_xml/[Año]/[Mes]/N.xml      │
│   • Mueve PDF → facturas_pdf/[Año]/[Mes]/N.pdf      │
│   • Elimina ZIP original                            │
└─────────────┬──────────────────────────────────────┘
              │ rutas_xml[]
              ▼
┌────────────────────────────────────────────────────┐
│ 3. PARSEO XML (lector_xml.procesar_xml)            │
│   • Detecta AttachedDocument / CDATA               │
│   • Extrae: proveedor, NIT, fecha, N° factura      │
│   • Itera InvoiceLine → items[]                    │
│   • normalizar_producto() a cada descripción       │
│   • Guarda valores ORIGINALES + convertidos        │
└─────────────┬──────────────────────────────────────┘
              │ datos_factura{}
              ▼
┌────────────────────────────────────────────────────┐
│ 4. REGLAS CONVERSIÓN (aplicar_reglas_conversion)   │
│   • Lookup proveedor en reglas_conversion.json     │
│   • factor = 30 para PARDO DIAZ IVAN (cubetas)     │
│   • cantidad × factor | precio ÷ factor            │
│   • Estandariza columnas a minúsculas              │
└─────────────┬──────────────────────────────────────┘
              │ resultados[] (lista de filas)
              ▼
┌────────────────────────────────────────────────────┐
│ 5. EXCEL CONSOLIDADO (generar_excel)               │
│   • Filtra EXCLUIR_PRODUCTOS                       │
│   • DataFrame → facturas_consolidadas_*.xlsx       │
└─────────────┬──────────────────────────────────────┘
              │ ruta_excel
              ▼
┌────────────────────────────────────────────────────┐
│ 6. OPTIMIZACIÓN STOCK (optimizar_stock)            │
│   • Agrupa por (tipo, valor unitario)              │
│   • Suma → huevos_disponibles                      │
│   • huevos_a_vender = disponible × (0.97 a 1.03)   │
│   • Redondea a múltiplo 150, clampa                │
│   • stock_optimizado_*.xlsx                        │
└─────────────┬──────────────────────────────────────┘
              │ ruta_optimo
              ▼
┌────────────────────────────────────────────────────┐
│ 7. GENERAR FACTURAS SIMULADAS                      │
│   • Por producto, fragmenta_huevos() en lotes      │
│   • Distribuye por día hábil (mar/vie ×3 peso)     │
│   • Añade margen +3 a +5 COP/huevo                 │
│   • Arma facturas (1-3 productos, <3M COP)         │
│   • Numeración LSFE 7000++                         │
│   • facturas_generadas_*.xlsx (hojas por mes + all)│
└────────────────────────────────────────────────────┘
              │
              ▼ (opcional, manual por usuario)
┌────────────────────────────────────────────────────┐
│ 8. IMPORTAR VENTAS REALES A BD                     │
│   • GUI → Ventas Reales → Subir Excel              │
│   • insertar_ventas_from_dataframe() → ventas_reales│
│   • Clientes únicos → tabla clientes               │
│   • Log → auditoria                                │
└────────────────────────────────────────────────────┘
```

---

## 💡 7. Guía Para Implementar una Nueva Función

### Paso 1: Identifica el nivel de la nueva funcionalidad

| **Nivel de Cambio** | **Dónde tocar** | **Ejemplos** |
|---|---|---|
| 🟢 **Configuración** | `utils/config.py` + JSONs | Cambiar límites, agregar exclusiones, factor nuevo proveedor |
| 🟡 **Utilidad/Módulo** | Nuevo archivo en `utils/` + import en `main.py`/`gui_app.py` | Nuevo reporte, integración API, nuevo exportador |
| 🟠 **Pipeline** | `main.py` (añadir paso) + `gui_app.py` (botón/pestaña) | Nuevo paso entre optimización y facturación |
| 🔴 **Interfaz** | `gui_app.py` (nueva sección `elif opcion == ...`) | Dashboard nuevo, página de configuración |
| 🔵 **Persistencia** | `utils/database.py` (tabla nueva) + import | Nueva tabla SQL, queries específicos |

---

### Paso 2: Convenciones del proyecto (patrones a seguir)

#### 🎨 Nombres y estilo:
- **Módulos**: `snake_case.py` (ej: `nuevo_exportador.py`)
- **Funciones**: `snake_case()` (verbos: `generar_`, `procesar_`, `optimizar_`)
- **Constantes globales**: `UPPER_SNAKE_CASE` en `config.py`
- **Columnas DataFrame**: en **minúsculas** internamente (ver `optimizador_stock.py` L49)
- **Columnas salida Excel**: formato amigable ej: `Valor Total (COP)`

#### 🔗 Patrón de "contrato de datos" (Excel columnas):
Siempre que un módulo escribe Excel y otro lo lee, **se valida el esquema**. Ejemplo en [optimizador_stock.py L52-L55](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/optimizador_stock.py#L52-L55):
```python
columnas_requeridas = {"tipo", "cantidad", "valor unitario", "nit_proveedor"}
if not columnas_requeridas.issubset(df.columns):
    print(f"[ERROR] Columnas faltantes: {columnas_requeridas - set(df.columns)}")
```

#### 📝 Formato de rutas:
- Usa `os.path.join()` + `os.getcwd()` NUNCA rutas hardcodeadas con `\`
- Directorios: `os.makedirs(ruta, exist_ok=True)` antes de guardar

#### 🎲 Aleatoriedad reproducible:
- Siempre establece `np.random.seed(42)` o semilla fija antes de operar con aleatorios (ver [optimizador_stock.py L87](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/optimizador_stock.py#L87))
- Módulo `random` → semilla global o por ámbito

---

### Paso 3: Ejemplos concretos de implementación

#### CASO A) Agregar nueva regla de conversión para proveedor XYZ
1. Abre [reglas_conversion.json](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/reglas_conversion.json)
2. Agrega entrada:
```json
{
  "PARDO DIAZ IVAN": {"factor": 30, "tipo_objetivo": "Huevo"},
  "NUEVO PROVEEDOR S.A.S": {"factor": 15, "tipo_objetivo": "Media cubeta"}
}
```
3. Listo. El sistema lo detecta automáticamente via `cargar_reglas_conversion()`

---

#### CASO B) Agregar nuevo tipo de huevo "DUO" (AA+AAA mezclado)
1. Agrega entradas en [normalizacion_productos.json](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/normalizacion_productos.json):
```json
"HUEVO DUO": "DUO",
"MEZCLA AA AAA": "DUO",
"HUEVO ESPECIAL": "DUO"
```
2. (Opcional) Si quieres excluirlo temporalmente → agregalo a `EXCLUIR_PRODUCTOS` en [config.py L13-L17](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/config.py#L13-L17)

---

#### CASO C) Agregar nueva pestaña en Streamlit (ej: "Configuración")
1. En [gui_app.py L228-L239](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/gui_app.py#L228-L239) agrega la opción:
```python
opcion_principal = st.sidebar.radio(
    "Ir a:",
    [
        "🏠 Inicio / Dashboard", 
        "⚙️ Pasos Individuales",
        "🚀 Proceso Completo (ZIP)",
        "💾 Gestión de Resultados",
        "📈 4. Ventas Reales (BD)",
        "🔍 5. Análisis por Producto",
        "🛠️ 6. Configuración"    # ← NUEVA OPCIÓN
    ]
)
```

2. Al final del archivo (antes del cierre), agrega el bloque `elif`:
```python
elif opcion == "🛠️ 6. Configuración":
    st.title("🛠️ Configuración del Sistema")
    # Aquí tu lógica: sliders para MIN_HUEVOS, editor JSON, etc.
    st.slider("Mínimo huevos por factura", 150, 600, MIN_HUEVOS, 150)
```

3. Guarda y recarga Streamlit.

---

#### CASO D) Nuevo módulo: Exportador facturas a CSV por cliente
1. Crea `utils/exportador_csv.py`:
```python
import os
import pandas as pd
from utils.config import CARPETA_RESULTADOS

def exportar_por_cliente(ruta_facturas_generadas):
    """Toma facturas generadas y agrupa CSV por cliente (o tipo)."""
    if not os.path.exists(ruta_facturas_generadas):
        return None
    
    df = pd.read_excel(ruta_facturas_generadas, sheet_name="all_facturas")
    
    for tipo, grupo in df.groupby("Tipo"):
        ruta_csv = os.path.join(CARPETA_RESULTADOS, f"cliente_{tipo}.csv")
        grupo.to_csv(ruta_csv, index=False, encoding="utf-8-sig")
    
    return True
```

2. **Regístralo en main.py**: Agrega import y llamada opcional
3. **Agrega botón en GUI**: En "Optimización y Facturación" → botón secundario que llame tu función

---

#### CASO E) Nueva tabla en SQLite: `productos_catalogo`
1. En [database.py L13-L48](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/utils/database.py#L13-L48) agrega DDL:
```python
sql_catalogo = """
CREATE TABLE IF NOT EXISTS productos_catalogo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE,
    descripcion TEXT,
    costo_promedio REAL,
    stock_seguridad INTEGER
);
"""
cur.executescript(sql_ventas + sql_clientes + sql_aud + sql_catalogo)
```

2. Agrega funciones helpers: `insertar_producto()`, `obtener_catalogo()`
3. (Opcional) Crea página GUI para gestionar catálogo

---

## ▶️ 8. Cómo Ejecutar el Proyecto

### Entorno:
```bash
# 1. Crear entorno (opcional pero recomendado)
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# 2. Instalar dependencias
pip install -r requirements.txt
```

### Modo CLI (sin interfaz):
```bash
# Dejar ZIPs en ./facturas_zip/
python main.py
```

### Modo Interfaz Web (Streamlit):
```bash
python -m streamlit run gui_app.py
# o según README.md (acortado)
```
→ Abre el navegador en `http://localhost:8501`

---

## ✅ 9. Checklist de Calidad para Nuevas Funciones

Antes de dar por lista una nueva implementación, valida:

- [ ] **Constantes** están en `config.py` (no hardcodeadas)
- [ ] **Rutas** usan `os.path.join()` y `exist_ok=True`
- [ ] **Archivos** tienen timestamp `YYYYMMDD_HHMMSS` en el nombre
- [ ] **Validación esquema** columnas requeridas al leer Excel
- [ ] **Fallback** si la librería opcional no está (ej: PuLP → heurístico, Plotly → Altair)
- [ ] **Logs** en consola con prefijo: `[OK]`, `[ERROR]`, `[AVISO]`, `[BUSCANDO]`, `[OPTIMIZANDO]`
- [ ] **GUI nueva sección** agregada al menú sidebar + bloque `elif opcion ==`
- [ ] **Semilla** `np.random.seed(42)` si hay aleatoriedad
- [ ] **Import seguro** try/except en GUI para módulos críticos (ver [gui_app.py L29-L46](file:///c:/Users/Sebastian%20Cortes/Desktop/Proyectos/automatizador_facturas/gui_app.py#L29-L46))

---

## 📞 10. Resumen de Puntos de Extensión Clave

| Quiero modificar... | Archivo clave | Función / Línea |
|---|---|---|
| 🆕 Nombres de productos | `normalizacion_productos.json` | Diccionario completo |
| 📏 Factores por proveedor | `reglas_conversion.json` | Dict `{proveedor: {factor, tipo}}` |
| 🚫 Qué productos/NITs filtrar | `utils/config.py` | `EXCLUIR_NITS`, `EXCLUIR_PRODUCTOS` |
| 📦 Límites por factura | `utils/config.py` | `MIN/MAX_HUEVOS`, `MULTIPLE_HUEVOS` |
| 📊 Nombres columnas Excel | Cada generador `to_excel()` | `df.columns`, `df.rename()` |
| 🧠 Lógica de optimización | `utils/optimizador_stock.py` | `optimizar_stock()` L36 |
| 🎲 Distribución días / margenes | `utils/generador_facturas.py` | `generar_facturas_desde_optimo()` L75 |
| 🖼️ Nueva página web | `gui_app.py` | Sidebar opción + bloque `elif opcion ==` |
| 🗃️ Nueva tabla / query SQL | `utils/database.py` | `inicializar_db()` + nueva función |
| ➕ Nuevo paso en pipeline CLI | `main.py` | Función `main()` L208-L246 |
| 🆕 Nuevo paso en GUI | `gui_app.py` | Proceso Completo / Pasos individuales |

---

**Fin de la documentación.**
