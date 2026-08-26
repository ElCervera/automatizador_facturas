from typing import Tuple, Any
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver

def wait_for_presence(driver: WebDriver, locator: Tuple[str, str], timeout: int):
    """
    Espera la presencia de un elemento en el DOM.
    """
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))

def wait_clickable(driver: WebDriver, locator: Tuple[str, str], timeout: int):
    """
    Espera a que un elemento sea cliqueable.
    """
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))

def click_when_clickable(driver: WebDriver, locator: Tuple[str, str], timeout: int):
    """
    Hace clic cuando el elemento es cliqueable.
    """
    elem = wait_clickable(driver, locator, timeout)
    elem.click()
    return elem

def type_when_visible(driver: WebDriver, locator: Tuple[str, str], text: str, timeout: int):
    """
    Escribe texto cuando el elemento es visible.
    """
    elem = WebDriverWait(driver, timeout).until(EC.visibility_of_element_located(locator))
    elem.clear()
    elem.send_keys(text)
    return elem
