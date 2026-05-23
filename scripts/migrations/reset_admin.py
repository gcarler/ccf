import sqlite3

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def reset_admin():
    try:
        # Usar la base de datos correcta
        db_path = "ccf_v2.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Contraseña a establecer
        new_password = "Admin123!"
        hashed_password = pwd_context.hash(new_password)

        # Verificar si el usuario existe
        cursor.execute("SELECT id FROM users WHERE username = 'admin_ccf'")
        user = cursor.fetchone()

        if user:
            # Actualizar contraseña
            cursor.execute(
                "UPDATE users SET password_hash = ?, is_active = 1 WHERE username = 'admin_ccf'",
                (hashed_password,),
            )
            print(f"EXITO: Contraseña de 'admin_ccf' actualizada a: {new_password}")
        else:
            # Crear si no existe
            cursor.execute(
                "INSERT INTO users (username, password_hash, is_active) VALUES (?, ?, 1)",
                ("admin_ccf", hashed_password),
            )
            print(f"EXITO: Usuario 'admin_ccf' creado con contraseña: {new_password}")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    reset_admin()
