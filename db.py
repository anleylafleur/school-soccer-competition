import os
import pyodbc



pyodbc.pooling = False


def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{os.getenv('DB_SERVER')},1433;"
        f"DATABASE={os.getenv('DB_NAME')};"
        f"UID={os.getenv('DB_USER')};"
        f"PWD={os.getenv('DB_PASSWORD')};"
        "Encrypt=yes;"
<<<<<<< HEAD
        "TrustServerCertificate=no;"
        "Connection Timeout=60;"
=======
        "TrustServerCertificate=yes;"
        "Connection Timeout=120;"
>>>>>>> e6bb30e3c32320a55a0a4e3576676ff2cebeab41
    )