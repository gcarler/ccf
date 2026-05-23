import json
import os
import sys
from datetime import datetime

# Añadir el directorio raíz al path para importar backend
sys.path.append(os.getcwd())

from backend import crud, models, schemas
from backend.agents.orchestrator import AgentOrchestrator
from backend.core.database import SessionLocal


def perform_forensic_audit():
    print("🚀 Iniciando Auditoría Forense de Tuberías via Neural MESH...")

    db = SessionLocal()
    try:
        # 1. Recolectar contexto real
        users_count = db.query(models.User).count()
        projects_count = db.query(models.Project).count()
        members_count = db.query(models.Member).count()
        tasks_count = db.query(models.AgentTask).count()

        # Obtener una muestra de las tablas
        users_sample = [
            {"id": u.id, "role": u.role} for u in db.query(models.User).limit(5).all()
        ]
        projects_sample = [
            {"id": p.id, "title": p.title}
            for p in db.query(models.Project).limit(5).all()
        ]

        metrics = {
            "stats": {
                "users": users_count,
                "projects": projects_count,
                "members": members_count,
                "agent_tasks": tasks_count,
            },
            "samples": {"users": users_sample, "projects": projects_sample},
            "timestamp": datetime.now().isoformat(),
        }

        # 2. Invocar al Orquestador GPT
        orchestrator = AgentOrchestrator()

        audit_prompt = f"""
        Realiza una AUDITORÍA FORENSE de las 'tuberías' (arquitectura de datos y flujo) del sistema MESH.
        Contexto actual:
        - Usuarios totales: {users_count} (Roles detectados: admin, pastor, lider, estudiante)
        - Proyectos activos: {projects_count}
        - Miembros en CRM: {members_count}
        - Tareas de Agentes: {tasks_count}
        
        Analiza posibles 'fugas' o inconsistencias basadas en que existen rutas duplicadas en el frontend 
        (/groups vs /community/groups) y evalúa si la base de datos refleja esta redundancia o si el 
        flujo de datos es íntegro. Propón 3 puntos críticos de mejora en la infraestructura.
        """

        print("🧠 Consultando al Cerebro Neuronal...")
        insight = orchestrator.run_diagnosis(summary=audit_prompt, metrics=metrics)

        print("\n🏆 RESULTADO DE LA AUDITORÍA FORENSE:")
        print("------------------------------------")
        print(insight.payload)
        print("------------------------------------")

        # 3. Persistir el hallazgo en el sistema
        crud.create_agent_insight(db, insight)
        print("\n✅ Auditoría persistida en la base de datos de MESH.")

    except Exception as e:
        print(f"❌ Error durante la auditoría: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    perform_forensic_audit()
