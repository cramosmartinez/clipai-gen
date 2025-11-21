# backend/init_app_manual.py
import sys
import os
import pathlib

# CRÍTICO: Añadir backend al PATH para las importaciones
sys.path.append(os.path.dirname(os.path.abspath(__file__))) 

from app import init_db
from werkzeug.security import generate_password_hash # Necesario si quieres agregar usuarios manualmente

if __name__ == "__main__":
    print("🚀 1. Creando tablas 'clips' y 'users' y usuario 'test'...")
    try:
        init_db() # Llama a la función que crea las tablas y el usuario 'test'
        print("✅ Tablas creadas y usuario 'test' insertado.")
    except Exception as e:
        print(f"❌ Error al inicializar DB: {e}")