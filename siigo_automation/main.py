import argparse
import sys
import time
from pathlib import Path

from siigo_automation.config.settings import (
    DRY_RUN,
    EXCEL_PATH,
    HEADLESS,
    PATCHED_MAX_ATTEMPTS_PER_INVOICE,
    PATCHED_RETRY_DELAY_SECONDS,
    SIIGO_URL,
    WAIT_FOR_MANUAL_SETUP,
    WAIT_TIMEOUT,
)
from siigo_automation.services.browser import create_driver
from siigo_automation.services.excel_reader import exportar_facturas_exitosas, read_facturacion
from siigo_automation.services.siigo_facturacion_robusta import (
    procesar_factura_robusta,
    recuperar_pantalla_ventas_limpia_robusta,
)
from siigo_automation.services.siigo_login import ensure_session_active
from siigo_automation.utils.debug_artifacts import dump_debug_artifacts, report_fatal_error
from siigo_automation.utils.logger import get_logger



def run() -> int:
    args = _parse_args()
    dry_run = args.dry_run or DRY_RUN
    return run_robusto(
        dry_run=dry_run,
        limit=args.limit,
        inspect_only=args.inspect_semantics,
    )


def run_robusto(
    dry_run=False,
    limit=None,
    inspect_only=False,
    excel_path=None,
    browser_type=None,
    wait_for_manual_setup=None,
    progress_callback=None,
    custom_logger=None,
    manual_ready_event=None,
) -> int:
    """
    Ejecuta el flujo de facturación en modo robusto usando Selenium y Flutter semantics.
    Acepta parámetros opcionales para integración fluida con la GUI de Streamlit u otros entornos.
    """
    logger = custom_logger or get_logger("robo_facturador_2.0")
    driver = None
    completed = False
    facturas_exitosas = []

    if wait_for_manual_setup is None:
        wait_for_manual_setup = WAIT_FOR_MANUAL_SETUP

    if not dry_run and not inspect_only:
        logger.warning("Ejecutando modo ROBUSTO en vivo (generará facturas reales).")

    try:
        actual_excel_path = Path(excel_path) if excel_path else Path(EXCEL_PATH)
        facturas = _read_facturas(logger, path=actual_excel_path, limit=limit)
        if not facturas:
            return 0

        driver = create_driver(browser_type=browser_type, headless=HEADLESS)
        _prepare_session(driver, logger, wait_for_manual_setup=wait_for_manual_setup, manual_ready_event=manual_ready_event)

        total = len(facturas)
        for index, factura in enumerate(facturas, start=1):
            if progress_callback:
                progress_callback(index, total, factura["numero_factura"])

            _procesar_factura_con_reintentos(
                driver=driver,
                factura=factura,
                index=index,
                total_facturas=total,
                logger=logger,
                dry_run=dry_run,
                processor=procesar_factura_robusta,
                recovery=recuperar_pantalla_ventas_limpia_robusta,
                inspect_only=inspect_only,
            )
            facturas_exitosas.append(factura)

        completed = True
        logger.info("Proceso completado correctamente.")
        return 0
    except KeyboardInterrupt:
        logger.warning("Proceso interrumpido manualmente. Cerrando navegador.")
        if driver is not None:
            _safe_quit(driver, logger)
            driver = None
        return 130
    except Exception as exc:
        report_fatal_error(exc, "robusto", driver, logger)
        return 1
    finally:
        if facturas_exitosas:
            try:
                ruta = exportar_facturas_exitosas(facturas_exitosas)
                logger.info("Reporte de facturas exitosas guardado en: %s", ruta)
            except Exception as e:
                logger.error("No se pudo exportar el reporte de facturas exitosas: %s", e)

        if driver is not None and completed:
            logger.info("Cerrando navegador")
            _safe_quit(driver, logger)


def _procesar_factura_con_reintentos(
    driver,
    factura,
    index,
    total_facturas,
    logger,
    dry_run=False,
    processor=procesar_factura_robusta,
    recovery=recuperar_pantalla_ventas_limpia_robusta,
    inspect_only=False,
):
    numero_factura = factura["numero_factura"]
    attempt = 1

    while True:
        logger.info(
            "Iniciando factura %s de %s: %s | intento %s",
            index,
            total_facturas,
            numero_factura,
            attempt,
        )

        try:
            processor(
                driver=driver,
                factura=factura,
                timeout=WAIT_TIMEOUT,
                logger=logger,
                dry_run=dry_run,
                inspect_only=inspect_only,
            )
            return
        except Exception as exc:
            dump_debug_artifacts(driver, f"retry_{numero_factura}_{attempt}", logger)
            logger.exception(
                "Fallo procesando factura %s en intento %s: %s",
                numero_factura,
                attempt,
                exc,
            )

            if not _is_retryable_exception(exc):
                raise RuntimeError(
                    f"La factura {numero_factura} falló por una causa no recuperable."
                ) from exc

            if _attempts_exhausted(attempt):
                raise RuntimeError(
                    f"La factura {numero_factura} superó el límite de reintentos."
                ) from exc

            logger.info(
                "Recuperando Siigo antes de reintentar la factura %s", numero_factura
            )
            recovery(driver, WAIT_TIMEOUT, logger)
            time.sleep(PATCHED_RETRY_DELAY_SECONDS)
            attempt += 1


def _read_facturas(logger, path=None, limit=None):
    actual_path = Path(path) if path else Path(EXCEL_PATH)
    logger.info("Leyendo archivo de facturación: %s", actual_path)
    facturas = read_facturacion(actual_path)
    if not facturas:
        logger.info("No se encontraron facturas para procesar.")
        return []

    logger.info("Se encontraron %s facturas para procesar.", len(facturas))
    if limit is not None and limit > 0:
        facturas = facturas[:limit]
        logger.info("Modo prueba limitado a %s facturas.", len(facturas))
    return facturas


def _prepare_session(driver, logger, wait_for_manual_setup=WAIT_FOR_MANUAL_SETUP, manual_ready_event=None):
    if wait_for_manual_setup:
        logger.info("Abriendo Siigo POS para configuración manual")
        driver.get(SIIGO_URL)
        logger.info(
            "Por favor, deja Siigo POS listo en 'Ventas e ingresos' con la sesión iniciada y el turno abierto."
        )
        if manual_ready_event is not None:
            logger.info("Esperando confirmación desde la interfaz gráfica...")
            manual_ready_event.wait()
            logger.info("Confirmación recibida desde la GUI. Continuando...")
        elif sys.stdin and sys.stdin.isatty():
            input("Cuando todo esté listo, presiona Enter para comenzar la facturación...")
        else:
            logger.info("Modo no interactivo detectado; continuando sin esperar Enter.")

        try:
            ensure_session_active(
                driver=driver,
                url=SIIGO_URL,
                timeout=WAIT_TIMEOUT,
                logger=logger,
                navigate=False,
            )
        except Exception as exc:
            logger.warning(
                "No se pudo validar automáticamente la pantalla principal de Siigo POS: %s",
                exc,
            )
            logger.warning(
                "Se continuará con la automatización porque la preparación fue confirmada."
            )
    else:
        ensure_session_active(
            driver=driver,
            url=SIIGO_URL,
            timeout=WAIT_TIMEOUT,
            logger=logger,
        )


def _attempts_exhausted(attempt: int) -> bool:
    if PATCHED_MAX_ATTEMPTS_PER_INVOICE <= 0:
        return False
    return attempt >= PATCHED_MAX_ATTEMPTS_PER_INVOICE


def _is_retryable_exception(exc: Exception) -> bool:
    message = str(exc).lower()
    non_retryable_markers = [
        "no existe el archivo",
        "faltan columnas",
        "peligro de duplicación",
        "no se debe reintentar",
    ]
    return not any(marker in message for marker in non_retryable_markers)


def _safe_quit(driver, logger):
    try:
        driver.quit()
    except BaseException as exc:
        logger.warning("No se pudo cerrar navegador limpiamente: %s", exc)


def _parse_args():
    parser = argparse.ArgumentParser(description="Robo Facturador 2.0 - Siigo POS Automation")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ensayo seguro: no hace click en Cobrar ni Enviar a la DIAN.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Procesa solo las primeras N facturas del Excel.",
    )
    parser.add_argument(
        "--inspect-semantics",
        action="store_true",
        help="Modo robusto: guarda mapa de Flutter semantics sin ejecutar acciones.",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit debe ser mayor que 0.")
    return args


if __name__ == "__main__":
    sys.exit(run())
