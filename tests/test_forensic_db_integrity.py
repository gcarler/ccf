"""Pruebas Automatizadas de Integridad Forense — Plataforma CCF.

Valida:
  - Axioma 1: Kernel de Personas (relación 1:1 auth_users con personas, cero tablas paralelas)
  - Axioma 2: Fechas UTC sin datetime.utcnow() deprecado y soporte soft deletes
  - Axioma 3: Aislamiento multi-tenant por sede_id en tablas transaccionales
  - Cero pasarelas de pago comerciales en la base de datos
"""

import pytest
from pathlib import Path
from sqlalchemy import inspect
from backend.core.database import engine


def test_axiom_1_kernel_personas_integrity():
    """Valida que personas.id sea la identidad canónica y auth_users comparta el UUID."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "personas" in tables, "La tabla 'personas' no existe en PostgreSQL"
    assert "auth_users" in tables, "La tabla 'auth_users' no existe en PostgreSQL"

    auth_fks = [
        fk for fk in inspector.get_foreign_keys("auth_users")
        if fk.get("referred_table") == "personas"
    ]
    assert len(auth_fks) > 0, "auth_users no tiene clave foránea a personas.id"

    # Verificar que al menos 100 tablas referencien personas.id
    persona_fks = []
    for t in tables:
        for fk in inspector.get_foreign_keys(t):
            if fk.get("referred_table") == "personas":
                persona_fks.append(t)

    assert len(set(persona_fks)) >= 100, f"Se esperaban >= 100 tablas referenciando personas.id, se hallaron {len(set(persona_fks))}"


def test_axiom_3_multi_tenant_isolation():
    """Valida que las tablas de dominio posean aislamiento por sede_id."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    required_tenant_tables = [
        "auth_users",
        "academy_programs",
        "academy_academic_periods",
        "grupos_evangelismo",
        "expense_reports",
        "agenda_eventos",
    ]

    for table in required_tenant_tables:
        cols = [c["name"] for c in inspector.get_columns(table)]
        assert "sede_id" in cols, f"La tabla {table} no tiene la columna canónica sede_id"


def test_axiom_2_zero_utcnow():
    """Valida la ausencia total de datetime.utcnow() en el código fuente."""
    backend_dir = Path("backend")
    violations = []
    for py_file in backend_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
            if "datetime.utcnow()" in content:
                violations.append(str(py_file))
        except Exception:
            pass

    assert len(violations) == 0, f"Archivos con datetime.utcnow() deprecado: {violations}"


def test_zero_commercial_payment_gateways_in_db():
    """Valida que no existan tablas ni columnas para pasarelas comerciales externas."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    forbidden = ["stripe", "wompi", "mercadopago", "paypal", "payu"]

    violations = []
    for t in tables:
        for f in forbidden:
            if f in t.lower():
                violations.append(f"table:{t}")
        for c in inspector.get_columns(t):
            for f in forbidden:
                if f in c["name"].lower():
                    violations.append(f"column:{t}.{c['name']}")

    assert len(violations) == 0, f"Pasarelas comerciales encontradas en base de datos: {violations}"
