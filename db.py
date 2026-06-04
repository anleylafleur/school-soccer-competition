import os
import pyodbc

pyodbc.pooling = False

def get_connection():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{server},1433;"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=120;"
        "LoginTimeout=120;"
    )