import sqlite3


def final_verify():
    try:
        conn = sqlite3.connect("ccf_v2.db")
        cursor = conn.cursor()

        # Asegurar que admin_ccf tenga el rol de admin y esté activo
        cursor.execute(
            "UPDATE users SET role = 'admin', is_active = 1 WHERE username = 'admin_ccf'"
        )

        # Verificar cómo quedó
        cursor.execute(
            "SELECT id, username, role, is_active FROM users WHERE username = 'admin_ccf'"
        )
        result = cursor.fetchone()

        if result:
            print(f"VERIFICACIÓN FINAL:")
            print(f"ID: {result[0]}")
            print(f"Usuario: {result[1]}")
            print(f"Rol: {result[2]}")
            print(f"Estado: {'Activo' if result[3] else 'Inactivo'}")
            print("\nAhora sí, puedes entrar con total seguridad.")
        else:
            print("ERROR: El usuario no existe.")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    final_verify()
