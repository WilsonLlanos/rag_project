import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

conn_str = os.getenv("AZURE_SQL_CONNECTION_STRING")
print(f"Tentando conectar com: {conn_str}")

try:
    conn = pyodbc.connect(conn_str)
    print("✅ CONEXÃO BEM SUCEDIDA!")
    conn.close()
except Exception as e:
    print(f"❌ ERRO FATAL: {e}")