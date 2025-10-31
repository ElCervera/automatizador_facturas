import json
import os

# Carga el diccionario de equivalencias
def cargar_diccionario():
    ruta = os.path.join(os.path.dirname(os.path.dirname(__file__)), "normalizacion_productos.json")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ No se encontró el archivo de normalización.")
        return {}

# Aplica la normalización al nombre del producto
def normalizar_producto(nombre):
    if not nombre:
        return ""
    nombre = nombre.strip().upper()  # elimina espacios y pasa a mayúsculas
    diccionario = cargar_diccionario()
    return diccionario.get(nombre, nombre)  # si no existe, devuelve el original
