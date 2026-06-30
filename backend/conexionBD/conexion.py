# backend/conexionBD/conexion.py
import os
from dotenv import load_dotenv

load_dotenv()  # carga las variables desde el archivo .env

DB_NAME = os.getenv("DB_NAME", "test_docs")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tesis")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# Construir la URL de conexión para SQLAlchemy
DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"