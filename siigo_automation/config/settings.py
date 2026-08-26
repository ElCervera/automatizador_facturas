from pathlib import Path
import os

"""
Configuracion central del proyecto.
"""

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR = PROJECT_ROOT / "debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

SIIGO_URL: str = os.getenv("SIIGO_URL", "https://pos.siigo.com/")
WAIT_TIMEOUT: int = int(os.getenv("WAIT_TIMEOUT", "20"))
HEADLESS: bool = os.getenv("HEADLESS", "false").lower() == "true"

import sys

# Detección de plataforma y navegador por defecto
DEFAULT_BROWSER: str = "edge" if sys.platform.startswith("win") else "firefox"
BROWSER_TYPE: str = os.getenv("BROWSER_TYPE", DEFAULT_BROWSER).lower()

# Perfiles persistentes para conservar la sesión iniciada
EDGE_PROFILE_PATH: str = os.getenv(
    "EDGE_PROFILE_PATH",
    str(PROJECT_ROOT / ".edge_profile"),
)
FIREFOX_PROFILE_PATH: str = os.getenv(
    "FIREFOX_PROFILE_PATH",
    str(PROJECT_ROOT / ".firefox_profile"),
)

EXCEL_PATH: str = os.getenv("EXCEL_PATH", str(DATA_DIR / "facturacion.xlsx"))

# Ajustes operativos.
POST_SEND_WAIT_SECONDS: float = float(os.getenv("POST_SEND_WAIT_SECONDS", "3"))
POST_NAVIGATION_WAIT_SECONDS: float = float(os.getenv("POST_NAVIGATION_WAIT_SECONDS", "1.5"))
DEFAULT_PRODUCT_PREFIX: str = os.getenv("DEFAULT_PRODUCT_PREFIX", "HUEVO")
EDGE_DEBUGGER_ADDRESS: str | None = os.getenv("EDGE_DEBUGGER_ADDRESS")
ATTACH_TO_EDGE: bool = os.getenv("ATTACH_TO_EDGE", "false").lower() == "true"
WAIT_FOR_MANUAL_SETUP: bool = os.getenv("WAIT_FOR_MANUAL_SETUP", "true").lower() == "true"
DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() == "true"
PATCHED_RETRY_DELAY_SECONDS: float = float(os.getenv("PATCHED_RETRY_DELAY_SECONDS", "5"))
PATCHED_MAX_ATTEMPTS_PER_INVOICE: int = int(
    os.getenv("PATCHED_MAX_ATTEMPTS_PER_INVOICE", "0")
)

# Credenciales opcionales. El flujo principal reutiliza una sesion ya iniciada.
SIIGO_USER: str | None = os.getenv("SIIGO_USER")
SIIGO_PASSWORD: str | None = os.getenv("SIIGO_PASSWORD")

Path(EDGE_PROFILE_PATH).mkdir(parents=True, exist_ok=True)
Path(FIREFOX_PROFILE_PATH).mkdir(parents=True, exist_ok=True)

