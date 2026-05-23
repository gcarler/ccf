import os
import sys

import requests

BASE_URL = os.getenv("CCF_BASE_URL", "http://localhost:8001")


def audit_endpoint(method, path, data=None, params=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = None
        if method == "GET":
            response = requests.get(f"{BASE_URL}{path}", params=params, headers=headers)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{path}", json=data, headers=headers)
        elif method == "PATCH":
            response = requests.patch(f"{BASE_URL}{path}", json=data, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        status = response.status_code
        try:
            result = response.json()
        except Exception:
            result = response.text

        return status, result
    except Exception as e:
        return 500, str(e)


def run_audit():
    print("--- STARTING CCF PLATFORM AUDIT ---")

    # 1. Test Root
    s, r = audit_endpoint("GET", "/")
    print(f"[ROOT] Status: {s} - {'OK' if s == 200 else 'FAIL'}")

    # 2. Test Auth Login
    admin_email = os.getenv("CCF_ADMIN_EMAIL", "admin.demo@ccf.local")
    admin_password = os.getenv("CCF_ADMIN_PASSWORD")

    if not admin_password:
        print("[AUTH] ERROR: Set CCF_ADMIN_PASSWORD environment variable. Skipping auth tests.")
        token = None
    else:
        print("\n[AUTH] Testing Admin Login...")
        payload = {"username": admin_email, "password": admin_password}
        try:
            resp = requests.post(f"{BASE_URL}/auth/login", data=payload)
            s = resp.status_code
            if s == 200:
                token = resp.json().get("access_token")
                print(f"[AUTH] Login successful. Token obtained.")
            else:
                token = None
                print(f"[AUTH] Login FAILED: {s} - {resp.text}")
        except Exception as e:
            token = None
            print(f"[AUTH] Connection error: {e}")

    if token:
        # 3. Test Courses
        s, r = audit_endpoint("GET", "/courses/", token=token)
        print(f"[COURSES] List: {s} (Found: {len(r) if isinstance(r, list) else 0})")

        # 4. Test Testimonials (Admin)
        s, r = audit_endpoint("GET", "/admin/testimonials", token=token)
        print(f"[TESTIMONIALS] Admin: {s} (Found: {len(r) if isinstance(r, list) else 0})")

        # 5. Test Members
        s, r = audit_endpoint("GET", "/crm/members/", token=token)
        print(f"[MEMBERS] List: {s} (Found: {len(r) if isinstance(r, list) else 0})")

        # 6. Test Enrollment logic
        if isinstance(r, list) and len(r) > 0:
            user_id = r[0].get("id")
            s, r = audit_endpoint("GET", f"/users/{user_id}/enrollments", token=token)
            print(f"[ENROLLMENTS] User {user_id}: {s}")

    print("\n--- AUDIT COMPLETE ---")


if __name__ == "__main__":
    run_audit()
