from datetime import datetime
from pathlib import Path
import re

from siigo_automation.config.settings import DEBUG_DIR



def dump_debug_artifacts(driver, label: str, logger) -> dict[str, str]:
    """
    Guarda una captura de pantalla y el HTML actual para depuracion.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = re.sub(r"[^a-zA-Z0-9_-]+", "_", label).strip("_") or "debug"

    screenshot_path = Path(DEBUG_DIR) / f"{timestamp}_{safe_label}.png"
    html_path = Path(DEBUG_DIR) / f"{timestamp}_{safe_label}.html"

    try:
        driver.save_screenshot(str(screenshot_path))
    except Exception as exc:
        logger.warning("No se pudo guardar screenshot de depuracion: %s", exc)

    try:
        html_path.write_text(driver.page_source, encoding="utf-8")
    except Exception as exc:
        logger.warning("No se pudo guardar HTML de depuracion: %s", exc)

    logger.warning("Screenshot de depuracion: %s", screenshot_path)
    logger.warning("HTML de depuracion: %s", html_path)

    return {
        "screenshot": str(screenshot_path),
        "html": str(html_path),
    }


def report_fatal_error(exc: Exception, mode: str, driver, logger) -> None:
    """
    Genera un reporte detallado del error fatal en debug/ultimo_error.txt y
    debug/YYYYMMDD_HHMMSS_error_report.txt, captura capturas/HTML, y
    muestra un resumen legible por consola.
    """
    import traceback
    from config.settings import DEBUG_DIR

    # Encontrar la causa raiz del error
    root_exc = exc
    while root_exc.__cause__ is not None:
        root_exc = root_exc.__cause__

    error_msg = str(root_exc)
    tb_str = "".join(traceback.format_exception(type(root_exc), root_exc, root_exc.__traceback__))

    # Nombre del archivo para reporte legible
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(DEBUG_DIR) / f"{timestamp}_error_report.txt"
    last_report_path = Path(DEBUG_DIR) / "ultimo_error.txt"

    # Formatear el reporte de error
    report_content = []
    report_content.append("=" * 80)
    report_content.append("REPORTE DE ERROR FATAL DE AUTOMATIZACION")
    report_content.append("=" * 80)
    report_content.append(f"Fecha/Hora:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_content.append(f"Modo ejecucion:   {mode}")
    report_content.append(f"Error principal:  {error_msg}")
    report_content.append("=" * 80)

    # Intentar obtener capturas de pantalla/HTML del driver
    screenshot_msg = "No disponible"
    html_msg = "No disponible"
    if driver is not None:
        try:
            artifacts = dump_debug_artifacts(driver, f"fatal_error_{mode}", logger)
            screenshot_msg = artifacts.get("screenshot", "No disponible")
            html_msg = artifacts.get("html", "No disponible")
        except Exception as e:
            logger.warning("No se pudieron guardar artefactos de depuracion durante el reporte: %s", e)

    report_content.append(f"Captura de pantalla (PNG): {screenshot_msg}")
    report_content.append(f"Codigo HTML de la pagina:  {html_msg}")

    # Buscar snapshots semanticos recientes en la carpeta debug
    try:
        semantics_files = sorted(
            Path(DEBUG_DIR).glob("*.semantics.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if semantics_files:
            report_content.append(f"Ultimo snapshot semantico: {semantics_files[0]}")
    except Exception:
        pass

    report_content.append("=" * 80)
    report_content.append("TRACEBACK DETALLADO DEL ERROR:")
    report_content.append("=" * 80)
    report_content.append(tb_str)
    report_content.append("=" * 80)

    report_text = "\n".join(report_content)

    # Guardar reporte detallado
    try:
        report_path.write_text(report_text, encoding="utf-8")
        last_report_path.write_text(report_text, encoding="utf-8")
    except Exception as e:
        logger.error("No se pudo escribir el archivo de reporte de error: %s", e)

    # Imprimir en consola de manera muy visible y clara
    print("\n" + "=" * 80)
    print(" [ERROR FATAL] EL PROGRAMA SE HA DETENIDO DEBIDO A UN ERROR NO RECUPERABLE")
    print("=" * 80)
    print(f" Modo:            {mode}")
    print(f" Error:           {error_msg}")
    print(f" Reporte creado:  {report_path}")
    print(f" Copia del reporte: {last_report_path}")
    if screenshot_msg != "No disponible":
        print(f" Captura de pantalla: {screenshot_msg}")
    print("=" * 80 + "\n")

    # Tambien logear al logger
    logger.error("Error fatal en modo %s: %s", mode, error_msg)
