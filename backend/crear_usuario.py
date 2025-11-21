# backend/crear_usuario.py
import sqlite3
import os
from werkzeug.security import generate_password_hash

# Ruta a tu DB
db_path = os.path.join(os.path.dirname(__file__), 'temp', 'clips.db')

def create_admin():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    user = "admin"
    pwd = "123"
    hashed = generate_password_hash(pwd)
    
    try:
        cursor.execute("INSERT INTO users (username, password_hash, credits) VALUES (?, ?, ?)", (user, hashed, 100))
        conn.commit()
        print(f"✅ Usuario creado exitosamente: {user} / {pwd}")
    except sqlite3.IntegrityError:
        print(f"⚠️ El usuario '{user}' ya existe. Borra clips.db si quieres resetear.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_admin()