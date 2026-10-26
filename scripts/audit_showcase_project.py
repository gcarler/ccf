from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

# Setup project root in sys.path
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next((p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()), None)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app import app
from backend.core.database import SessionLocal
from backend.models import Sede
from backend.models_auth import Usuario
from backend.models_crm import Persona
from backend.models_projects import Project, ProjectTask
from starlette.testclient import TestClient


def audit_showcase_project() -> dict[str, Any]:
    db = SessionLocal()
    try:
        # 1. Resolve Showcase Project
        showcase_title = "Campus Virtual y Streaming 4K — Sedes CCF"
        project = db.query(Project).filter(Project.title == showcase_title).first()
        if not project:
            raise RuntimeError(f"No se encontró el proyecto '{showcase_title}'. Ejecuta seed_showcase_full_project.py primero.")

        project_id = str(project.id)
        print(f"Auditoría iniciada para Proyecto ID: {project_id}")

        # 2. Resolve Admin / PM User
        user = db.query(Usuario).filter(Usuario.username == "demo-projects").first()
        if not user:
            user = db.query(Usuario).filter(Usuario.is_active == True).first()

        # 3. Resolve Tasks for sub-resource tests
        tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project.id).all()
        task_id = str(next((t.id for t in tasks if t.title.startswith("Adquisición")), tasks[0].id))
        print(f"Usuario evaluador: {user.username} (ID: {user.id})")
        print(f"Total tareas vinculadas: {len(tasks)}")

        from backend.core.permissions import create_access_token
        access_token = create_access_token(data={"sub": str(user.id), "username": user.username})
        headers = {"Authorization": f"Bearer {access_token}"}

        client = TestClient(app)

        endpoints = [
            ("Detalle Proyecto", f"/api/projects/{project_id}"),
            ("Tareas (Kanban/Table/Gantt)", f"/api/projects/{project_id}/tasks"),
            ("Fases del Proyecto", f"/api/projects/{project_id}/phases"),
            ("Componentes EDT Nivel 2", f"/api/projects/{project_id}/components"),
            ("Regla 100% Presupuestal", f"/api/projects/{project_id}/components/budget-100-rule"),
            ("Árbol WBS / EDT", f"/api/projects/{project_id}/wbs-tree"),
            ("Dependencias (Flow/Gantt)", f"/api/projects/{project_id}/dependencies"),
            ("Ruta Crítica", f"/api/projects/{project_id}/critical-path"),
            ("Valor Ganado (EVM)", f"/api/projects/{project_id}/evm"),
            ("Curva S de EVM", f"/api/projects/{project_id}/evm/curve-s"),
            ("Líneas Base", f"/api/projects/{project_id}/baselines"),
            ("Time Tracking Logs", f"/api/projects/{project_id}/time-logs"),
            ("Time Tracking Resumen", f"/api/projects/{project_id}/time-tracking-summary"),
            ("Gastos Registrados", f"/api/projects/{project_id}/expenses"),
            ("Resumen de Presupuesto", f"/api/projects/{project_id}/budget-summary"),
            ("Matriz de Riesgos", f"/api/projects/{project_id}/risks"),
            ("Resumen de Riesgos y EMV", f"/api/projects/{project_id}/risks-summary"),
            ("Carga de Trabajo (Workload)", f"/api/projects/{project_id}/workload"),
            ("Equipo del Proyecto", f"/api/projects/{project_id}/team"),
            ("Acta Constitución (Charter)", f"/api/projects/{project_id}/charter"),
            ("Registro de Interesados", f"/api/projects/{project_id}/stakeholders"),
            ("Control de Cambios (CCB)", f"/api/projects/{project_id}/change-requests"),
            ("Calidad y CoQ Summary", f"/api/projects/{project_id}/quality-summary"),
            ("Bóveda Documental (Files)", f"/api/projects/{project_id}/files"),
            ("Resumen de Archivos", f"/api/projects/{project_id}/files/summary"),
            ("Wiki del Proyecto", f"/api/projects/{project_id}/wiki"),
            ("Pizarra (Whiteboard)", f"/api/projects/{project_id}/whiteboard"),
            ("Indicadores MGA CREMA", f"/api/projects/{project_id}/advanced-indicators"),
            ("Matriz de Ejecución Indicadores", f"/api/projects/{project_id}/indicators/execution-matrix"),
            ("KPIs Operativos", f"/api/projects/{project_id}/kpis"),
            ("Reglas de Automatización", f"/api/projects/{project_id}/automations"),
            ("Export Datos Ejecutivos", f"/api/projects/{project_id}/export/executive-data"),
            ("Export PDF Resumen", f"/api/projects/{project_id}/export/summary-pdf"),
            ("Insumos de Tarea (Supplies)", f"/api/projects/{project_id}/tasks/{task_id}/supplies"),
            ("Dimensiones de Tarea", f"/api/projects/{project_id}/tasks/{task_id}/dimensions"),
            ("Aceptación DoD de Tarea", f"/api/projects/{project_id}/tasks/{task_id}/dod-acceptance"),
            ("Estado DoD de Tarea", f"/api/projects/{project_id}/tasks/{task_id}/dod-status"),
        ]

        results = {
            "project_id": project_id,
            "project_title": project.title,
            "tested_endpoints": len(endpoints),
            "ok": [],
            "partial": [],
            "failed": [],
        }

        print("\n" + "=" * 80)
        print("EJECUTANDO BATERÍA DE PRUEBAS DE INTEGRACIÓN SOBRE EL PROYECTO SHOWCASE")
        print("=" * 80)

        for name, url in endpoints:
            try:
                res = client.get(url, headers=headers)
                status = res.status_code
                content_type = res.headers.get("content-type", "")

                if status == 200:
                    if "application/json" in content_type:
                        data = res.json()
                        # Analyze data completeness
                        is_empty_or_zero = False
                        if isinstance(data, list) and len(data) == 0:
                            is_empty_or_zero = True
                        elif isinstance(data, dict) and len(data) == 0:
                            is_empty_or_zero = True

                        if is_empty_or_zero:
                            results["partial"].append({
                                "name": name,
                                "url": url,
                                "status": status,
                                "reason": "Retornó 200 pero la lista o estructura de datos está vacía.",
                            })
                            print(f"⚠️  [PARCIAL]  {name:35} | {url:50} -> 200 (payload vacío)")
                        else:
                            results["ok"].append({
                                "name": name,
                                "url": url,
                                "status": status,
                                "size": len(res.content),
                            })
                            print(f"✅  [OK]       {name:35} | {url:50} -> 200 ({len(res.content)} bytes)")
                    elif "application/pdf" in content_type:
                        results["ok"].append({
                            "name": name,
                            "url": url,
                            "status": status,
                            "size": len(res.content),
                        })
                        print(f"✅  [OK]       {name:35} | {url:50} -> 200 PDF ({len(res.content)} bytes)")
                    else:
                        results["ok"].append({
                            "name": name,
                            "url": url,
                            "status": status,
                            "size": len(res.content),
                        })
                        print(f"✅  [OK]       {name:35} | {url:50} -> 200 ({content_type})")
                else:
                    results["failed"].append({
                        "name": name,
                        "url": url,
                        "status": status,
                        "error": res.text[:200],
                    })
                    print(f"❌  [FALLO]    {name:35} | {url:50} -> {status} ({res.text[:80]})")

            except Exception as e:
                results["failed"].append({
                    "name": name,
                    "url": url,
                    "status": "EXCEPTION",
                    "error": str(e),
                })
                print(f"💥  [EXCEPCIÓN] {name:35} | {url:50} -> {e}")

        print("\n" + "=" * 80)
        print("RESUMEN DE AUDITORÍA:")
        print(f"  Total herramientas probadas: {len(endpoints)}")
        print(f"  ✓ Funcionó Bien:             {len(results['ok'])}")
        print(f"  ⚠️ Funcionó a Medias:        {len(results['partial'])}")
        print(f"  ❌ No Funcionó:              {len(results['failed'])}")
        print("=" * 80)

        return results

    finally:
        db.close()


if __name__ == "__main__":
    audit_showcase_project()
