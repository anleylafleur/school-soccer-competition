import pyodbc

def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=SchoolSoccerCompetitionDB;"
        "Trusted_Connection=yes;"
    )