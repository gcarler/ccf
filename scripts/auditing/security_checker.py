def test_security_logic():
    print("🔐 Iniciando Test de Privilegios y Seguridad")

    # Simulación de roles
    roles_prueba = [
        {"user": "pedro_lider", "role": "coordinador"},
        {"user": "ana_estudiante", "role": "estudiante"},
        {"user": "luis_admin", "role": "admin"},
    ]

    sensitive_actions = ["delete_donation", "view_audit_log", "manage_access"]

    permissions = {
        "admin": ["delete_donation", "view_audit_log", "manage_access"],
        "pastor": ["view_audit_log"],
        "coordinador": [],
        "estudiante": [],
    }

    for u in roles_prueba:
        print(f"\n👤 Usuario: {u['user']} (Rol: {u['role']})")
        for action in sensitive_actions:
            allowed = action in permissions.get(u["role"], [])
            status = "✅ BLOQUEADO" if not allowed else "⚠️ PERMITIDO"
            print(f"   - Acción '{action}': {status}")


if __name__ == "__main__":
    test_security_logic()
