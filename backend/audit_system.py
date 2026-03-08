import requests
import json

BASE_URL = "http://localhost:8001"

def audit_endpoint(method, path, data=None, params=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{path}", params=params, headers=headers)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{path}", json=data, headers=headers)
        elif method == "PATCH":
            response = requests.patch(f"{BASE_URL}{path}", json=data, headers=headers)
        
        status = response.status_code
        try:
            result = response.json()
        except:
            result = response.text
            
        return status, result
    except Exception as e:
        return 500, str(e)

def run_audit():
    print("--- INICIANDO AUDITORÍA CCF PLATFORM ---")
    
    # 1. Test Root
    s, r = audit_endpoint("GET", "/")
    print(f"[ROOT] Status: {s} - {'OK' if s==200 else 'FAIL'}")

    # 2. Test Auth Login
    print("\n[AUTH] Probando Login Admin...")
    payload = {"username": "admin.demo@ccf.local", "password": "admin1234"}
    # Note: /auth/login uses form data, not JSON usually in FastAPI OAuth2
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", data=payload)
        s = resp.status_code
        if s == 200:
            token = resp.json().get("access_token")
            print(f"[AUTH] Login exitoso. Token obtenido.")
        else:
            token = None
            print(f"[AUTH] Login FALLIDO: {s} - {resp.text}")
    except Exception as e:
        token = None
        print(f"[AUTH] Error de conexión: {e}")

    if token:
        # 3. Test Courses
        s, r = audit_endpoint("GET", "/courses/", token=token)
        print(f"[COURSES] Listado: {s} (Encontrados: {len(r) if isinstance(r, list) else 0})")

        # 4. Test Testimonials (Admin)
        s, r = audit_endpoint("GET", "/admin/testimonials/", token=token)
        print(f"[TESTIMONIALS] Admin: {s} (Encontrados: {len(r) if isinstance(r, list) else 0})")

        # 5. Test Members
        s, r = audit_endpoint("GET", "/members/", token=token)
        print(f"[MEMBERS] Listado: {s} (Encontrados: {len(r) if isinstance(r, list) else 0})")

        # 6. Test Enrollment logic
        if isinstance(r, list) and len(r) > 0:
            user_id = r[0].get("id") # Using first user for test
            s, r = audit_endpoint("GET", f"/users/{user_id}/enrollments", token=token)
            print(f"[ENROLLMENTS] Usuario {user_id}: {s}")

    print("\n--- FIN DE LA AUDITORÍA ---")

if __name__ == "__main__":
    run_audit()
