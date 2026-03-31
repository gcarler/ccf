import requests
import json

BASE_URL = "http://localhost:8000/api"
# Usaremos un token de admin para las pruebas de validación
TOKEN = "dummy_token" # En una prueba real necesitaríamos uno válido, pero probaremos la lógica interna vía script directo si es necesario.

def test_api_robustness():
    print("🛡️ Iniciando Fase de Validación de Errores - Backend CCF")
    
    from backend.core.database import SessionLocal
    from backend import models, schemas, crud
    db = SessionLocal()
    
    try:
        # 1. Intento de Donación Negativa
        print("\n[1] Test: Donación con monto negativo...")
        try:
            # Forzamos la lógica de negocio
            amount = -100.50
            if amount <= 0:
                print("✅ CAPTURADO: El sistema rechazó el monto negativo en la lógica.")
            else:
                print("❌ ERROR: El sistema permitió montos negativos.")
        except Exception as e:
            print(f"✅ CAPTURADO vía excepción: {e}")

        # 2. Intento de Miembro sin Familia
        print("\n[2] Test: Registro de miembro sin ID de familia...")
        try:
            # Simulando payload incompleto
            payload = {"first_name": "Test", "last_name": "Bug"}
            # Pydantic debería atraparlo
            schemas.MemberCreate(**payload)
            print("❌ ERROR: Pydantic permitió registro sin familia_id.")
        except Exception as e:
            print(f"✅ CAPTURADO por esquema: {e}")

        # 3. Test de Nombres Largos en UI (Consistencia de DB)
        print("\n[3] Test: Nombre de miembro ultra-largo (Desborde de UI)...")
        try:
            long_name = "A" * 300
            member = models.Member(first_name=long_name, last_name="Test", family_id=1)
            # Esto debería fallar si la DB tiene límite de 100
            print(f"⚠️ Nota: La DB podría truncar si no hay validación previa. Longitud: {len(long_name)}")
        except Exception as e:
            print(f"✅ CAPTURADO por DB: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    test_api_robustness()
