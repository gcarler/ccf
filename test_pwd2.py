import pg8000.native

ports = [5432, 5433]
for port in ports:
    try:
        con = pg8000.native.Connection(user="postgres", password="password", host="localhost", port=port)
        print(f"SUCCESS on port {port}")
        con.close()
    except Exception as e:
        print(f"Port {port} failed: {e}")
