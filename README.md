# 🧾 Automatizador de Facturas & 🤖 Robo Facturador Siigo POS

Plataforma integral desarrollada en **Python** para el procesamiento, consolidación y optimización de **facturas electrónicas DIAN (Colombia)**, integrada con un bot de automatización web multiplataforma (Windows/Linux) para la emisión automática de facturas en **Siigo POS** mediante **Streamlit**, **Selenium** y **Flutter Semantics**.

---

## 🎯 Visión General

El sistema cubre todo el ciclo de vida del procesamiento y emisión de facturación:

1. **📦 Procesamiento de Facturas DIAN (XML/ZIP)**: Descomprime, lee y extrae datos estructurados de XMLs emitidos por proveedores bajo normatividad DIAN.
2. **🧠 Optimización de Inventario (PuLP)**: Aplica algoritmos de programación lineal para calcular la distribución óptima de stock a vender según margen y existencias.
3. **📊 Simulación de Facturación de Venta**: Genera planillas Excel consolidadas con distribución aleatoria pero controlada de ventas por días hábiles.
4. **💾 Base de Datos e Históricos (SQLite)**: Persiste el histórico de ventas reales, calculando métricas de utilidad, precios promedio y rendimiento por producto.
5. **🤖 Facturación Automática en Siigo POS**: Bot agnóstico del sistema operativo que ingresa las facturas directamente en la plataforma web de Siigo POS, manejando Flutter Semantics, perfiles persistentes para mantener la sesión iniciada, consola de logs en vivo en la GUI y barra de progreso.

---

## ✨ Módulos de la Aplicación

La interfaz gráfica web (**Streamlit**) se divide en 7 secciones principales:

| Módulo | Nombre | Descripción |
|---|---|---|
| 🏠 | **Inicio / Dashboard** | Mapeo de métricas clave en tiempo real, estado de la base de datos, filtros por año/mes y estimación de utilidad. |
| ⚙️ | **1. Procesamiento (ZIP/XML)** | Carga y descompresión masiva de ZIPs de proveedores, extracción de XMLs y conversión de unidades por proveedor. |
| 🧮 | **2. Optimización y Facturación** | Cálculo de stock optimizado e ingeniería de facturas de venta simuladas. |
| 🚀 | **Proceso Completo** | Flujo orquestado de un solo clic desde los ZIPs hasta las planillas de resultados. |
| 💾 | **Gestión de Resultados** | Descarga, consulta y eliminación de reportes Excel generados en `./resultados/`. |
| 📈 | **4. Ventas Reales (BD)** | Importación y consulta de la base de datos de ventas en SQLite con gráficos interactivos. |
| 🔍 | **5. Análisis por Producto** | Métricas desglosadas por tipo de producto (cantidad vendida, valor total, precio promedio). |
| 🤖 | **7. Facturación Siigo POS** | Automatización web en segundo plano con Selenium, selección de navegador (Edge/Firefox), modo ensayo (Dry Run), y logs en vivo. |

---

## 🛠️ Requisitos del Sistema y Tecnologías

### Tecnologías Principales:
- **Python**: 3.10+ (Probado en 3.13 / 3.14)
- **Streamlit**: Interfaz web interactiva
- **Selenium WebDriver & webdriver-manager**: Automatización del navegador
- **Pandas, OpenPyXL, XlsxWriter**: Manipulación y generación de reportes Excel
- **PuLP**: Optimización mediante Programación Lineal
- **Plotly Express / Altair**: Gráficos e indicadores visuales
- **SQLite3**: Persistencia de datos

### Navegadores Soportados:
- **Windows**: Microsoft Edge (`msedgedriver` gestionado automáticamente).
- **Linux (Linux Mint / Ubuntu / Debian)**: Mozilla Firefox (`geckodriver` gestionado automáticamente).

---

## 🚀 Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone https://github.com/ElCervera/automatizador_facturas.git
cd automatizador_facturas
```

### 2. Crear y activar el entorno virtual
- **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **Linux / macOS**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Instalar las dependencias
```bash
pip install -r requirements.txt
```

---

## 🏃 Cómo Ejecutar la Aplicación

### 🌐 Opción A: Interfaz Gráfica Web (Streamlit) — Recomendado

- **Ejecución directa (sin activar entorno)**:
  ```powershell
  .\venv\Scripts\python.exe -m streamlit run gui_app.py
  ```
- **Con el entorno virtual activado**:
  ```bash
  streamlit run gui_app.py
  ```

Una vez ejecutado, abre en tu navegador la dirección indicada (por defecto `http://localhost:8501`).

---

### 💻 Opción B: Consola de Comandos (CLI)

- **Procesamiento de facturas y optimización**:
  ```bash
  python main.py
  ```
- **Ejecutar bot de Siigo POS independiente**:
  ```bash
  # Modo Ensayo (Dry Run: simula sin cobrar ni enviar a la DIAN)
  python siigo_automation/main.py --dry-run --limit 5
  ```

---

## 📂 Estructura del Proyecto

```
automatizador_facturas/
│
├── 📄 gui_app.py                   # Aplicación principal Streamlit (GUI)
├── 📄 main.py                      # Orquestador CLI principal del backend
├── 📄 requirements.txt             # Dependencias de Python
├── 📄 .gitignore                   # Exclusiones de Git (seguridad y temporales)
├── 📄 DOCUMENTACION_PROYECTO.md    # Documentación técnica extendida
├── 📄 normalizacion_productos.json # Mapeo de equivalencias de nombres de productos
├── 📄 reglas_conversion.json       # Reglas de conversión por proveedor
│
├── 📁 utils/                       # Funciones auxiliares del backend
│   ├── config.py                   # Rutas y constantes globales
│   ├── database.py                 # Consultas e inserciones en SQLite
│   ├── generador_facturas.py       # Algoritmo de generación de facturas simuladas
│   ├── lector_xml.py               # Parser de XMLs DIAN
│   ├── normalizador.py             # Normalización de textos
│   └── optimizador_stock.py        # Modelo de optimización PuLP
│
├── 📁 siigo_automation/            # Módulo de automatización para Siigo POS
│   ├── 📄 main.py                  # Orquestador del bot Selenium
│   ├── 📁 config/                  # Ajustes de Siigo y detección de SO
│   │   └── settings.py
│   ├── 📁 services/                # Servicios principales
│   │   ├── browser.py              # Controlador multiplataforma (Edge/Firefox)
│   │   ├── excel_reader.py         # Armonización automática de planillas Excel
│   │   ├── siigo_facturacion_robusta.py # Lógica de llenado de facturas en Siigo
│   │   └── siigo_login.py          # Verificación de sesión activa
│   ├── 📁 utils/                   # Utilidades del bot
│   │   ├── flutter_semantics.py    # Manejo de Flutter Web Semantics (aria-label)
│   │   ├── logger.py               # Captura de logs para la GUI
│   │   ├── debug_artifacts.py      # Captura de pantallas en caso de error
│   │   └── semantics_inspector.py  # Inspección del DOM semántico
│   └── 📁 data/                    # Carpeta para planilla diaria (facturacion.xlsx)
│
├── 📁 facturas_zip/                # Carpeta de entrada para archivos .zip
├── 📁 facturas_xml/                # Carpeta para archivos .xml extraídos
├── 📁 facturas_pdf/                # Carpeta para representaciones gráficas .pdf
└── 📁 resultados/                  # Carpeta de salida para reportes Excel generados
```

---

## ⚙️ Variables de Entorno (Opcional)

Puedes configurar un archivo `.env` en la raíz de `siigo_automation/` para personalizar el comportamiento del bot:

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `BROWSER_TYPE` | Forzar navegador (`edge` o `firefox`) | `auto` (autodetecta según SO) |
| `HEADLESS` | Ejecución en segundo plano sin ventana | `false` |
| `DRY_RUN` | Modo ensayo (no hace clic en Cobrar) | `false` |
| `WAIT_TIMEOUT` | Tiempo máximo de espera en segundos para elementos | `20` |

---

## 🔒 Seguridad y Privacidad

- **Credenciales Seguras**: El sistema no almacena credenciales ni claves en código o repositorios.
- **Sesión Persistente**: Para Siigo POS, el bot reutiliza los perfiles locales de navegador (`.edge_profile` / `.firefox_profile`). Solo inicias sesión manualmente una vez en el navegador y la sesión se conserva localmente.
- **Git Exclusions**: El archivo `.gitignore` previene la subida accidental de archivos de datos reales (`.xlsx`), bases de datos (`*.db`), carpetas de facturas (`facturas_pdf/`, `facturas_xml/`), entornos virtuales (`venv/`) y perfiles de usuario.

---

## 👨‍💻 Autor

Desarrollado por **Sebastián Cortes** ([@ElCervera](https://github.com/ElCervera)) — 2025/2026.