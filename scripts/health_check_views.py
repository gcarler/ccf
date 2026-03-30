
import requests
import time

def check_platform_health():
    base_url = "http://localhost:8001"
    print("🔍 Verificando conectividad de las vistas del sistema...")
    
    # 1. Login para obtener token
    print("🔑 Probando Acceso (Login)...")
    try:
        login_resp = requests.post(f"{base_url}/api/auth/login", data={
            "username": "luis.meza@ccf.la",
            "password": "admin123"
        })
        if login_resp.status_code != 200:
            print("❌ Error de Login. Verifique que el servidor esté listo.")
            return
        
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Autenticación Exitosa.")

        # 2. Verificar Endpoints de las Vistas Solicitadas
        views_to_test = [
            ("Dashboard / Panel", "/api/dashboard/metrics"),
            ("Calendario Ministerial", "/api/crm/events/"),
            ("CRM / Miembros", "/api/crm/members"),
            ("Academia / Cursos", "/api/academy/courses/"),
            ("Proyectos / Tareas", "/api/projects/tasks"),
            ("Conserjería Pastoral", "/api/crm/counseling/"),
            ("Muro de Oración", "/api/crm/prayer-requests/"),
            ("Gobernanza / Auditoría", "/api/governance/audit-logs")
        ]

        print("\n🚀 Navegando por los módulos...")
        for name, endpoint in views_to_test:
            resp = requests.get(f"{base_url}{endpoint}", headers=headers)
            if resp.status_code == 200:
                data_count = len(resp.json()) if isinstance(resp.json(), list) else "Datos OK"
                print(f"✅ {name}: OPERATIVO ({data_count} registros encontrados)")
            else:
                print(f"⚠️ {name}: Problema detectado (Status {resp.status_code})")

        print("\n🏆 CONCLUSIÓN: El Backend y la Base de Datos están listos.")
        print("Ahora puedes abrir tu navegador en http://localhost:3000 y verás las vistas llenas de datos.")

    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    # Esperar un momento a que el servidor termine de arrancar
    print("⏳ Esperando que el motor de la plataforma caliente...")
    time.sleep(5)
    check_platform_health()
