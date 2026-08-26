import json
from datetime import datetime
from pathlib import Path
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from siigo_automation.config.settings import DEBUG_DIR



def collect_semantics_nodes(driver: WebDriver) -> list[dict[str, Any]]:
    """
    Extrae nodos relevantes de Flutter semantics para entender la UI real.
    """
    script = """
        const nodes = Array.from(document.querySelectorAll('flt-semantics'));
        return nodes.map((node, index) => {
            const rect = node.getBoundingClientRect();
            const text = (node.innerText || node.textContent || '').trim();
            const childLabels = Array.from(
                node.querySelectorAll('[aria-label]')
            ).map((child) => child.getAttribute('aria-label') || '').filter(Boolean);
            return {
                index,
                id: node.id || '',
                role: node.getAttribute('role') || '',
                ariaLabel: node.getAttribute('aria-label') || '',
                childAriaLabels: childLabels,
                tappable: node.hasAttribute('flt-tappable'),
                text,
                tagName: node.tagName.toLowerCase(),
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                visible: rect.width > 0 && rect.height > 0,
            };
        }).filter((node) => (
            node.visible &&
            (node.text || node.ariaLabel || node.role || node.tappable)
        ));
    """
    return driver.execute_script(script)


def dump_semantics_snapshot(
    driver: WebDriver,
    label: str,
    logger,
    output_dir: str | Path | None = None,
) -> dict[str, str]:
    """
    Guarda HTML, screenshot y mapa semantico en debug/.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in label)
    safe_label = safe_label.strip("_") or "semantics"

    target_dir = Path(output_dir) if output_dir is not None else Path(DEBUG_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    base_path = target_dir / f"{timestamp}_{safe_label}"
    screenshot_path = base_path.with_suffix(".png")
    html_path = base_path.with_suffix(".html")
    semantics_path = base_path.with_suffix(".semantics.json")
    text_path = base_path.with_suffix(".semantics.txt")

    try:
        driver.save_screenshot(str(screenshot_path))
    except Exception as exc:
        logger.warning("No se pudo guardar screenshot semantico: %s", exc)

    try:
        html_path.write_text(driver.page_source, encoding="utf-8")
    except Exception as exc:
        logger.warning("No se pudo guardar HTML semantico: %s", exc)

    nodes = []
    try:
        nodes = collect_semantics_nodes(driver)
        semantics_path.write_text(
            json.dumps(nodes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        text_path.write_text(_format_nodes(nodes), encoding="utf-8")
    except Exception as exc:
        logger.warning("No se pudo guardar mapa semantico: %s", exc)

    logger.info("Nodos semanticos detectados: %s", len(nodes))
    logger.warning("Snapshot semantico: %s", semantics_path)

    return {
        "screenshot": str(screenshot_path),
        "html": str(html_path),
        "semantics": str(semantics_path),
        "text": str(text_path),
    }


def find_semantics_elements(driver: WebDriver, needle: str):
    """
    Busca elementos flt-semantics por texto visible o aria-label.
    """
    normalized = _normalize(needle)
    if not normalized:
        return []

    matches = []
    for element in driver.find_elements(By.CSS_SELECTOR, "flt-semantics"):
        try:
            text = _normalize(element.text)
            aria = _normalize(element.get_attribute("aria-label"))
            child_aria = _normalize(
                " ".join(
                    child.get_attribute("aria-label") or ""
                    for child in element.find_elements(By.CSS_SELECTOR, "[aria-label]")
                )
            )
            if normalized in text or normalized in aria or normalized in child_aria:
                matches.append(element)
        except Exception:
            continue
    return matches


def element_summary(element) -> str:
    try:
        rect = element.rect
    except Exception:
        rect = {}

    bits = [
        f"role={element.get_attribute('role') or ''}",
        f"aria={element.get_attribute('aria-label') or ''}",
        f"text={(element.text or '').strip()}",
        f"rect={rect}",
    ]
    return " | ".join(bits)


def _format_nodes(nodes: list[dict[str, Any]]) -> str:
    lines = []
    for node in nodes:
        child_labels = ", ".join(node.get("childAriaLabels", []))
        label = node["ariaLabel"] or child_labels or node["text"]
        if not label and not node["role"]:
            continue
        lines.append(
            "#{index} role={role} tappable={tappable} "
            "x={x} y={y} w={width} h={height} label={label!r}".format(
                label=label,
                **node,
            )
        )
    return "\n".join(lines)


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def find_semantics_elements(driver: WebDriver, needle: str):
    """
    Busca elementos flt-semantics por texto visible o aria-label de manera optimizada y rápida.
    """
    normalized = _normalize(needle)
    if not normalized:
        return []

    try:
        nodes = collect_semantics_nodes(driver)
    except Exception:
        return _find_semantics_elements_fallback(driver, needle, use_text_content=False)

    matches = []
    for node in nodes:
        node_text = _normalize(node.get("text", ""))
        node_aria = _normalize(node.get("ariaLabel", ""))
        child_aria = _normalize(" ".join(node.get("childAriaLabels", [])))

        if normalized in node_text or normalized in node_aria or normalized in child_aria:
            node_id = node.get("id")
            if node_id:
                try:
                    element = driver.find_element(By.ID, node_id)
                    matches.append(element)
                except Exception:
                    continue
    return matches


def find_semantics_elements_v2(driver: WebDriver, needle: str):
    """
    Busca elementos flt-semantics por textContent visible o aria-label de manera optimizada y rápida.
    Evita el problema de ocultamiento de texto por aria-label del padre en Selenium.
    """
    normalized = _normalize(needle)
    if not normalized:
        return []

    try:
        nodes = collect_semantics_nodes(driver)
    except Exception:
        return _find_semantics_elements_fallback(driver, needle, use_text_content=True)

    matches = []
    for node in nodes:
        node_text = _normalize(node.get("text", ""))
        node_aria = _normalize(node.get("ariaLabel", ""))
        child_aria = _normalize(" ".join(node.get("childAriaLabels", [])))

        if normalized in node_text or normalized in node_aria or normalized in child_aria:
            node_id = node.get("id")
            if node_id:
                try:
                    element = driver.find_element(By.ID, node_id)
                    matches.append(element)
                except Exception:
                    continue
    return matches


def _find_semantics_elements_fallback(driver: WebDriver, needle: str, use_text_content=False):
    normalized = _normalize(needle)
    if not normalized:
        return []

    matches = []
    for element in driver.find_elements(By.CSS_SELECTOR, "flt-semantics"):
        try:
            if use_text_content:
                text = _normalize(element.get_attribute("textContent"))
            else:
                text = _normalize(element.text)
            aria = _normalize(element.get_attribute("aria-label"))
            child_aria = _normalize(
                " ".join(
                    child.get_attribute("aria-label") or ""
                    for child in element.find_elements(By.CSS_SELECTOR, "[aria-label]")
                )
            )
            if normalized in text or normalized in aria or normalized in child_aria:
                matches.append(element)
        except Exception:
            continue
    return matches
