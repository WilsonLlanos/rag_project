import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    # A connection string que você já tem no .env
    conn_str = os.getenv("AZURE_SQL_CONNECTION_STRING")
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"Erro ao conectar no SQL: {e}")
        return None

# Ferramentas para interagir com o banco de dados relacional (tool calling)
def consulta_saldo_lote(loteid: int):
    """consulta o status e saldo atual """