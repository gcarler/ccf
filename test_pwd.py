import pg8000.native

passwords = ["postgres", "admin", "root", "", "1234", "12345", "123456", "password"]
ports = [5432, 5433]

for port in ports:
    for pwd in passwords:
        try:
            con = pg8000.native.Connection(user="postgres", password=pwd, host="localhost", port=port)
            print(f"SUCCESS on port {port} with password '{pwd}'")
            con.close()
            break
        except Exception as e:
            # print(f"Failed {port} {pwd}: {e}")
            pass
