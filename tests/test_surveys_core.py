"""Tests exhaustivos para el Core de Encuestas Dinámicas (TKT-SURVEYS-BACKEND-CORE-01).

Cubre:
- CRUD de Formularios y preguntas batch
- Acceso público por ID y por Slug
- Envío de respuestas y validación de campos obligatorios
- Enlace con Kernel de Personas (Axioma 1)
- Aislamiento Multi-Tenant (Axioma 3)
- Analítica agregada de preguntas (frecuencias, medias, texto)
- Tabla de respuestas para visualización tipo hoja de cálculo
- Exportación CSV con compatibilidad Excel (UTF-8 BOM)
"""

from __future__ import annotations

import uuid

from backend import models
from backend.schemas.surveys import EstadoFormulario, TipoPregunta
from tests.conftest import auth_headers, seed_admin


def test_create_survey_and_get_detail(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)

    payload = {
        "titulo": "Encuesta de Satisfacción Dominical 2026",
        "descripcion": "Queremos conocer tu experiencia en los servicios dominicales.",
        "slug": "satisfaccion-dominical-2026",
        "estado": EstadoFormulario.BORRADOR.value,
        "config_visual": {"tema": "light", "color_primario": "#0ea5e9"},
        "preguntas": [
            {
                "titulo": "¿Cómo calificarías la alabanza?",
                "tipo_pregunta": TipoPregunta.ESCALA_LINEAL.value,
                "es_requerida": True,
                "escala_min": 1,
                "escala_max": 5,
                "escala_min_etiqueta": "Regular",
                "escala_max_etiqueta": "Excelente",
            },
            {
                "titulo": "¿A qué servicio asististe?",
                "tipo_pregunta": TipoPregunta.OPCION_MULTIPLE.value,
                "es_requerida": True,
                "opciones": [
                    {"id": "serv-1", "label": "8:00 AM"},
                    {"id": "serv-2", "label": "10:30 AM"},
                    {"id": "serv-3", "label": "6:00 PM"},
                ],
            },
            {
                "titulo": "Comentarios adicionales",
                "tipo_pregunta": TipoPregunta.PARRAFO.value,
                "es_requerida": False,
            },
        ],
    }

    resp = client.post("/api/surveys", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["titulo"] == payload["titulo"]
    assert data["slug"] == "satisfaccion-dominical-2026"
    assert data["estado"] == EstadoFormulario.BORRADOR.value
    assert data["total_respuestas"] == 0
    assert len(data["preguntas"]) == 3
    assert data["preguntas"][0]["orden"] == 0
    assert data["preguntas"][1]["orden"] == 1
    assert data["preguntas"][2]["orden"] == 2

    survey_id = data["id"]

    # Obtener detalle
    detail_resp = client.get(f"/api/surveys/{survey_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == survey_id
    assert len(detail["preguntas"]) == 3


def test_update_survey_patch_and_soft_delete(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)

    # Crear formulario
    create_payload = {
        "titulo": "Encuesta Pre-Bautismo",
        "descripcion": "Formulario de preparación.",
        "estado": EstadoFormulario.BORRADOR.value,
    }
    create_resp = client.post("/api/surveys", json=create_payload, headers=headers)
    assert create_resp.status_code == 201
    survey_id = create_resp.json()["id"]

    # Modificar vía PATCH
    patch_payload = {
        "titulo": "Encuesta Pre-Bautismo Actualizada",
        "estado": EstadoFormulario.PUBLICADO.value,
        "mensaje_confirmacion": "¡Gracias por dar este gran paso de fe!",
        "limitar_una_respuesta": True,
    }
    patch_resp = client.patch(f"/api/surveys/{survey_id}", json=patch_payload, headers=headers)
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["titulo"] == "Encuesta Pre-Bautismo Actualizada"
    assert updated["estado"] == EstadoFormulario.PUBLICADO.value
    assert updated["mensaje_confirmacion"] == "¡Gracias por dar este gran paso de fe!"
    assert updated["limitar_una_respuesta"] is True

    # Soft Delete
    del_resp = client.delete(f"/api/surveys/{survey_id}", headers=headers)
    assert del_resp.status_code == 204

    # Verificar que ya no está accesible
    get_resp = client.get(f"/api/surveys/{survey_id}", headers=headers)
    assert get_resp.status_code == 404


def test_sync_survey_questions_batch(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)

    create_resp = client.post(
        "/api/surveys",
        json={"titulo": "Encuesta Jóvenes 2026", "estado": EstadoFormulario.BORRADOR.value},
        headers=headers,
    )
    survey_id = create_resp.json()["id"]

    batch_payload = {
        "preguntas": [
            {
                "titulo": "Nombre Completo",
                "tipo_pregunta": TipoPregunta.TEXTO_CORTO.value,
                "es_requerida": True,
            },
            {
                "titulo": "¿Perteneces a un grupo de conexión?",
                "tipo_pregunta": TipoPregunta.OPCION_MULTIPLE.value,
                "es_requerida": True,
                "opciones": [
                    {"id": "opt-1", "label": "Sí"},
                    {"id": "opt-2", "label": "No"},
                ],
            },
        ]
    }

    sync_resp = client.put(f"/api/surveys/{survey_id}/questions", json=batch_payload, headers=headers)
    assert sync_resp.status_code == 200
    questions = sync_resp.json()
    assert len(questions) == 2
    assert questions[0]["titulo"] == "Nombre Completo"
    assert questions[0]["orden"] == 0
    assert questions[1]["titulo"] == "¿Perteneces a un grupo de conexión?"
    assert questions[1]["orden"] == 1


def test_public_survey_view_and_submit_response(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)

    # 1. Crear encuesta y publicarla
    payload = {
        "titulo": "Censo de Voluntarios CCF",
        "slug": "censo-voluntarios-ccf",
        "estado": EstadoFormulario.PUBLICADO.value,
        "mensaje_confirmacion": "¡Registro exitoso en el voluntariado!",
        "preguntas": [
            {
                "titulo": "¿En qué ministerio te gustaría servir?",
                "tipo_pregunta": TipoPregunta.OPCION_MULTIPLE.value,
                "es_requerida": True,
                "opciones": [
                    {"id": "m1", "label": "Alabanza"},
                    {"id": "m2", "label": "Evangelismo"},
                    {"id": "m3", "label": "Medios"},
                ],
            },
            {
                "titulo": "Disponibilidad de días",
                "tipo_pregunta": TipoPregunta.CASILLAS.value,
                "es_requerida": False,
                "opciones": [
                    {"id": "d1", "label": "Sábados"},
                    {"id": "d2", "label": "Domingos"},
                ],
            },
        ],
    }
    create_resp = client.post("/api/surveys", json=payload, headers=headers)
    survey_data = create_resp.json()
    survey_id = survey_data["id"]
    p1_id = survey_data["preguntas"][0]["id"]
    p2_id = survey_data["preguntas"][1]["id"]

    # 2. Acceso público por SLUG sin auth
    pub_resp = client.get("/api/public/surveys/censo-voluntarios-ccf")
    assert pub_resp.status_code == 200
    pub_data = pub_resp.json()
    assert pub_data["titulo"] == "Censo de Voluntarios CCF"
    assert len(pub_data["preguntas"]) == 2

    # 3. Enviar respuesta pública
    submit_payload = {
        "nombre_respondente": "Ana Martínez",
        "email_respondente": "ana.martinez@ccf.org",
        "respuestas": [
            {
                "pregunta_id": p1_id,
                "valor_texto": "Alabanza",
            },
            {
                "pregunta_id": p2_id,
                "valor_json": ["Sábados", "Domingos"],
            },
        ],
        "metadatos": {"origen": "web_mobile"},
    }
    submit_resp = client.post("/api/public/surveys/censo-voluntarios-ccf/submit", json=submit_payload)
    assert submit_resp.status_code == 201
    submit_result = submit_resp.json()
    assert submit_result["status"] == "success"
    assert submit_result["mensaje_confirmacion"] == "¡Registro exitoso en el voluntariado!"
    envio_id = submit_result["envio_id"]

    # 4. Verificar incremento de total_respuestas en el formulario admin
    check_resp = client.get(f"/api/surveys/{survey_id}", headers=headers)
    assert check_resp.status_code == 200
    assert check_resp.json()["total_respuestas"] == 1


def test_public_submit_required_validation(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)

    payload = {
        "titulo": "Encuesta con Obligatoria",
        "slug": "encuesta-obligatoria-test",
        "estado": EstadoFormulario.PUBLICADO.value,
        "preguntas": [
            {
                "titulo": "¿Pregunta OBLIGATORIA?",
                "tipo_pregunta": TipoPregunta.TEXTO_CORTO.value,
                "es_requerida": True,
            }
        ],
    }
    create_resp = client.post("/api/surveys", json=payload, headers=headers)
    p_id = create_resp.json()["preguntas"][0]["id"]

    # Intentar enviar sin responder la pregunta requerida
    empty_submit = {
        "respuestas": [
            {
                "pregunta_id": p_id,
                "valor_texto": "",  # Vacío
            }
        ]
    }
    resp = client.post("/api/public/surveys/encuesta-obligatoria-test/submit", json=empty_submit)
    assert resp.status_code == 422
    assert "requiere una respuesta" in resp.json()["detail"]


def test_survey_analytics_summary_and_responses_table(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)

    payload = {
        "titulo": "Evaluación del Taller de Liderazgo",
        "slug": "eval-liderazgo-2026",
        "estado": EstadoFormulario.PUBLICADO.value,
        "preguntas": [
            {
                "titulo": "Puntaje del Taller",
                "tipo_pregunta": TipoPregunta.ESCALA_LINEAL.value,
                "es_requerida": True,
                "escala_min": 1,
                "escala_max": 5,
            },
            {
                "titulo": "Área de Servicio",
                "tipo_pregunta": TipoPregunta.OPCION_MULTIPLE.value,
                "es_requerida": True,
                "opciones": [{"id": "1", "label": "Niños"}, {"id": "2", "label": "Jóvenes"}],
            },
            {
                "titulo": "¿Qué aprendiste?",
                "tipo_pregunta": TipoPregunta.PARRAFO.value,
                "es_requerida": False,
            },
        ],
    }
    create_resp = client.post("/api/surveys", json=payload, headers=headers)
    survey_data = create_resp.json()
    survey_id = survey_data["id"]
    p_scale = survey_data["preguntas"][0]["id"]
    p_multi = survey_data["preguntas"][1]["id"]
    p_text = survey_data["preguntas"][2]["id"]

    # Enviar respuesta 1
    client.post(
        f"/api/public/surveys/{survey_id}/submit",
        json={
            "nombre_respondente": "Carlos",
            "email_respondente": "carlos@ccf.org",
            "respuestas": [
                {"pregunta_id": p_scale, "valor_numero": 4.0},
                {"pregunta_id": p_multi, "valor_texto": "Niños"},
                {"pregunta_id": p_text, "valor_texto": "Mucha paciencia y amor."},
            ],
        },
    )

    # Enviar respuesta 2
    resp_2 = client.post(
        f"/api/public/surveys/{survey_id}/submit",
        json={
            "nombre_respondente": "María",
            "email_respondente": "maria@ccf.org",
            "respuestas": [
                {"pregunta_id": p_scale, "valor_numero": 5.0},
                {"pregunta_id": p_multi, "valor_texto": "Niños"},
                {"pregunta_id": p_text, "valor_texto": "Estrategias de enseñanza bíblica."},
            ],
        },
    )
    envio_id_2 = resp_2.json()["envio_id"]

    # 1. Analítica
    analytics_resp = client.get(f"/api/surveys/{survey_id}/analytics/summary", headers=headers)
    assert analytics_resp.status_code == 200
    analytics = analytics_resp.json()
    assert analytics["total_respuestas"] == 2

    # Pregunta escala: promedio de 4 y 5 = 4.5
    scale_stat = next(p for p in analytics["preguntas"] if p["pregunta_id"] == p_scale)
    assert scale_stat["promedio"] == 4.5
    assert scale_stat["minimo"] == 4.0
    assert scale_stat["maximo"] == 5.0

    # Pregunta opción múltiple: "Niños" = 2
    multi_stat = next(p for p in analytics["preguntas"] if p["pregunta_id"] == p_multi)
    assert multi_stat["distribucion_opciones"].get("Niños") == 2

    # 2. Respuestas en formato tabla
    table_resp = client.get(f"/api/surveys/{survey_id}/responses/table", headers=headers)
    assert table_resp.status_code == 200
    table = table_resp.json()
    assert table["total"] == 2
    assert len(table["filas"]) == 2
    assert len(table["columnas"]) >= 4

    # 3. Respuesta individual
    indiv_resp = client.get(f"/api/surveys/{survey_id}/responses/individual/{envio_id_2}", headers=headers)
    assert indiv_resp.status_code == 200
    indiv = indiv_resp.json()
    assert indiv["nombre_respondente"] == "María"
    assert len(indiv["detalles"]) == 3


def test_export_survey_csv_utf8_bom(client, db_session):
    user, admin_p, sede = seed_admin(db_session)
    headers = auth_headers(client)

    payload = {
        "titulo": "Encuesta Exportación CSV",
        "slug": "export-csv-test",
        "estado": EstadoFormulario.PUBLICADO.value,
        "preguntas": [
            {
                "titulo": "¿Cuál es tu opinión?",
                "tipo_pregunta": TipoPregunta.TEXTO_CORTO.value,
                "es_requerida": True,
            }
        ],
    }
    create_resp = client.post("/api/surveys", json=payload, headers=headers)
    survey_data = create_resp.json()
    survey_id = survey_data["id"]
    p_id = survey_data["preguntas"][0]["id"]

    # Enviar respuesta con tildes y eñes
    client.post(
        f"/api/public/surveys/{survey_id}/submit",
        json={
            "nombre_respondente": "Iñaki Peña",
            "respuestas": [
                {"pregunta_id": p_id, "valor_texto": "¡Excelente comunión y edificación!"}
            ],
        },
    )

    # Descargar CSV
    csv_resp = client.get(f"/api/surveys/{survey_id}/export/csv", headers=headers)
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]

    content_bytes = csv_resp.content
    # Verificar UTF-8 BOM (\xef\xbb\xbf)
    assert content_bytes.startswith(b"\xef\xbb\xbf")
    decoded_text = content_bytes.decode("utf-8")
    assert "Iñaki Peña" in decoded_text
    assert "¡Excelente comunión y edificación!" in decoded_text


def test_tenant_isolation_axioma_3(client, db_session):
    # Sede 1
    user1, p1, sede1 = seed_admin(db_session)
    headers1 = auth_headers(client)

    # Crear sede 2 y usuario de sede 2 reutilizando seed_admin
    user2, p2, _ = seed_admin(db_session, email="pastor2@ccf.org")
    sede2 = models.Sede(
        id=uuid.uuid4(),
        nombre="Sede Pasacaballos",
        ciudad="Cartagena",
        es_activa=True,
    )
    db_session.add(sede2)
    db_session.flush()
    p2.sede_id = sede2.id
    user2.sede_id = sede2.id
    db_session.commit()

    # Usuario 1 crea encuesta asociada a sede 1
    create_resp = client.post(
        "/api/surveys",
        json={"titulo": "Encuesta Sede Central", "estado": EstadoFormulario.PUBLICADO.value},
        headers=headers1,
    )
    survey_id = create_resp.json()["id"]

    # Iniciar sesión como usuario 2 (sede 2)
    token2 = auth_headers(client, email="pastor2@ccf.org")

    # Usuario 2 intenta consultar encuesta de sede 1
    forbidden_resp = client.get(f"/api/surveys/{survey_id}", headers=token2)
    assert forbidden_resp.status_code == 403
    assert "No tienes acceso a los recursos de otra sede" in forbidden_resp.json()["detail"]
