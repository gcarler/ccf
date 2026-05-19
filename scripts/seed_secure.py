import requests
import time

BASE_URL = "http://localhost:8000"

def seed_secure():
    print("Seeding secure database...")
    
    # Create Admin
    admin_data = {
        "username": "admin",
        "email": "admin@ccf.com",
        "password": "adminpassword123",
        "role": "admin"
    }
    
    try:
        # Check if user exists by trying to login
        login_data = {"username": admin_data["email"], "password": admin_data["password"]}
        response = requests.post(f"{BASE_URL}/token", data=login_data)
        
        if response.status_code == 200:
            print("Admin already exists and is secure.")
            token = response.json()["access_token"]
        else:
            # Create user
            response = requests.post(f"{BASE_URL}/users/", json=admin_data)
            if response.status_code == 200:
                print("Secure Admin created.")
            else:
                print(f"Error creating admin: {response.text}")
            
            # Login to get token
            response = requests.post(f"{BASE_URL}/token", data=login_data)
            token = response.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        
        # Create Testimonials if needed
        test_testimonials = [
            {"content": "La nueva plataforma de formación es excelente.", "emotion": "Feliz", "author_id": 1},
            {"content": "El CRM nos ayuda a estar más conectados.", "emotion": "Agradecido", "author_id": 1}
        ]
        
        for t in test_testimonials:
            requests.post(f"{BASE_URL}/api/cms/testimonials", json=t)
        
        print("Seed completed successfully.")
        
    except Exception as e:
        print(f"Connection failed: {e}. Is the backend running?")

if __name__ == "__main__":
    # Wait for backend
    time.sleep(5)
    seed_secure()
