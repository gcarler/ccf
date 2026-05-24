import asyncio

import httpx


async def test():
    async with httpx.AsyncClient() as client:
        # Intentar login
        url = "http://127.0.0.1:8000/api/auth/login"
        data = {"username": "admin_ccf", "password": "admin123"}
        print(f"Probando login en {url}...")
        try:
            r = await client.post(url, data=data)
            print(f"Status: {r.status_code}")
            print(f"Respuesta: {r.text}")
        except Exception as e:
            print(f"Error de conexión: {e}")


if __name__ == "__main__":
    asyncio.run(test())
