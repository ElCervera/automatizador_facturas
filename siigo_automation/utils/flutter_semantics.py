import time

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait


def ensure_semantics_enabled(driver: WebDriver, timeout: int, logger) -> None:
    """
    Si la app es Flutter Web, puede renderizar casi todo en canvas.
    Al activar 'Enable accessibility' se generan nodos con aria-label (semantics)
    que Selenium puede encontrar y clickear.
    """
    try:
        placeholder = driver.find_elements(
            By.CSS_SELECTOR, "flt-semantics-placeholder[aria-label='Enable accessibility']"
        )
        if not placeholder:
            return
        if not placeholder[0].is_displayed():
            return
        logger.info("Activando Flutter semantics (Enable accessibility)")
        _safe_click(driver, placeholder[0])
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "flt-semantics")) > 0
        )
    except Exception as exc:
        logger.warning("No se pudo activar Flutter semantics: %s", exc)


def find_by_aria_label_contains(driver: WebDriver, needle: str):
    needle = (needle or "").strip().lower()
    if not needle:
        return None

    xpath = (
        "//*[@aria-label and contains("
        "translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
        f"'{needle}')]"
    )
    for element in driver.find_elements(By.XPATH, xpath):
        return element
    return None


def focus_flutter_text_field(driver: WebDriver, label_contains: str, timeout: int, logger):
    """
    En Flutter Web, al hacer click sobre el nodo semantico del TextField,
    aparece un input/textarea dentro de flt-text-editing-host. Retornamos
    ese elemento para poder escribir.
    """
    ensure_semantics_enabled(driver, timeout=timeout, logger=logger)

    target = find_by_aria_label_contains(driver, label_contains)
    if target is None:
        return None

    _safe_click(driver, target)
    end_time = time.time() + timeout
    while time.time() < end_time:
        for element in driver.find_elements(
            By.CSS_SELECTOR, "flt-text-editing-host input, flt-text-editing-host textarea"
        ):
            try:
                if element.is_displayed() and element.is_enabled():
                    return element
            except Exception:
                continue
        time.sleep(0.1)
    return None


def _safe_click(driver: WebDriver, element) -> None:
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    except Exception:
        pass
    try:
        element.click()
        return
    except Exception:
        pass
    try:
        driver.execute_script("arguments[0].click();", element)
    except Exception:
        return
