from fastapi.testclient import TestClient
from backend.app import app
from backend.auth import get_current_user, require_active_user
from backend.models import User

def override_get_current_user():
    return User(id=1, email="test@test.com", is_active=True, role="ADMIN")

app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[require_active_user] = override_get_current_user

client = TestClient(app)
response = client.post("/api/projects/", json={
    "title": "Nuevo Proyecto Test",
    "description": "",
    "color": "#2563eb",
    "status": "active"
})
print("STATUS:", response.status_code)
print("BODY:", response.json())
