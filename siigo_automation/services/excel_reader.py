from collections import OrderedDict
from pathlib import Path
from typing import Any
import re
import unicodedata

import pandas as pd


# Aliases para mapear encabezados de distintas versiones de Excel
COLUMN_ALIASES = {
    "numero_factura": ["n factura", "numero_factura", "numero factura", "n. factura", "n° factura", "nro factura"],
    "producto": ["tipo", "producto", "descripcion", "detalle"],
    "cantidad": ["n cubetas", "cubetas vendidas", "cantidad", "cant", "n_cubetas"],
    "precio_unitario": ["valor cubeta", "precio venta (cop/cubeta)", "precio_unitario", "precio unitario", "valor unitario", "precio"]
}

EXPECTED_COLUMNS = {
    "n factura": "numero_factura",
    "tipo": "producto",
    "n cubetas": "cantidad",
    "valor cubeta": "precio_unitario",
}


def _normalize_column_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text.strip().lower())
    return text


def _find_column_mapping(df_columns: list[Any]) -> dict[str, str] | None:
    """
    Encuentra un mapeo desde los nombres reales de las columnas en el DataFrame
    hacia las claves estándar (numero_factura, producto, cantidad, precio_unitario).
    """
    norm_to_orig = {_normalize_column_name(col): col for col in df_columns}
    mapping = {}

    for target_key, aliases in COLUMN_ALIASES.items():
        matched = False
        for alias in aliases:
            if alias in norm_to_orig:
                mapping[norm_to_orig[alias]] = target_key
                matched = True
                break
        if not matched:
            return None

    return mapping


def _parse_int(value: Any, field_name: str) -> int:
    if pd.isna(value):
        raise ValueError(f"El campo '{field_name}' viene vacio.")

    text = str(value).strip()
    if not text:
        raise ValueError(f"El campo '{field_name}' viene vacio.")

    try:
        return int(float(text))
    except ValueError as exc:
        raise ValueError(f"No se pudo convertir '{text}' a entero para '{field_name}'.") from exc


def _parse_money(value: Any) -> int:
    if pd.isna(value):
        raise ValueError("El precio unitario viene vacio.")

    if isinstance(value, (int, float)):
        return int(round(float(value)))

    text = str(value).strip()
    if not text:
        raise ValueError("El precio unitario viene vacio.")

    cleaned = text.replace("$", "").replace(" ", "")
    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        parts = cleaned.split(",")
        cleaned = "".join(parts) if len(parts[-1]) == 3 else ".".join(parts)
    elif "." in cleaned:
        parts = cleaned.split(".")
        cleaned = "".join(parts) if len(parts[-1]) == 3 else cleaned

    try:
        return int(round(float(cleaned)))
    except ValueError as exc:
        raise ValueError(f"No se pudo interpretar el precio unitario '{text}'.") from exc


def read_facturacion(path: Path) -> list[dict[str, Any]]:
    """
    Lee el Excel diario (o facturas generadas) y agrupa las líneas por número de factura.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de facturacion: {path}")

    xl = pd.ExcelFile(path, engine="openpyxl")
    df = None
    column_mapping = None

    for sheet_name in xl.sheet_names:
        try:
            temp_df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
            if temp_df.empty:
                continue
            mapping = _find_column_mapping(temp_df.columns)
            if mapping is not None:
                df = temp_df
                column_mapping = mapping
                break
        except Exception:
            continue

    if df is None:
        df = pd.read_excel(path, engine="openpyxl")
        if not df.empty:
            column_mapping = _find_column_mapping(df.columns)

    if df is None or df.empty:
        return []

    if column_mapping is None:
        raise ValueError(
            f"No se pudieron identificar las columnas obligatorias (N factura, Tipo, Cantidad/Cubetas, Precio) en {path.name}."
        )

    df = df.rename(columns=column_mapping)
    df = df[["numero_factura", "producto", "cantidad", "precio_unitario"]].dropna(how="all")

    facturas: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    for row_number, row in enumerate(df.to_dict(orient="records"), start=2):
        if pd.isna(row["numero_factura"]):
            continue
        numero_factura = str(row["numero_factura"]).strip()
        producto = str(row["producto"]).strip()
        cantidad = _parse_int(row["cantidad"], "Cantidad/Cubetas")
        precio_unitario = _parse_money(row["precio_unitario"])

        if not numero_factura:
            raise ValueError(f"La fila {row_number} no tiene 'N factura'.")
        if not producto:
            raise ValueError(f"La fila {row_number} no tiene 'Tipo'.")
        if cantidad <= 0:
            raise ValueError(f"La fila {row_number} tiene una cantidad invalida: {cantidad}.")
        if precio_unitario <= 0:
            raise ValueError(
                f"La fila {row_number} tiene un precio unitario invalido: {precio_unitario}."
            )

        if numero_factura not in facturas:
            facturas[numero_factura] = {
                "numero_factura": numero_factura,
                "items": [],
            }

        facturas[numero_factura]["items"].append(
            {
                "producto": producto,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "row_number": row_number,
            }
        )

    return list(facturas.values())


def exportar_facturas_exitosas(facturas: list[dict[str, Any]], directorio_salida: str | Path = "data") -> None:
    """
    Exporta las facturas procesadas exitosamente a un nuevo archivo Excel
    manteniendo la estructura de columnas original.
    """
    import datetime
    
    if not facturas:
        return

    path_salida = Path(directorio_salida)
    path_salida.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_salida = path_salida / f"facturas_procesadas_{timestamp}.xlsx"

    filas = []
    for factura in facturas:
        numero = factura["numero_factura"]
        for item in factura["items"]:
            filas.append({
                "n factura": numero,
                "tipo": item["producto"],
                "n cubetas": item["cantidad"],
                "valor cubeta": item["precio_unitario"],
            })

    df = pd.DataFrame(filas)
    columnas_ordenadas = list(EXPECTED_COLUMNS.keys())
    df = df[columnas_ordenadas]
    
    df.to_excel(archivo_salida, index=False, engine="openpyxl")
    return archivo_salida
