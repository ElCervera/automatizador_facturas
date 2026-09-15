@echo off
TITLE Crear Acceso Directo en el Escritorio
COLOR 0B

cd /d "%~dp0"

set "TARGET=%~dp0Iniciar_Automatizador.bat"
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT=%DESKTOP%\Automatizador de Facturas.lnk"

echo =======================================================
echo    CREANDO ACCESO DIRECTO EN EL ESCRITORIO DE WINDOWS
echo =======================================================
echo.
echo Destino: "%TARGET%"
echo Ubicacion: "%SHORTCUT%"
echo.

powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT%'); $s.TargetPath='%TARGET%'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=1; $s.Description='Automatizador de Facturas y Siigo POS'; $s.Save()"

if exist "%SHORTCUT%" (
    echo [EXITO] Acceso directo creado exitosamente en tu Escritorio!
) else (
    echo [ERROR] No se pudo crear el acceso directo automatizado.
)

echo.
echo Presiona cualquier tecla para salir...
pause > nul
