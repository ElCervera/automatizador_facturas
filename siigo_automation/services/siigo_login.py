from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from siigo_automation.utils.flutter_semantics import ensure_semantics_enabled


ACTIVE_SESSION_LOCATORS = [
    (By.XPATH, "//span[contains(normalize-space(.), 'Ventas e ingresos')]"),
    (
        By.XPATH,
        "//input[contains(@placeholder, 'Buscar por Producto') or contains(@placeholder, 'Buscar por producto')]",
    ),
    (By.XPATH, "//button[contains(., 'Cobrar')]"),
]

LOGIN_LOCATORS = [
    (By.XPATH, "//input[@type='email' or @name='username']"),
    (By.XPATH, "//input[@type='password']"),
    (By.XPATH, "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'iniciar sesion')]"),
]


def ensure_session_active(
    driver: WebDriver,
    url: str,
    timeout: int,
    logger,
    navigate: bool = True,
) -> None:
    """
    Abre Siigo POS y valida que la sesion siga activa.
    """
    if navigate:
        driver.get(url)

    # Activar Flutter semantics antes de validar elementos visibles.
    ensure_semantics_enabled(driver, timeout=timeout, logger=logger)

    try:
        WebDriverWait(driver, timeout).until(
            lambda current_driver: any(
                _is_visible(current_driver, locator)
                for locator in ACTIVE_SESSION_LOCATORS
            )
        )
    except TimeoutException as exc:
        if any(_is_visible(driver, locator) for locator in LOGIN_LOCATORS):
            raise RuntimeError(
                "La sesion de Siigo POS no esta activa. Abre la sesion manualmente en el perfil de Edge."
            ) from exc

        raise RuntimeError(
            "No fue posible validar la pantalla principal de Siigo POS."
        ) from exc

    logger.info("Sesion activa confirmada en Siigo POS")


def _is_visible(driver: WebDriver, locator: tuple[str, str]) -> bool:
    try:
        return bool(driver.find_elements(*locator))
    except Exception:
        return False
