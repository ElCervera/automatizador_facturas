
import pandas as pd
import os
import glob

files = glob.glob("resultados/stock_optimizado_*.xlsx")
if files:
    latest_file = max(files, key=os.path.getmtime)
    print(f"Checking file: {latest_file}")
    df = pd.read_excel(latest_file)
    print(df[['tipo', 'valor unitario', 'huevos_disponibles', 'huevos_a_vender']].head(20))
else:
    print("No files found")
