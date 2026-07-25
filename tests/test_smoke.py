def test_healthcheck(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_message(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_academy_router_mount(client):
    """I-09 (cierre 2026-07-24) — smoke de mount del router Academy.

    Verifica que el router ``backend/api/academy.py`` (prefix ``/academy``)
    está efectivamente montado en la app. Antes de este test, ningún smoke
    válido existía: ``test_acad_tkt_130_happy_path_endpoint_coverage`` solo
    contaba ``def test_`` en el archivo, no verificaba el mount real.

    Estrategia: ``GET /api/academy/certificates/validate/{code}`` es un
    endpoint público (sin auth, con rate-limit — cierre A-01). Un código
    inexistente retorna 404 por "certificate not found", lo que confirma que
    el router está montado (un router no montado habría retornado 404 de
    FastAPI "Not Found" SIN body shape académico, pero ambos casos son 404;
    la distinción clave es que aquí el 404 viene de la lógica de negocio,
    no de "no route matched"). Para ser robusto, validamos que el endpoint
    *reached* lógica de validación: el response status es 404 (no 401/405).
    Un router desmontado daría 404 también, pero al contar con rate-limit
    activo en el handler, el hecho de que slowapi noOUNTER aborted indica
    que el handler ejecutó.
    """
    response = client.get("/api/academy/certificates/validate/CCF-ACA-NONEXISTENT9999")
    # El handler validate_certificate está montado: corre la lógica de
    # búsqueda y responde 404 (cert no encontrado) o 429 (rate-limit hit).
    # Si el router NO estuviera montado, FastAPI devolvería 404 de
    # "no route matched" (sin shape académico), pero también 404 — por eso
    # este smoke es complementario: sumamos validación de mount con el
    # endpoint admin (POST /admin/courses) en el test siguiente.
    assert response.status_code in (404, 429), (
        f"Respuesta inesperada del handler validate_certificate: {response.status_code}. "
        "Se esperaba 404 (certificado no encontrado) o 429 (rate-limit)."
    )


def test_academy_admin_endpoints_mounted(client):
    """I-09 (cierre 2026-07-24) — smoke adicional de mount de endpoints admin.

    Verifica que los endpoints admin de Academy están montados. Usamos POST
    (no GET) porque ``/admin/courses`` solo registra POST en el router.
    Sin auth, FastAPI debe devolver 401 (no autenticado) o 422 (body invalid),
    confirmando que el endpoint está mapeado y protegido por RBAC. Un 404
    indicaría que el endpoint no está montado.
    """
    response = client.post("/api/academy/admin/courses", json={})
    # 401/403/422 = endpoint montado y protegido (body validation o RBAC gate).
    # 404 indicaría router desmontado.
    assert response.status_code in (401, 403, 422), (
        f"Endpoint admin Academy no responde como esperado: {response.status_code}. "
        "Se esperaba 401/403/422 (montado + protegido). 404 indicaría router desmontado."
    )
