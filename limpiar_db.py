# limpiar_db.py
import sqlite3
import os

DB_FILE = os.path.join(os.getcwd(), "automatizador.db")

if os.path.exists(DB_FILE):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Vaciar tablas (sin borrarlas)
    cur.executescript("""
    DELETE FROM ventas_reales;
    DELETE FROM clientes;
    DELETE FROM auditoria;
    DELETE FROM stock_optimizado;
    VACUUM;
    """)

    conn.commit()
    conn.close()
    print("[OK] Base de datos limpiada correctamente.")
else:
    print("[AVISO] No se encontró el archivo automatizador.db")
