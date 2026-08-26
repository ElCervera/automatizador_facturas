import time

# pyrefly: ignore [missing-import]
from selenium.webdriver.common.action_chains import ActionChains
# pyrefly: ignore [missing-import]
from selenium.webdriver.common.by import By
# pyrefly: ignore [missing-import]
from selenium.webdriver.common.keys import Keys
# pyrefly: ignore [missing-import]
from selenium.webdriver.remote.webdriver import WebDriver
# pyrefly: ignore [missing-import]
from selenium.webdriver.support.ui import WebDriverWait

from siigo_automation.config.settings import POST_NAVIGATION_WAIT_SECONDS, POST_SEND_WAIT_SECONDS, SIIGO_URL
from siigo_automation.utils.flutter_semantics import ensure_semantics_enabled
from siigo_automation.utils.semantics_inspector import (
    dump_semantics_snapshot,
    element_summary,
    find_semantics_elements,
)




def procesar_factura_robusta(
    driver: WebDriver,
    factura,
    timeout,
    logger,
    dry_run=False,
    inspect_only=False,
):
    """
    Flujo experimental sin coordenadas: solo Selenium + Flutter semantics.
    """
    numero_factura = factura["numero_factura"]
    logger.info("Modo robusto | Procesando factura %s", numero_factura)

    ensure_semantics_enabled(driver, timeout=timeout, logger=logger)
    dump_semantics_snapshot(driver, f"robusto_inicio_{numero_factura}", logger)

    if inspect_only:
        logger.info("Modo inspeccion: no se ejecutan acciones sobre la factura.")
        return

    _ensure_sales_screen(driver, timeout, logger)

    total_calculado = 0
    for item_index, item in enumerate(factura["items"]):
        producto = item["producto"]
        cantidad = item["cantidad"]
        precio_unitario = item["precio_unitario"]

        logger.info(
            "Robusto | Factura %s | Item %s | Producto=%s | Cantidad=%s | Precio=%s",
            numero_factura,
            item_index + 1,
            producto,
            cantidad,
            precio_unitario,
        )

        _click_product_by_semantics(driver, producto, timeout, logger)
        _open_item_editor_by_semantics(driver, producto, item_index, timeout, logger)
        _edit_current_item_by_semantics(driver, cantidad, precio_unitario, timeout, logger)
        total_calculado += cantidad * precio_unitario

    logger.info("Robusto | Total calculado: %s", total_calculado)

    if dry_run:
        logger.warning(
            "DRY RUN robusto: factura %s validada hasta antes del cobro.",
            numero_factura,
        )
        dump_semantics_snapshot(driver, f"robusto_dry_run_{numero_factura}", logger)
        recuperar_pantalla_ventas_limpia_robusta(driver, timeout, logger)
        return

    _procesar_cobro_robusto(driver, numero_factura, total_calculado, timeout, logger)


def _ensure_sales_screen(driver, timeout, logger):
    ensure_semantics_enabled(driver, timeout=timeout, logger=logger)
    if _click_first_semantics(driver, ["Ventas e ingresos"], logger, optional=True):
        time.sleep(1.5)
    _clear_pre_invoice_if_present(driver, logger)
    _click_first_semantics(driver, ["Nueva Factura"], logger, optional=True)
    time.sleep(1.5)
    _clear_pre_invoice_if_present(driver, logger)


def _click_product_by_semantics(driver, product_name, timeout, logger):
    candidates = _product_candidates(product_name)
    element = _find_first_clickable_semantics(driver, candidates)
    if element is None:
        dump_semantics_snapshot(driver, f"robusto_producto_no_encontrado_{product_name}", logger)
        raise RuntimeError(f"Robusto no encontro producto por semantics: {product_name}")

    logger.info("Click producto por semantics: %s", element_summary(element))
    _safe_click(driver, element)
    time.sleep(1.5)


def _open_item_editor_by_semantics(driver, product_name, item_index, timeout, logger):
    ensure_semantics_enabled(driver, timeout=timeout, logger=logger)

    # Wait dynamically for the item editor buttons to appear in the cart
    unique = []
    end_time = time.time() + 5
    while time.time() < end_time:
        unique = _find_cart_item_editor_buttons(driver, product_name)
        if len(unique) >= item_index + 1:
            break
        time.sleep(0.2)

    if not unique:
        dump_semantics_snapshot(driver, f"robusto_editor_no_encontrado_{item_index + 1}", logger)
        raise RuntimeError(f"Robusto no encontro editor para item {item_index + 1}")

    element = unique[min(item_index, len(unique) - 1)]
    logger.info("Click boton editor carrito por semantics: %s", element_summary(element))
    _safe_click(driver, element)

    if not _wait_for_text(driver, ["Edición de item", "EdiciÃ³n de item"], timeout):
        dump_semantics_snapshot(driver, f"robusto_editor_no_abierto_{item_index + 1}", logger)
        raise RuntimeError(f"Robusto no pudo abrir editor para item {item_index + 1}")

    dump_semantics_snapshot(driver, f"robusto_editor_abierto_{item_index + 1}", logger)


def recuperar_pantalla_ventas_limpia_robusta(driver, timeout, logger):
    """
    Recuperacion del modo robusto sin pyautogui ni coordenadas de click.
    """
    logger.info("Robusto | Recuperando pantalla principal sin coordenadas")
    _press_escape_with_selenium(driver)

    try:
        driver.get(SIIGO_URL)
        _wait_for_page_ready(driver, timeout)
    except Exception as exc:
        logger.warning("Robusto | No se pudo navegar a Siigo POS: %s", exc)

    time.sleep(max(POST_NAVIGATION_WAIT_SECONDS, 2))
    ensure_semantics_enabled(driver, timeout=timeout, logger=logger)
    _click_first_semantics(driver, ["Ventas e ingresos"], logger, optional=True)
    time.sleep(1.5)
    _clear_pre_invoice_if_present(driver, logger)

    logger.info("Robusto | Refrescando para confirmar pantalla limpia")
    driver.refresh()
    _wait_for_page_ready(driver, timeout)
    time.sleep(max(POST_NAVIGATION_WAIT_SECONDS, 2))
    ensure_semantics_enabled(driver, timeout=timeout, logger=logger)
    _click_first_semantics(driver, ["Ventas e ingresos"], logger, optional=True)
    time.sleep(1)
    _clear_pre_invoice_if_present(driver, logger)

    logger.info("Robusto | Pantalla recuperada")


def _edit_current_item_by_semantics(driver, quantity, unit_price, timeout, logger):
    quantity_field = _focus_text_field_by_labels(driver, ["Cantidad"], timeout, logger)
    if quantity_field is None:
        dump_semantics_snapshot(driver, "robusto_cantidad_no_encontrado", logger)
        raise RuntimeError("Robusto no encontro campo Cantidad por semantics.")
    _replace_input_value(quantity_field, str(quantity))

    price_field = _focus_text_field_by_labels(
        driver,
        ["Precio unitario", "Precio unitario*", "Precio"],
        timeout,
        logger,
    )
    if price_field is None:
        dump_semantics_snapshot(driver, "robusto_precio_no_encontrado", logger)
        raise RuntimeError("Robusto no encontro campo Precio por semantics.")
    _replace_input_value(price_field, str(unit_price))

    if not _click_first_semantics(driver, ["Guardar"], logger):
        dump_semantics_snapshot(driver, "robusto_guardar_no_encontrado", logger)
        raise RuntimeError("Robusto no encontro boton Guardar.")

    time.sleep(2)


def _focus_text_field_by_labels(driver, labels, timeout, logger):
    for label in labels:
        native_field = _find_native_input_by_label(driver, label)
        if native_field is not None:
            try:
                native_field.click()
                field = _wait_for_text_editing_host(driver, 2)
                logger.info("Campo nativo enfocado por aria-label: %s", label)
                return field or native_field
            except Exception:
                pass

        for element in find_semantics_elements(driver, label):
            try:
                _safe_click(driver, element)
                field = _wait_for_text_editing_host(driver, timeout)
                if field is not None:
                    logger.info("Campo enfocado por semantics: %s", element_summary(element))
                    return field
            except Exception:
                continue
    return None


def _find_native_input_by_label(driver, label):
    normalized = label.lower()
    for field in driver.find_elements(By.CSS_SELECTOR, "input[aria-label], textarea[aria-label]"):
        try:
            aria = (field.get_attribute("aria-label") or "").lower()
            if normalized in aria:
                return field
        except Exception:
            continue
    return None


def _clear_pre_invoice_if_present(driver, logger):
    clear_group = None
    for label in ["Clear pre-invoice button", "Limpiar", "Borrar"]:
        matches = find_semantics_elements(driver, label)
        if matches:
            clear_group = matches[0]
            break

    if clear_group is None:
        return False

    rect = _rect(clear_group)
    if rect.get("x", 0) < 1450:
        return False

    logger.info("Limpiando pre-cuenta por semantics: %s", element_summary(clear_group))
    _safe_click(driver, clear_group)
    time.sleep(1)
    _confirm_clear_if_present(driver, logger)
    time.sleep(1)
    return True


def _confirm_clear_if_present(driver, logger):
    for label in ["Aceptar", "Confirmar", "Si", "Sí", "Eliminar", "Limpiar"]:
        element = _find_first_clickable_semantics(driver, [label])
        if element is None:
            continue
        logger.info("Confirmando limpieza por semantics: %s", element_summary(element))
        _safe_click(driver, element)
        return True
    return False


def _wait_for_text_editing_host(driver, timeout):
    end_time = time.time() + timeout
    while time.time() < end_time:
        fields = driver.find_elements(
            By.CSS_SELECTOR,
            "flt-text-editing-host input, flt-text-editing-host textarea",
        )
        for field in fields:
            try:
                if field.is_displayed() and field.is_enabled():
                    return field
            except Exception:
                continue
        time.sleep(0.1)
    return None


def _replace_input_value(element, value):
    try:
        element.click()
        time.sleep(0.2)
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.DELETE)
        element.send_keys(value)
        time.sleep(0.2)
        element.send_keys(Keys.TAB)
        return
    except Exception:
        pass

    driver = element.parent
    driver.execute_script(
        """
        const element = arguments[0];
        const value = arguments[1];
        element.focus();
        element.value = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        element,
        value,
    )


def _click_first_semantics(driver, labels, logger, optional=False):
    element = _find_first_clickable_semantics(driver, labels)
    if element is None:
        if optional:
            return False
        return False

    logger.info("Click semantics: %s", element_summary(element))
    _safe_click(driver, element)
    return True


def _find_first_clickable_semantics(driver, labels):
    for label in labels:
        for element in find_semantics_elements(driver, label):
            if _is_tappable(element) and not _is_giant_container(element):
                return element
    return None


def _find_cart_item_editor_buttons(driver, product_name):
    product_key = _normalize_product_name(product_name)
    product_buttons = []

    for element in find_semantics_elements(driver, product_name):
        if not _is_tappable(element):
            continue
        if _is_giant_container(element):
            continue
        rect = _rect(element)
        text = _normalize_product_name(
            f"{element.get_attribute('aria-label') or ''} {element.text or ''}"
        )
        if product_key not in text:
            continue
        if rect.get("x", 0) < 1450:
            continue
        if rect.get("width", 0) > 330:
            continue
        product_buttons.append(element)

    product_buttons = _unique_elements(
        sorted(product_buttons, key=lambda element: _rect(element).get("y", 0))
    )

    editor_buttons = []
    all_buttons = driver.find_elements(By.CSS_SELECTOR, "flt-semantics")
    for product_button in product_buttons:
        product_rect = _rect(product_button)
        row_buttons = []
        for candidate in all_buttons:
            if not _is_tappable(candidate):
                continue
            if _is_giant_container(candidate):
                continue
            rect = _rect(candidate)
            if rect.get("x", 0) <= product_rect.get("x", 0) + product_rect.get("width", 0) - 5:
                continue
            if abs(_center_y(rect) - _center_y(product_rect)) > 26:
                continue
            if rect.get("width", 0) > 70 or rect.get("height", 0) > 70:
                continue
            row_buttons.append(candidate)

        if row_buttons:
            editor_buttons.append(sorted(row_buttons, key=lambda element: _rect(element).get("x", 0))[0])

    return _unique_elements(editor_buttons)


def _wait_for_text(driver, labels, timeout):
    end_time = time.time() + timeout
    while time.time() < end_time:
        for label in labels:
            if find_semantics_elements(driver, label):
                return True
        time.sleep(0.2)
    return False


def _safe_click(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    except Exception:
        pass
    try:
        ActionChains(driver).move_to_element(element).click().perform()
        return
    except Exception:
        pass
    try:
        element.click()
        return
    except Exception:
        pass
    driver.execute_script("arguments[0].click();", element)


def _press_escape_with_selenium(driver):
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        for _ in range(3):
            body.send_keys(Keys.ESCAPE)
            time.sleep(0.3)
    except Exception:
        pass


def _wait_for_page_ready(driver, timeout):
    try:
        WebDriverWait(driver, timeout).until(
            lambda current_driver: current_driver.execute_script(
                "return document.readyState"
            ) in ("interactive", "complete")
        )
    except Exception:
        time.sleep(2)


def _is_tappable(element) -> bool:
    try:
        return (
            element.get_attribute("flt-tappable") is not None
            or element.get_attribute("role") in ("button", "group")
        )
    except Exception:
        return False


def _is_giant_container(element) -> bool:
    rect = _rect(element)
    return rect.get("width", 0) > 900 or rect.get("height", 0) > 500


def _rect(element):
    try:
        return element.rect
    except Exception:
        return {}


def _center_y(rect):
    return rect.get("y", 0) + rect.get("height", 0) / 2


def _normalize_product_name(value):
    return " ".join(str(value or "").upper().split())


def _unique_elements(elements):
    seen = set()
    unique = []
    for element in elements:
        element_id = element.id
        if element_id in seen:
            continue
        seen.add(element_id)
        unique.append(element)
    return unique


def _product_candidates(product_name):
    name = str(product_name).strip()
    return [
        name,
        name.upper(),
        name.lower(),
        name.replace("HUEVO ", ""),
    ]


def _procesar_cobro_robusto(driver, numero_factura, total_calculado, timeout, logger):
    logger.info("Robusto | Factura %s | Iniciando fase de cobro por %s", numero_factura, total_calculado)

    if not _click_first_semantics(driver, ["cobrar"], logger):
        dump_semantics_snapshot(driver, f"robusto_error_cobrar_1_{numero_factura}", logger)
        raise RuntimeError(f"Robusto no encontro el boton 'Cobrar' principal para la factura {numero_factura}.")

    logger.info("Robusto | Esperando modal de pago...")
    if not _wait_for_text(driver, ["contado"], timeout):
        dump_semantics_snapshot(driver, f"robusto_error_modal_pago_{numero_factura}", logger)
        raise RuntimeError(f"Robusto no encontro el metodo de pago 'Contado' para la factura {numero_factura}.")

    time.sleep(1)

    # Click en "Contado" para asegurarnos que esta seleccionado
    if not _click_first_semantics(driver, ["contado"], logger):
        dump_semantics_snapshot(driver, f"robusto_error_contado_{numero_factura}", logger)
        raise RuntimeError("Robusto no pudo hacer clic en 'Contado'.")

    time.sleep(1)

    # Asignar el valor total del pago escribiendo en el campo "Valor" de la pestaña Contado
    logger.info("Robusto | Intentando asignar %s al campo Valor...", total_calculado)
    campo_valor = _focus_text_field_by_labels(driver, ["Valor"], timeout, logger)
    if campo_valor:
        # Enviamos el valor como entero y presionamos Enter para que lo registre Siigo
        _replace_input_value(campo_valor, str(int(total_calculado)) + Keys.ENTER)
    else:
        dump_semantics_snapshot(driver, f"robusto_error_asignar_valor_{numero_factura}", logger)
        raise RuntimeError("Robusto no pudo asignar el valor de pago (campo Valor no encontrado).")

    time.sleep(1)

    if not _click_first_semantics(driver, ["guardar y enviar a la dian", "cobrar", "facturar", "terminar"], logger):
        dump_semantics_snapshot(driver, f"robusto_error_cobrar_2_{numero_factura}", logger)
        raise RuntimeError("Robusto no encontro el boton final de cobro/facturacion.")

    logger.info("Robusto | Factura %s enviada. Esperando procesamiento...", numero_factura)

    # Esperar dinámicamente a que el modal de pago se cierre (hasta 35 segundos)
    max_wait = 35
    end_time = time.time() + max_wait
    modal_closed = False
    while time.time() < end_time:
        # Check if we transitioned to the print settings or export screen (success indicator)
        if find_semantics_elements(driver, "Configuración de impresión") or find_semantics_elements(driver, "Exportar para impresión"):
            logger.info("Robusto | Se detecto pantalla de impresion/exito. Factura completada.")
            modal_closed = True
            break
        if not find_semantics_elements(driver, "guardar y enviar a la dian"):
            modal_closed = True
            break
        time.sleep(0.5)

    if not modal_closed:
        dump_semantics_snapshot(driver, f"robusto_error_validacion_pago_{numero_factura}", logger)
        raise RuntimeError(
            f"El modal de pago sigue abierto tras {max_wait}s de confirmar la factura {numero_factura}. "
            "Peligro de duplicación: NO SE DEBE REINTENTAR esta factura automáticamente."
        )

    dump_semantics_snapshot(driver, f"robusto_exito_{numero_factura}", logger)

    logger.info("Robusto | Recuperando pantalla limpia...")
    try:
        recuperar_pantalla_ventas_limpia_robusta(driver, timeout, logger)
    except Exception as exc:
        logger.error("Robusto | Error recuperando pantalla limpia pos-exito: %s", exc)
        raise RuntimeError(
            f"Error recuperando pantalla limpia tras confirmacion exitosa: {exc}. "
            "Peligro de duplicación: NO SE DEBE REINTENTAR esta factura automáticamente."
        ) from exc
