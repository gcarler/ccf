import requests


def test_login():
    url = "http://localhost:8000/auth/login"
    data = {"username": "admin@ccf.com", "password": "admin123"}

    print(f"Probando conexion a {url}...")
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            print("LOGIN EXITOSO!")
            print(f"Token recibido: {token_data['access_token'][:30]}...")

            # Probar el endpoint /me con el token
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            me_response = requests.get("http://localhost:8000/auth/me", headers=headers)
            if me_response.status_code == 200:
                print("PERFIL MINISTERIAL VALIDADO:")
                print(me_response.json())
            else:
                print(f"Error al obtener perfil: {me_response.status_code}")
        else:
            print(f"ERROR EN LOGIN: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Fallo de conexion: {e}")


if __name__ == "__main__":
    test_login()
