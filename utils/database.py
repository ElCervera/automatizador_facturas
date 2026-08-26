import sqlite3
import os
from datetime import datetime
import pandas as pd

DB_FILE = os.path.join(os.getcwd(), "automatizador.db")

def get_conn():
    conn = sqlite3.connect(DB_FILE, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_db():
    sql_ventas = """
    CREATE TABLE IF NOT EXISTS ventas_reales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        anio INTEGER,
        mes TEXT,
        dia INTEGER,
        n_factura TEXT,
        tipo TEXT,
        cantidad_huevos INTEGER,
        precio_unitario REAL,
        valor_total REAL,
        cliente TEXT,
        observaciones TEXT
    );
    """
    sql_clientes = """
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE
    );
    """
    sql_aud = """
    CREATE TABLE IF NOT EXISTS auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        accion TEXT,
        detalle TEXT
    );
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(sql_ventas + sql_clientes + sql_aud)
    conn.commit()
    conn.close()

def log_accion(accion, detalle=""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO auditoria (timestamp, accion, detalle) VALUES (?, ?, ?)",
        (datetime.utcnow().isoformat(), accion, detalle)
    )
    conn.commit()
    conn.close()

def safe_float(val):
    """Convierte valores numéricos con seguridad (quita $ o comas)."""
    if pd.isna(val) or val == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace("$", "").replace(",", "").replace(" ", "").replace("-", "0"))
    except Exception:
        return 0.0

def safe_int(val):
    """Convierte valores enteros con seguridad."""
    try:
        return int(round(safe_float(val)))
    except Exception:
        return 0

def guess_month_year_from_filename(filename):
    """Extrae mes y año a partir del nombre del archivo."""
    filename = filename.lower()
    meses = {
        "ene": "Enero", "feb": "Febrero", "mar": "Marzo", "abr": "Abril",
        "may": "Mayo", "jun": "Junio", "jul": "Julio", "ago": "Agosto",
        "sep": "Septiembre", "oct": "Octubre", "nov": "Noviembre", "dic": "Diciembre"
    }
    anio = datetime.now().year
    mes = "Desconocido"
    for key, nombre in meses.items():
        if key in filename:
            mes = nombre
            break
    for token in filename.split("_"):
        if token.isdigit() and len(token) == 4:
            anio = int(token)
            break
    return mes, anio

def insertar_ventas_from_dataframe(df, filename="desconocido.xlsx"):
    mes, anio = guess_month_year_from_filename(filename)
    conn = get_conn()
    cur = conn.cursor()
    rows = []
    
    calendar_months = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    for _, r in df.iterrows():
        try:
            n_factura = str(r.get("N factura", "")).strip()
            tipo = str(r.get("Tipo", "")).strip()
            cantidad = safe_int(r.get("Cantidad", 0))
            precio = safe_float(r.get("Valor Unitario", r.get("Precio base", 0)))
            cliente = str(r.get("Tercero", "") or "SIN CLIENTE").strip()
            valor_total = cantidad * precio

            fecha_iso = f"{anio}-{list(calendar_months.keys())[list(calendar_months.values()).index(mes)]+1:02d}-01" if mes != "Desconocido" else datetime.utcnow().strftime("%Y-%m-%d")

            rows.append((fecha_iso, anio, mes, 1, n_factura, tipo, cantidad, precio, valor_total, cliente, filename))
        except Exception as e:
            print(f"[ERROR] Error en fila: {e}")

    cur.executemany("""
        INSERT INTO ventas_reales (fecha, anio, mes, dia, n_factura, tipo, cantidad_huevos, precio_unitario, valor_total, cliente, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()

    # Insertar clientes únicos
    clientes_unicos = set([r[9] for r in rows if r[9]])
    for c in clientes_unicos:
        try:
            cur.execute("INSERT OR IGNORE INTO clientes (nombre) VALUES (?)", (c,))
        except Exception:
            pass

    conn.commit()
    conn.close()
    log_accion("import_excel", f"{len(rows)} filas importadas de {filename}")
    return len(rows)

def query_ventas(sql, params=()):
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

inicializar_db()
