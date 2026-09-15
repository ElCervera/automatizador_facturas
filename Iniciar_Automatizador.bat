@echo off
TITLE Automatizador de Facturas - Streamlit GUI
COLOR 0A

:: Cambiar al directorio del script
cd /d "%~dp0"

echo ===================================================
echo     INICIANDO AUTOMATIZADOR DE FACTURAS Y SIIGO
echo ===================================================
echo.

:: Verificar existencia del entorno virtual
if exist "venv\Scripts\activate.bat" (
    echo [OK] Entorno virtual detectado. Activando venv...
    call venv\Scripts\activate.bat
) else (
    echo [ADVERTENCIA] No se detecto el directorio 'venv'.
    echo Se intentara ejecutar usando el Python global del sistema.
    echo.
)

echo [INFO] Lanzando interfaz grafica en Streamlit...
echo.
python -m streamlit run gui_app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Hubo un problema al iniciar la aplicacion.
    echo Presiona cualquier tecla para cerrar esta ventana.
    pause > nul
)
