import requests
import json

BASE_URL = "http://localhost:8000"

def seed():
    print("Seeding database...")
    
    # 1. Create User
    user_data = {
        "username": "admin",
        "email": "admin@ccf.com",
        "role": "admin",
        "password": "password123"
    }
    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    if response.status_code == 200:
        user_id = response.json()["id"]
        print(f"User created with ID: {user_id}")
    else:
        print(f"User creation failed or exists: {response.text}")
        user_id = 1 # Assume 1 if exists

    # 2. Create Initial Testimonials
    testimonials = [
        {"content": "Increíble plataforma, me encanta la interfaz.", "emotion": "Inspirado", "author_id": user_id},
        {"content": "El CRM me ha facilitado mucho el trabajo con mi equipo.", "emotion": "Agradecido", "author_id": user_id},
        {"content": "Esperando con ansias los nuevos cursos de la academia.", "emotion": "Motivado", "author_id": user_id},
    ]

    for t in testimonials:
        res = requests.post(f"{BASE_URL}/api/cms/testimonials", json=t)
        if res.status_code in (200, 201):
            print(f"Testimonial created: {res.json()['id']}")
            
            # Auto-approve one for demo
            if "Interfaz" in t["content"]:
                t_id = res.json()["id"]
                requests.patch(f"{BASE_URL}/api/admin/testimonials/{t_id}", json={"is_approved": True})
                print(f"Testimonial {t_id} auto-approved.")

if __name__ == "__main__":
    seed()
