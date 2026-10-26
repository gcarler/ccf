"""Auditoría de ESCRITURA del módulo de proyectos sobre el proyecto showcase.

Cada paso ejecuta una mutación vía API, relee el recurso para verificar
persistencia y registra OK / PARCIAL / FALLO. Incluye pruebas negativas
(ciclo de dependencias, aislamiento por sede, rol de solo lectura).
Requiere haber ejecutado antes scripts/seeding/seed_showcase_full_project.py.
"""

from __future__ import annotations

import io
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

_HERE = Path(__file__).resolve()
_ROOT = next(p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file())
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.disable(logging.CRITICAL)

from backend import models  # noqa: F401,E402
from backend.app import app  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402
from backend.core.permissions import create_access_token  # noqa: E402
from backend.models_auth import RolPlataforma, Usuario  # noqa: E402
from backend.models_projects import Project, ProjectTask  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

TITLE = "Campus Virtual y Streaming 4K — Sedes CCF"
RESULTS: list[tuple[str, str, str]] = []


def _headers(user: Usuario) -> dict[str, str]:
    tok = create_access_token(data={"sub": str(user.id), "username": user.username})
    return {"Authorization": f"Bearer {tok}"}


def step(name: str, fn: Callable[[], tuple[str, str]]) -> None:
    try:
        verdict, note = fn()
    except Exception as exc:  # noqa: BLE001 - auditoría: capturar todo
        verdict, note = "FALLO", f"excepción: {exc!r}"[:200]
    icon = {"OK": "✅", "PARCIAL": "⚠️ ", "FALLO": "❌"}[verdict]
    RESULTS.append((name, verdict, note))
    print(f"{icon} [{verdict:7}] {name:48} {note}")


def pdf_bytes(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 750, text)
    c.save()
    return buf.getvalue()


def main() -> int:
    db = SessionLocal()
    admin = db.query(Usuario).filter(Usuario.username == "demo-projects").one()
    project = (
        db.query(Project).filter(Project.title == TITLE, Project.deleted_at.is_(None))
        .order_by(Project.created_at.desc()).first()
    )
    if not project:
        print("Proyecto showcase no encontrado; ejecuta la semilla primero.")
        return 2
    pid = str(project.id)
    base = f"/api/projects/{pid}"
    tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project.id, ProjectTask.deleted_at.is_(None)).all()
    by_title = {t.title: t for t in tasks}
    t_vlan = next(t for t in tasks if t.title.startswith("Configuración de routers"))
    t_cam = next(t for t in tasks if t.title.startswith("Instalación y calibración"))
    t_last = next(t for t in tasks if t.title.startswith("Transmisión oficial"))
    outsider = (
        db.query(Usuario).join(RolPlataforma, Usuario.rol_plataforma_id == RolPlataforma.id)
        .filter(RolPlataforma.nombre.ilike("admin%"), Usuario.is_active.is_(True), Usuario.sede_id != project.sede_id)
        .first()
    )
    reader = (
        db.query(Usuario).join(RolPlataforma, Usuario.rol_plataforma_id == RolPlataforma.id)
        .filter(RolPlataforma.nombre == "LECTOR", Usuario.is_active.is_(True)).first()
    )
    ind = db.query(models.ProjectIndicator).filter(models.ProjectIndicator.project_id == project.id).first()
    persona_id = str(admin.id)
    db.close()

    c = TestClient(app)
    h = _headers(admin)
    S: dict[str, Any] = {}
    print(f"Proyecto {pid}\n" + "=" * 100)

    def req(method: str, url: str, **kw: Any):
        return getattr(c, method)(url, headers=kw.pop("headers", h), **kw)

    # ---- Tareas ---------------------------------------------------------
    def create_task():
        r = req("post", f"{base}/tasks", json={"title": "AUDIT: tarea creada por API", "priority": "high",
                "status": "fase-2-inst", "estimated_hours": 4, "assignee_id": persona_id,
                "start_date": datetime.now(timezone.utc).isoformat(),
                "due_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        S["task"] = r.json()["id"]
        ids = [t["id"] for t in req("get", f"{base}/tasks").json()] if isinstance(req("get", f"{base}/tasks").json(), list) else []
        return ("OK", "creada y visible en listado") if S["task"] in ids else ("PARCIAL", "creada pero no aparece en GET /tasks")
    step("Crear tarea", create_task)

    def patch_task():
        r = req("patch", f"{base}/tasks/{S['task']}", json={"status": "fase-3-test", "physical_progress_pct": 50, "start_date": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(), "due_date": (datetime.now(timezone.utc) + timedelta(days=16)).isoformat()})
        if r.status_code != 200:
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        g = req("get", f"/api/projects/tasks/{S['task']}").json()
        ok = g.get("status") == "fase-3-test" and float(g.get("physical_progress_pct", 0)) == 50
        return ("OK", "estado y avance persistidos") if ok else ("PARCIAL", f"releído: {g.get('status')}/{g.get('physical_progress_pct')}")
    step("Editar tarea (estado + avance)", patch_task)

    def subtask():
        r = req("post", f"{base}/tasks/{S['task']}/subtasks", json={"title": "AUDIT: subtarea", "estimated_hours": 1, "status": "fase-2-inst"})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        S["sub"] = r.json()["id"]
        return "OK", "subtarea creada"
    step("Crear subtarea", subtask)

    def reassign():
        other = db2_other_persona
        r = req("patch", f"{base}/tasks/{S['task']}/reassign", json={"assignee_id": other})
        return ("OK", "reasignada") if r.status_code == 200 else ("FALLO", f"{r.status_code} {r.text[:120]}")
    s2 = SessionLocal()
    db2_other_persona = str(s2.query(models.Persona).filter(models.Persona.id != admin.id).first().id)
    s2.close()
    step("Reasignar tarea a otra persona", reassign)

    # ---- Dependencias / flow -------------------------------------------
    def dep_ok():
        r = req("post", f"{base}/dependencies", json={"predecessor_id": S["task"], "successor_id": str(t_last.id), "dependency_type": "FS", "lag_days": 0})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        S["dep"] = r.json()["id"]
        return "OK", "dependencia creada"
    step("Crear dependencia nueva", dep_ok)

    def dep_cycle():
        r = req("post", f"{base}/dependencies", json={"predecessor_id": str(t_last.id), "successor_id": S["task"], "dependency_type": "FS", "lag_days": 0})
        return ("OK", f"ciclo rechazado ({r.status_code})") if r.status_code in (400, 409, 422) else ("FALLO", f"ciclo no rechazado limpiamente (HTTP {r.status_code})")
    step("Rechazar dependencia circular", dep_cycle)

    def cpm():
        r = req("get", f"{base}/critical-path")
        return ("OK", "ruta crítica recalculada") if r.status_code == 200 and S.get("dep") else ("FALLO", f"{r.status_code}")
    step("Ruta crítica tras cambio de dependencias", cpm)

    # ---- Tiempo ---------------------------------------------------------
    def timelog():
        before = req("get", f"{base}/time-tracking-summary").json()
        r = req("post", f"{base}/time-logs", json={"task_id": S["task"], "hours": 2.5, "description": "AUDIT horas", "is_billable": True})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        S["log"] = r.json()["id"]
        after = req("get", f"{base}/time-tracking-summary").json()
        return ("OK", "horas registradas y resumen cambió") if after != before else ("PARCIAL", "registrada pero el resumen no cambió")
    step("Registrar horas", timelog)

    def timelog_neg():
        r = req("post", f"{base}/time-logs", json={"task_id": S["task"], "hours": -3})
        return ("OK", f"horas negativas rechazadas ({r.status_code})") if r.status_code in (400, 422) else ("FALLO", f"horas negativas ACEPTADAS ({r.status_code})")
    step("Rechazar horas negativas", timelog_neg)

    # ---- Costos ---------------------------------------------------------
    def supply():
        r = req("post", f"{base}/tasks/{t_cam.id}/supplies", json={"item_name": "AUDIT insumo", "quantity": 2, "unit_cost": 1000, "total_cost": 2000, "status": "approved"})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        S["supply"] = r.json()["id"]
        return "OK", f"insumo creado ({r.json().get('total_cost')})"
    step("Crear insumo de tarea", supply)

    def expense():
        before = req("get", f"{base}/budget-summary").json()
        r = req("post", f"{base}/expenses", json={"amount": 500000, "category": "equipment", "description": "AUDIT gasto", "status": "paid"})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        S["exp"] = r.json()["id"]
        after = req("get", f"{base}/budget-summary").json()
        return ("OK", "gasto registrado y presupuesto cambió") if after != before else ("PARCIAL", "gasto creado, budget-summary sin cambio")
    step("Registrar gasto", expense)

    def evm():
        r = req("get", f"{base}/evm")
        return ("OK", "EVM recalculado") if r.status_code == 200 else ("FALLO", str(r.status_code))
    step("EVM tras gasto/horas", evm)

    # ---- Riesgos / KPI / hitos -----------------------------------------
    def risk():
        r = req("post", f"{base}/risks", json={"title": "AUDIT riesgo", "probability": 4, "impact": 4, "financial_impact": 1000000, "probability_pct": 50, "risk_type": "threat"})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        S["risk"] = r.json()["id"]
        emv = r.json().get("emv")
        return ("OK", f"EMV={emv}") if emv == 500000 else ("PARCIAL", f"EMV esperado 500000, obtenido {emv}")
    step("Crear riesgo y validar EMV", risk)

    def risk_task():
        r = req("post", f"{base}/risks/{S['risk']}/convert-to-task")
        return ("OK", "riesgo convertido en tarea") if r.status_code in (200, 201) else ("FALLO", f"{r.status_code} {r.text[:120]}")
    step("Convertir riesgo en tarea", risk_task)

    def kpi():
        r = req("post", f"{base}/kpis", json={"title": "AUDIT KPI", "target_value": 100, "current_value": 10, "unit": "%"})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        S["kpi"] = r.json()["id"]
        p = req("patch", f"{base}/kpis/{S['kpi']}", json={"current_value": 60})
        return ("OK", "KPI creado y actualizado") if p.status_code == 200 else ("PARCIAL", f"creado; PATCH {p.status_code}")
    step("Crear y actualizar KPI", kpi)

    def milestone():
        r = req("post", f"{base}/milestones", json={"title": "AUDIT hito", "target_date": datetime.now(timezone.utc).isoformat()})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        p = req("patch", f"{base}/milestones/{r.json()['id']}", json={"is_completed": True})
        return ("OK", "hito creado y completado") if p.status_code == 200 else ("PARCIAL", f"PATCH {p.status_code}")
    step("Crear y completar hito", milestone)

    # ---- Indicadores CREMA ---------------------------------------------
    def crema():
        r = req("post", f"{base}/indicators/validate-crema", json={"name": "Porcentaje de sedes con transmisión 4K", "description": "Mide cobertura", "unit_of_measure": "%", "target_value": 100})
        return ("OK", f"CREMA validó ({r.status_code})") if r.status_code == 200 else ("FALLO", f"{r.status_code} {r.text[:120]}")
    step("Validar indicador (CREMA)", crema)

    def ind_rec():
        r = req("post", f"{base}/indicators/{ind.id}/records", json={"period": "2026-Q4-P3", "target_value": 75, "actual_value": 70, "notes": "AUDIT"})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        spi = r.json().get("spi")
        return ("OK", f"registro creado, SPI={spi}") if spi is not None else ("PARCIAL", "registro creado, SPI no calculado")
    step("Registrar avance de indicador", ind_rec)

    def ind_sync():
        r = req("post", f"{base}/indicators/sync-execution")
        return ("OK", "sincronización ejecutada") if r.status_code == 200 else ("FALLO", f"{r.status_code} {r.text[:120]}")
    step("Sincronizar indicadores con ejecución", ind_sync)

    # ---- Comunicación ---------------------------------------------------
    def comment():
        r = req("post", f"{base}/comments", json={"content": "AUDIT comentario", "task_id": S["task"], "mentions": [persona_id]})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        S["cmt"] = r.json()["id"]
        p = req("post", f"{base}/tasks/{S['task']}/comments/{S['cmt']}/pin")
        return ("OK", "comentario con mención y fijado") if p.status_code == 200 else ("PARCIAL", f"creado; pin {p.status_code}")
    step("Comentar con mención y fijar", comment)

    def message():
        r = req("post", f"{base}/messages", json={"content": "AUDIT mensaje de chat"})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        msgs = req("get", f"{base}/messages").json()
        return ("OK", "mensaje en el chat") if "AUDIT mensaje" in str(msgs) else ("PARCIAL", "enviado pero no listado")
    step("Enviar mensaje al chat del proyecto", message)

    def wiki():
        r = req("post", f"{base}/wiki", json={"title": "Wiki", "content": "# AUDIT wiki\ncontenido"})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        return ("OK", "wiki guardada") if "AUDIT wiki" in str(req("get", f"{base}/wiki").json()) else ("PARCIAL", "guardada pero GET no la refleja")
    step("Editar wiki", wiki)

    def whiteboard():
        r = req("post", f"{base}/whiteboard", json={"title": "Pizarra", "elements_json": "[]"})
        return ("OK", "pizarra guardada") if r.status_code in (200, 201) else ("FALLO", f"{r.status_code} {r.text[:120]}")
    step("Guardar pizarra", whiteboard)

    def fav():
        r = req("post", f"{base}/tasks/{S['task']}/toggle-favorite")
        return ("OK", "favorito alternado") if r.status_code == 200 else ("FALLO", f"{r.status_code}")
    step("Marcar tarea favorita", fav)

    # ---- Documentos PDF -------------------------------------------------
    def upload_vault():
        r = req("post", f"{base}/files/upload", files={"file": ("AUDIT_boveda.pdf", pdf_bytes("AUDIT vault"), "application/pdf")}, data={"category": "auditoria", "name": "AUDIT PDF bóveda"})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:140]}"
        S["file"] = r.json()
        d = c.get(S["file"]["file_url"])
        return ("OK", f"subido y descargable ({len(d.content)} B)") if d.status_code == 200 and d.content.startswith(b"%PDF") else ("PARCIAL", f"subido pero GET {S['file']['file_url']} -> {d.status_code}")
    step("Subir PDF a bóveda documental y descargarlo", upload_vault)

    def upload_attach():
        r = req("post", f"{base}/tasks/{S['task']}/attachments", files={"file": ("AUDIT_adjunto.pdf", pdf_bytes("AUDIT attach"), "application/pdf")})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:140]}"
        atts = r.json().get("attachments") or []
        if not atts:
            return "PARCIAL", "subido pero la respuesta no lista adjuntos"
        S["att"] = atts[-1]["id"]
        return "OK", "adjunto de tarea subido"
    step("Subir PDF como adjunto de tarea", upload_attach)

    def upload_bad():
        accepted = []
        for fname, ctype, data in [("virus.exe", "application/x-msdownload", b"MZ\x90\x00"), ("shell.php", "application/x-php", b"<?php echo 1;"),
                                   ("x.html", "text/html", b"<script>1</script>"), ("x.svg", "image/svg+xml", b"<svg onload=alert(1)>")]:
            r = req("post", f"{base}/files/upload", files={"file": (fname, data, ctype)})
            if r.status_code in (200, 201):
                accepted.append(fname)
                req("delete", f"{base}/files/{r.json()['id']}")
        return ("OK", "los 4 tipos peligrosos fueron rechazados") if not accepted else ("FALLO", "ACEPTADOS: " + ", ".join(accepted))
    step("Rechazar .exe/.php/.html/.svg en bóveda", upload_bad)

    def link_drive():
        r = req("post", f"{base}/files/link-drive", json={"name": "AUDIT Doc", "drive_url": "https://docs.google.com/document/d/1AUDITabc/edit", "category": "auditoria"})
        return ("OK", "enlace Drive vinculado") if r.status_code in (200, 201) else ("FALLO", f"{r.status_code} {r.text[:120]}")
    step("Vincular documento de Google Drive", link_drive)

    # ---- Gobierno PMI ---------------------------------------------------
    def ccr():
        r = req("post", f"{base}/change-requests", json={"title": "AUDIT CR", "justification": "prueba", "change_type": "budget", "cost_impact_delta": 100000, "schedule_impact_days": 1})
        if r.status_code not in (200, 201):
            return "FALLO", f"{r.status_code} {r.text[:120]}"
        d = req("post", f"{base}/change-requests/{r.json()['id']}/decide", json={"decision": "approved", "review_notes": "AUDIT"})
        return ("OK", "CR creada y decidida") if d.status_code == 200 else ("PARCIAL", f"creada; decide {d.status_code} {d.text[:100]}")
    step("Solicitud de cambio (CCB) crear + decidir", ccr)

    def dod():
        r = req("post", f"{base}/tasks/{S['task']}/dod-acceptance", json={"specification_met": True, "tests_no_critical_failures": True, "evidence_archived": True, "supervisor_sign_off": True, "coq_classification": "prevention", "coq_amount": 1000})
        return ("OK", "DoD aceptado") if r.status_code in (200, 201) else ("FALLO", f"{r.status_code} {r.text[:120]}")
    step("Aceptar DoD con costo de calidad", dod)

    def baseline():
        r = req("post", f"{base}/baselines", json={"name": "AUDIT baseline"})
        return ("OK", "línea base creada") if r.status_code in (200, 201) else ("FALLO", f"{r.status_code} {r.text[:120]}")
    step("Crear línea base", baseline)

    # ---- Seguridad ------------------------------------------------------
    def isolation():
        if not outsider:
            return "PARCIAL", "no hay admin de otra sede para probar"
        r = req("get", base, headers=_headers(outsider))
        return ("OK", f"otra sede bloqueada ({r.status_code})") if r.status_code in (403, 404) else ("FALLO", f"FUGA entre sedes ({r.status_code})")
    step("Aislamiento multi-sede (lectura)", isolation)

    def isolation_w():
        if not outsider:
            return "PARCIAL", "no hay admin de otra sede para probar"
        r = req("post", f"{base}/tasks", headers=_headers(outsider), json={"title": "intruso"})
        return ("OK", f"escritura entre sedes bloqueada ({r.status_code})") if r.status_code in (403, 404) else ("FALLO", f"ESCRITURA entre sedes ({r.status_code})")
    step("Aislamiento multi-sede (escritura)", isolation_w)

    def reader_write():
        if not reader:
            return "PARCIAL", "no hay usuario LECTOR para probar"
        r = req("post", f"{base}/tasks", headers=_headers(reader), json={"title": "lector escribe"})
        return ("OK", f"lector no puede escribir ({r.status_code})") if r.status_code in (403, 404) else ("FALLO", f"lector ESCRIBIÓ ({r.status_code})")
    step("Rol lector no puede escribir", reader_write)

    def noauth():
        r = c.get(base)
        return ("OK", "sin token -> 401") if r.status_code == 401 else ("FALLO", f"sin token -> {r.status_code}")
    step("Sin autenticación", noauth)

    # ---- Borrado lógico -------------------------------------------------
    def deletes():
        out = []
        for label, url in [("subtarea", f"{base}/tasks/{S.get('task')}/subtasks/{S.get('sub')}"), ("dependencia", f"{base}/dependencies/{S.get('dep')}"),
                           ("horas", f"{base}/time-logs/{S.get('log')}"), ("gasto", f"{base}/expenses/{S.get('exp')}"),
                           ("riesgo", f"{base}/risks/{S.get('risk')}"), ("kpi", f"{base}/kpis/{S.get('kpi')}"),
                           ("insumo", f"{base}/tasks/{t_cam.id}/supplies/{S.get('supply')}"),
                           ("adjunto", f"{base}/tasks/{S['task']}/attachments/{S.get('att')}"),
                           ("tarea", f"{base}/tasks/{S['task']}")]:
            r = req("delete", url)
            out.append((label, r.status_code))
        bad = [f"{k}:{v}" for k, v in out if v not in (200, 204)]
        return ("OK", "9 borrados lógicos correctos") if not bad else ("FALLO", "falló: " + ", ".join(bad))
    step("Borrar lo creado (soft delete)", deletes)

    def deleted_gone():
        ids = [t["id"] for t in req("get", f"{base}/tasks").json()]
        return ("OK", "tarea borrada ya no aparece") if S["task"] not in ids else ("FALLO", "tarea borrada SIGUE visible")
    step("Tarea borrada no aparece en listado", deleted_gone)

    print("=" * 100)
    n = {k: sum(1 for _, v, _ in RESULTS if v == k) for k in ("OK", "PARCIAL", "FALLO")}
    print(f"TOTAL {len(RESULTS)} | ✅ {n['OK']} | ⚠️ {n['PARCIAL']} | ❌ {n['FALLO']}")
    return 1 if n["FALLO"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
