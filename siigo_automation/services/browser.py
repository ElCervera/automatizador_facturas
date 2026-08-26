import os
import shutil
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from siigo_automation.config import settings
from siigo_automation.utils.logger import get_logger



def create_driver(browser_type: str | None = None, headless: bool = settings.HEADLESS) -> webdriver.Remote:
    """
    Crea un driver de navegador agnóstico del SO (Edge o Firefox).
    Si browser_type es None o 'auto', autodetecta según el sistema operativo:
    - Windows -> Edge
    - Linux Mint / Linux -> Firefox
    """
    logger = get_logger("browser_service")
    
    if not browser_type or browser_type.lower() in ("auto", "auto-detectar", "autodetectar"):
        browser_type = getattr(settings, "BROWSER_TYPE", None)
        if not browser_type or browser_type.lower() in ("auto", "auto-detectar", "autodetectar"):
            browser_type = "edge" if sys.platform.startswith("win") else "firefox"

    browser_type = browser_type.lower()
    logger.info("Navegador seleccionado: %s (SO: %s)", browser_type, sys.platform)

    if browser_type == "firefox":
        return create_firefox_driver(headless=headless)
    else:
        return create_edge_driver(headless=headless)


def create_edge_driver(headless: bool = settings.HEADLESS) -> webdriver.Edge:
    """
    Crea o reutiliza una instancia de Microsoft Edge con perfil persistente.
    """
    logger = get_logger("browser_service")
    profile_path = Path(settings.EDGE_PROFILE_PATH)
    profile_path.mkdir(parents=True, exist_ok=True)

    options = EdgeOptions()
    if headless and not settings.ATTACH_TO_EDGE:
        options.add_argument("--headless=new")

    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.page_load_strategy = "eager"
    
    # Desactivar reduccion de rendimiento/throttling cuando la ventana pierde el foco
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")

    if settings.ATTACH_TO_EDGE:
        debugger_address = settings.EDGE_DEBUGGER_ADDRESS or "127.0.0.1:9222"
        logger.info("Conectando a la ventana existente de Edge en %s", debugger_address)
        options.add_experimental_option("debuggerAddress", debugger_address)
        return webdriver.Edge(service=_build_edge_service(logger), options=options)

    logger.info("Inicializando Microsoft Edge con perfil persistente en %s", profile_path)
    return _create_new_edge_instance(options, logger)


def create_firefox_driver(headless: bool = settings.HEADLESS) -> webdriver.Firefox:
    """
    Crea o reutiliza una instancia de Mozilla Firefox con perfil persistente.
    """
    logger = get_logger("browser_service")
    profile_path = Path(settings.FIREFOX_PROFILE_PATH)
    profile_path.mkdir(parents=True, exist_ok=True)

    options = FirefoxOptions()
    if headless:
        options.add_argument("-headless")

    options.add_argument("-profile")
    options.add_argument(str(profile_path))
    options.page_load_strategy = "eager"

    logger.info("Inicializando Mozilla Firefox con perfil persistente en %s", profile_path)
    return _create_new_firefox_instance(options, logger)


def _create_new_edge_instance(options: EdgeOptions, logger) -> webdriver.Edge:
    configured_driver = os.getenv("EDGEDRIVER_PATH")
    if configured_driver and Path(configured_driver).exists():
        logger.info("Usando msedgedriver configurado en EDGEDRIVER_PATH")
        return webdriver.Edge(service=EdgeService(configured_driver), options=options)

    local_driver = shutil.which("msedgedriver")
    if local_driver:
        logger.info("Usando msedgedriver disponible en PATH")
        return webdriver.Edge(service=EdgeService(local_driver), options=options)

    try:
        logger.info("Intentando iniciar Edge con Selenium Manager")
        return webdriver.Edge(options=options)
    except Exception as exc:
        logger.warning("Selenium Manager no pudo iniciar Edge: %s", exc)

    logger.info("Intentando obtener msedgedriver con webdriver-manager")
    service = EdgeService(EdgeChromiumDriverManager().install())
    return webdriver.Edge(service=service, options=options)


def _create_new_firefox_instance(options: FirefoxOptions, logger) -> webdriver.Firefox:
    configured_driver = os.getenv("GECKODRIVER_PATH")
    if configured_driver and Path(configured_driver).exists():
        logger.info("Usando geckodriver configurado en GECKODRIVER_PATH")
        return webdriver.Firefox(service=FirefoxService(configured_driver), options=options)

    local_driver = shutil.which("geckodriver")
    if local_driver:
        logger.info("Usando geckodriver disponible en PATH")
        return webdriver.Firefox(service=FirefoxService(local_driver), options=options)

    try:
        logger.info("Intentando iniciar Firefox con Selenium Manager")
        return webdriver.Firefox(options=options)
    except Exception as exc:
        logger.warning("Selenium Manager no pudo iniciar Firefox: %s", exc)

    logger.info("Intentando obtener geckodriver con webdriver-manager")
    service = FirefoxService(GeckoDriverManager().install())
    return webdriver.Firefox(service=service, options=options)


def _build_edge_service(logger) -> EdgeService:
    configured_driver = os.getenv("EDGEDRIVER_PATH")
    if configured_driver and Path(configured_driver).exists():
        logger.info("Usando msedgedriver configurado en EDGEDRIVER_PATH")
        return EdgeService(configured_driver)

    local_driver = shutil.which("msedgedriver")
    if local_driver:
        logger.info("Usando msedgedriver disponible en PATH")
        return EdgeService(local_driver)

    logger.info("Intentando obtener msedgedriver con webdriver-manager")
    return EdgeService(EdgeChromiumDriverManager().install())
