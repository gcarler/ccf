from __future__ import annotations

import io
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Setup project root in sys.path
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next((p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()), None)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Load models to ensure all SQLAlchemy mappers are properly registered
from backend import models
from backend.core.database import SessionLocal
from backend.core.storage import storage_service
from backend.models_auth import Usuario
from backend.models_crm import Persona
from backend.models_projects import (
    Project,
    ProjectActivityLog,
    ProjectAttachment,
    ProjectAutomationRule,
    ProjectBaseline,
    ProjectChangeRequest,
    ProjectComment,
    ProjectComponent,
    ProjectDocument,
    ProjectDodAcceptance,
    ProjectExpense,
    ProjectFile,
    ProjectIndicator,
    ProjectIndicatorRecord,
    ProjectKPI,
    ProjectLifecycle,
    ProjectMember,
    ProjectMilestone,
    ProjectPhase,
    ProjectRisk,
    ProjectStakeholder,
    ProjectTask,
    ProjectTaskDependency,
    ProjectTimeLog,
    ProjectWhiteboard,
    TaskSupply,
)
from backend.models import Sede

# ReportLab for real PDF generation
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_styled_pdf(title: str, subtitle: str, paragraphs: list[str]) -> bytes:
    """Generates a genuine, beautifully styled multi-page PDF document."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Header brand banner
    c.setFillColor(HexColor("#0284c7"))  # CCF Brand Primary
    c.rect(0, height - 80, width, 80, fill=1, stroke=0)

    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 42, "COMUNIDAD CRISTIANA EL FARO — PLATAFORMA CCF")

    c.setFont("Helvetica", 11)
    c.drawString(50, height - 62, "Módulo de Proyectos • Documentación Oficial de Ingeniería")

    # Document Title
    y = height - 120
    c.setFillColor(HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, title)

    y -= 22
    c.setFillColor(HexColor("#64748b"))
    c.setFont("Helvetica-Oblique", 11)
    c.drawString(50, y, subtitle)

    y -= 15
    c.setStrokeColor(HexColor("#cbd5e1"))
    c.setLineWidth(1)
    c.line(50, y, width - 50, y)

    # Content paragraphs
    y -= 25
    c.setFillColor(HexColor("#334155"))
    c.setFont("Helvetica", 10)

    for p in paragraphs:
        # Simple word-wrap
        words = p.split()
        line = ""
        for word in words:
            test_line = f"{line} {word}".strip()
            if c.stringWidth(test_line, "Helvetica", 10) < (width - 100):
                line = test_line
            else:
                c.drawString(50, y, line)
                y -= 15
                line = word
                if y < 60:
                    c.showPage()
                    y = height - 60
                    c.setFont("Helvetica", 10)
        if line:
            c.drawString(50, y, line)
            y -= 22
            if y < 60:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 10)

    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor("#94a3b8"))
    c.drawString(50, 30, f"Generado automáticamente por Plataforma CCF • Fecha: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    c.drawRightString(width - 50, 30, "Página 1 de 1")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def seed_showcase_project() -> dict:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        print("Iniciando creación de proyecto de prueba integral CCF...")

        # 1. Resolve Sede Matriz
        sede = db.query(Sede).filter(Sede.nombre.ilike("%Matriz%")).first()
        if not sede:
            sede = db.query(Sede).first()
        if not sede:
            raise RuntimeError("No se encontró ninguna sede en la base de datos.")
        sede_id = sede.id
        print(f"Sede asignada: {sede.nombre} ({sede_id})")

        # 2. Resolve Key Personas
        personas = db.query(Persona).limit(10).all()
        if len(personas) < 4:
            raise RuntimeError("Se requieren al menos 4 personas en la base de datos para armar el equipo.")

        p_owner = personas[0]      # Lucas Barrio u owner principal
        p_tech = personas[1]       # Líder Técnico
        p_prod = personas[2]       # Coordinadora Producción
        p_audio = personas[3]      # Especialista Audio
        p_sponsor = personas[0]    # Sponsor institucional

        print(f"Equipo seleccionado:")
        print(f"  Owner / Director: {p_owner.nombre_completo or p_owner.nombres} ({p_owner.id})")
        print(f"  Líder Técnico: {p_tech.nombre_completo or p_tech.nombres} ({p_tech.id})")
        print(f"  Coord. Producción: {p_prod.nombre_completo or p_prod.nombres} ({p_prod.id})")
        print(f"  Espec. Audio: {p_audio.nombre_completo or p_audio.nombres} ({p_audio.id})")

        # 3. Clean any existing showcase project with same title (idempotency)
        showcase_title = "Campus Virtual y Streaming 4K — Sedes CCF"
        existing = db.query(Project).filter(Project.title == showcase_title).all()
        for old_p in existing:
            print(f"Eliminando versión anterior del proyecto showcase ({old_p.id})...")
            # Backrefs sin cascade: se eliminan explícitamente (solo datos del showcase).
            db.query(ProjectDodAcceptance).filter(ProjectDodAcceptance.project_id == old_p.id).delete(synchronize_session=False)
            db.query(ProjectChangeRequest).filter(ProjectChangeRequest.project_id == old_p.id).delete(synchronize_session=False)
            db.expire_all()
            db.delete(db.get(Project, old_p.id))
        db.commit()

        # 4. Create Project
        start_date = now - timedelta(days=20)
        target_date = now + timedelta(days=50)

        project = Project(
            id=uuid.uuid4(),
            sede_id=sede_id,
            title=showcase_title,
            description=(
                "Modernización de la infraestructura audiovisual, centro de medios, plataforma de streaming 4K "
                "y transmisión interactiva para todas las sedes de Comunidad Cristiana El Faro. Proyecto integral "
                "diseñado para certificar y verificar el 100% de las herramientas del módulo de proyectos CCF."
            ),
            status="active",
            owner_id=p_owner.id,
            color="#0284c7",
            icon="Radio",
            start_date=start_date,
            target_date=target_date,
            progress_mode="auto_tasks",
            manual_progress=0.0,
            budget_allocated=25000000.0,
            budget_spent=16750000.0,
            contingency_reserve=2500000.0,
            management_reserve=2500000.0,
            management_reserve_pct=10.0,
            created_at=start_date,
            updated_at=now,
        )
        db.add(project)
        db.flush()
        print(f"✓ Proyecto creado con ID: {project.id}")

        # 5. Project Lifecycle (PMI Project Charter & Governance)
        lifecycle = ProjectLifecycle(
            id=uuid.uuid4(),
            project_id=project.id,
            sponsor_id=p_sponsor.id,
            business_case=(
                "La rápida expansión multi-sede de CCF requiere transmisiones de alta fidelidad con latencia "
                "menor a 1.5s y soporte para más de 10,000 conexiones concurrentes entre sedes físicas y campus online."
            ),
            strategic_justification=(
                "Alineado con el Plan Estratégico Ministerial CCF 2026 para unificar la experiencia dominical y formativa."
            ),
            measurable_objectives=[
                "Uptime de streaming dominical >= 99.8%",
                "Latencia inter-sedes <= 1.5 segundos",
                "Capacitación de voluntarios: 100% del equipo operativo evaluado",
            ],
            key_assumptions=[
                "Disponibilidad de ancho de banda simétrico de 500Mbps por sede",
                "Disponibilidad de equipo técnico voluntario capacitado",
            ],
            key_constraints=[
                "Presupuesto límite cerrado de $25,000,000 COP",
                "Entrega final antes del Congreso Anual del 15 de Diciembre",
            ],
            high_level_risks=[
                "Retrasos en aduana de switchers 4K (severidad alta)",
                "Interrupciones de energía en sede sur (severidad media)",
            ],
            preliminary_budget=25000000.0,
            development_approach="hybrid",
            pmo_type="controlling",
            charter_status="authorized",
            authorized_by=p_sponsor.id,
            authorized_at=start_date,
            closure_status="open",
            created_at=start_date,
            updated_at=now,
        )
        db.add(lifecycle)

        # 6. Stakeholders Register (Matriz Poder vs Interés)
        stakeholders_data = [
            ("Pastor General CCF", "Liderazgo Pastoral", "Pastoral Principal", 5, 5, "manage_closely", "supportive"),
            ("Director de Comunicaciones", "Dirección de Medios", "Comunicaciones CCF", 4, 3, "keep_satisfied", "supportive"),
            ("Líder de Transmisión Sede Sur", "Operador de Sede", "Ministerio de Transmisión", 2, 5, "keep_informed", "leading"),
            ("Equipo de Voluntarios Audiovisuales", "Operadores de Cámara", "Voluntariado CCF", 2, 2, "monitor", "neutral"),
        ]
        for name, role, org, pwr, itst, quad, eng in stakeholders_data:
            stk = ProjectStakeholder(
                id=uuid.uuid4(),
                project_id=project.id,
                persona_id=p_owner.id if "Pastor" in name else p_tech.id,
                display_name=name,
                role_title=role,
                organization_or_ministry=org,
                power_level=pwr,
                interest_level=itst,
                quadrant=quad,
                engagement_level=eng,
                management_strategy=f"Estrategia de comunicación personalizada para {name} según cuadrante {quad}.",
                created_at=start_date,
            )
            db.add(stk)

        # 7. Project Phases
        phases_specs = [
            ("Fase 1: Diagnóstico e Ingeniería", "fase-1-diag", "#3b82f6", 0, start_date, start_date + timedelta(days=12)),
            ("Fase 2: Adquisición e Instalación", "fase-2-inst", "#8b5cf6", 1, start_date + timedelta(days=13), start_date + timedelta(days=32)),
            ("Fase 3: Pruebas y Certificación 4K", "fase-3-test", "#f59e0b", 2, start_date + timedelta(days=33), start_date + timedelta(days=48)),
            ("Fase 4: Puesta en Producción y Cierre", "fase-4-prod", "#10b981", 3, start_date + timedelta(days=49), target_date),
        ]
        phases: dict[str, ProjectPhase] = {}
        for pname, pslug, pcolor, porder, psdate, pedate in phases_specs:
            phase = ProjectPhase(
                id=uuid.uuid4(),
                project_id=project.id,
                name=pname,
                slug=pslug,
                color=pcolor,
                order_index=porder,
                start_date=psdate,
                end_date=pedate,
            )
            db.add(phase)
            phases[pslug] = phase
        db.flush()

        # 8. Components (WBS / EDT Nivel 2 — 100% Budget Rule: Sum = $25,000,000)
        components_specs = [
            ("COMP-01", "Infraestructura de Red y Servidores", "Equipamiento de fibra óptica, routers MikroTik 10G y switches gestionados.", 8000000.0, 0, "#3b82f6"),
            ("COMP-02", "Equipamiento Audiovisual y Switchers 4K", "Switchers Blackmagic ATEM 4K, cámaras PTZ y cableado SDI Belden.", 12000000.0, 1, "#8b5cf6"),
            ("COMP-03", "Capacitación, Pruebas y Certificación", "Talleres a voluntarios, pruebas de carga con CDN y transmisión inaugural.", 5000000.0, 2, "#10b981"),
        ]
        components: dict[str, ProjectComponent] = {}
        for ccode, cname, cdesc, cbudget, corder, ccolor in components_specs:
            comp = ProjectComponent(
                id=uuid.uuid4(),
                project_id=project.id,
                code=ccode,
                name=cname,
                description=cdesc,
                budget_allocated=cbudget,
                order_index=corder,
                color=ccolor,
                status="active",
                created_at=start_date,
            )
            db.add(comp)
            components[ccode] = comp
        db.flush()

        # 9. Milestones
        milestones_specs = [
            ("Aprobación de Arquitectura de Red y Topología", "Aprobación formal del diagrama de red", start_date + timedelta(days=10), True),
            ("Llegada e Instalación de Switchers y Cámaras 4K", "Equipos recibidos en aduana e instalados en cabina", start_date + timedelta(days=28), True),
            ("Primera Transmisión Piloto Inter-Sedes", "Ensayo general con audio Dante y video SDI", start_date + timedelta(days=42), False),
            ("Lanzamiento Oficial en Congreso Ministerial", "Servicio dominical inaugural en 4K", target_date - timedelta(days=5), False),
        ]
        for mtitle, mdesc, mtdate, mdone in milestones_specs:
            db.add(
                ProjectMilestone(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    title=mtitle,
                    description=mdesc,
                    target_date=mtdate,
                    is_completed=mdone,
                    created_at=start_date,
                )
            )

        # 10. Project Members (Team)
        team_specs = [
            (p_owner.id, "director"),
            (p_tech.id, "lead_engineer"),
            (p_prod.id, "audiovisual_producer"),
            (p_audio.id, "audio_engineer"),
        ]
        for pid, prole in team_specs:
            db.add(
                ProjectMember(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    persona_id=pid,
                    role=prole,
                    invited_at=start_date,
                )
            )

        # 11. Tasks (WBS Nivel 3 + Subtasks)
        # We define a clear DAG structure for React Flow and Gantt
        tasks: dict[str, ProjectTask] = {}

        # Task 1: Requerimientos de red (Completed)
        t1 = ProjectTask(
            id=uuid.uuid4(),
            project_id=project.id,
            component_id=components["COMP-01"].id,
            order_index=0,
            title="Levantamiento de requerimientos de ancho de banda y cableado estructurado",
            description="Inspección en sitio del ancho de banda simétrico y puntos de red en Sede Matriz y Sede Sur.",
            status="completed",
            priority="high",
            assignee_id=p_tech.id,
            start_date=start_date,
            due_date=start_date + timedelta(days=8),
            physical_progress_pct=100.0,
            estimated_hours=16.0,
            labels=["redes", "infraestructura", "alta_prioridad"],
            created_at=start_date,
        )
        db.add(t1)
        tasks["t1"] = t1

        # Task 2: Configuración VLANs (In Progress)
        t2 = ProjectTask(
            id=uuid.uuid4(),
            project_id=project.id,
            component_id=components["COMP-01"].id,
            order_index=1,
            title="Configuración de routers MikroTik y VLANs dedicadas de streaming y audio Dante",
            description="Configuración de QoS en puertos troncales y aislamiento de tráfico de asistentes del canal de broadcast.",
            status="in_progress",
            priority="urgent",
            assignee_id=p_tech.id,
            start_date=start_date + timedelta(days=9),
            due_date=start_date + timedelta(days=22),
            physical_progress_pct=65.0,
            estimated_hours=24.0,
            labels=["mikrotik", "qos", "dante"],
            created_at=start_date + timedelta(days=8),
        )
        db.add(t2)
        tasks["t2"] = t2

        # Task 3: Adquisición de Switchers (Completed)
        t3 = ProjectTask(
            id=uuid.uuid4(),
            project_id=project.id,
            component_id=components["COMP-02"].id,
            order_index=2,
            title="Adquisición e importación de switchers Blackmagic ATEM SDI Pro ISO 4K",
            description="Compra corporativa con proveedor autorizado, trámite aduanero y póliza de garantía extendida.",
            status="completed",
            priority="urgent",
            assignee_id=p_prod.id,
            start_date=start_date + timedelta(days=5),
            due_date=start_date + timedelta(days=20),
            physical_progress_pct=100.0,
            estimated_hours=20.0,
            labels=["equipamiento", "blackmagic", "4k"],
            created_at=start_date + timedelta(days=4),
        )
        db.add(t3)
        tasks["t3"] = t3

        # Task 4: Calibración cámaras PTZ (In Progress)
        t4 = ProjectTask(
            id=uuid.uuid4(),
            project_id=project.id,
            component_id=components["COMP-02"].id,
            order_index=3,
            title="Instalación y calibración de cámaras robóticas PTZ 4K y enlace SDI",
            description="Montaje en truss principal, conexión de cableado Belden 1694A y programación de presets del controlador.",
            status="in_progress",
            priority="high",
            assignee_id=p_prod.id,
            start_date=start_date + timedelta(days=21),
            due_date=start_date + timedelta(days=32),
            physical_progress_pct=40.0,
            estimated_hours=30.0,
            labels=["ptz", "calibracion", "hardware"],
            created_at=start_date + timedelta(days=20),
        )
        db.add(t4)
        tasks["t4"] = t4

        # Subtask 4.1
        t4_sub1 = ProjectTask(
            id=uuid.uuid4(),
            project_id=project.id,
            parent_id=t4.id,
            component_id=components["COMP-02"].id,
            order_index=0,
            title="Tendido y conectorización de cableado SDI Belden en auditorio norte",
            description="Tirada de 120 metros con conectores BNC Neutrik crimpados a 12G-SDI.",
            status="completed",
            priority="high",
            assignee_id=p_tech.id,
            start_date=start_date + timedelta(days=21),
            due_date=start_date + timedelta(days=25),
            physical_progress_pct=100.0,
            estimated_hours=12.0,
            labels=["cableado", "sdi"],
            created_at=start_date + timedelta(days=20),
        )
        db.add(t4_sub1)

        # Subtask 4.2
        t4_sub2 = ProjectTask(
            id=uuid.uuid4(),
            project_id=project.id,
            parent_id=t4.id,
            component_id=components["COMP-02"].id,
            order_index=1,
            title="Ajuste de balance de blancos, shutter y presets de enfoque en auditorio",
            description="Calibración con carta de color Datacolor a 4500K para iluminación del escenario.",
            status="in_progress",
            priority="medium",
            assignee_id=p_prod.id,
            start_date=start_date + timedelta(days=26),
            due_date=start_date + timedelta(days=32),
            physical_progress_pct=30.0,
            estimated_hours=10.0,
            labels=["color", "calibracion"],
            created_at=start_date + timedelta(days=25),
        )
        db.add(t4_sub2)

        # Task 5: Taller Voluntarios (Todo)
        t5 = ProjectTask(
            id=uuid.uuid4(),
            project_id=project.id,
            component_id=components["COMP-03"].id,
            order_index=4,
            title="Taller de capacitación intensiva para operadores de switcher y cámaras",
            description="Entrenamiento práctico en vivo con simulación de contingencias y transiciones dominicales.",
            status="todo",
            priority="medium",
            assignee_id=p_audio.id,
            start_date=start_date + timedelta(days=33),
            due_date=start_date + timedelta(days=40),
            physical_progress_pct=0.0,
            estimated_hours=16.0,
            labels=["capacitacion", "voluntarios"],
            created_at=start_date + timedelta(days=30),
        )
        db.add(t5)
        tasks["t5"] = t5

        # Task 6: Prueba de Estrés CDN (Todo)
        t6 = ProjectTask(
            id=uuid.uuid4(),
            project_id=project.id,
            component_id=components["COMP-03"].id,
            order_index=5,
            title="Prueba de estrés de streaming 4K con simulación de 1,500 conexiones concurrentes",
            description="Simulación distribuida con Cloudflare Stream y CDN para medir bitrate sostenido y buffer health.",
            status="todo",
            priority="urgent",
            assignee_id=p_tech.id,
            start_date=start_date + timedelta(days=38),
            due_date=start_date + timedelta(days=45),
            physical_progress_pct=0.0,
            estimated_hours=20.0,
            labels=["pruebas", "cdn", "rendimiento"],
            created_at=start_date + timedelta(days=32),
        )
        db.add(t6)
        tasks["t6"] = t6

        # Task 7: Transmisión Inaugural (Todo)
        t7 = ProjectTask(
            id=uuid.uuid4(),
            project_id=project.id,
            component_id=components["COMP-03"].id,
            order_index=6,
            title="Transmisión oficial del servicio inaugural y monitoreo de telemetría",
            description="Servicio central dominical con transmisión interactiva, monitoreo en tiempo real y acta de cierre.",
            status="todo",
            priority="urgent",
            assignee_id=p_owner.id,
            start_date=start_date + timedelta(days=46),
            due_date=start_date + timedelta(days=50),
            physical_progress_pct=0.0,
            estimated_hours=12.0,
            labels=["produccion", "inaugural", "transmision"],
            created_at=start_date + timedelta(days=35),
        )
        db.add(t7)
        tasks["t7"] = t7

        db.flush()

        # 12. Task Dependencies (DAG for Flow Diagram / Gantt / Critical Path)
        dependencies_specs = [
            ("t1", "t2", "FS", 0),  # Redes -> VLANs
            ("t3", "t4", "FS", 1),  # Compra Switchers -> Calibración Cámaras
            ("t2", "t6", "FS", 2),  # VLANs -> Prueba Estrés CDN
            ("t4", "t5", "FS", 0),  # Cámaras Calibradas -> Taller Voluntarios
            ("t5", "t7", "FS", 1),  # Voluntarios Capacitados -> Transmisión Inaugural
            ("t6", "t7", "FS", 0),  # Prueba Estrés -> Transmisión Inaugural
        ]
        for pred_k, succ_k, dep_type, lag in dependencies_specs:
            dep = ProjectTaskDependency(
                id=uuid.uuid4(),
                project_id=project.id,
                predecessor_id=tasks[pred_k].id,
                successor_id=tasks[succ_k].id,
                dependency_type=dep_type,
                lag_days=lag,
                created_at=start_date,
            )
            db.add(dep)

        # 13. Task Supplies & Materials
        supplies_specs = [
            (tasks["t3"].id, "Switcher Blackmagic ATEM Television Studio 4K", 2, 4500000.0, 9000000.0, "approved"),
            (tasks["t4"].id, "Bobina 100m Cable Coaxial SDI Belden 1694A RG6", 3, 650000.0, 1950000.0, "approved"),
            (tasks["t2"].id, "Router Mikrotik Cloud Router Switch CRS326 10G", 2, 1800000.0, 3600000.0, "approved"),
            (tasks["t4"].id, "Kit Conectores BNC Neutrik 12G-SDI Crimp (Pack x20)", 4, 150000.0, 600000.0, "approved"),
            (tasks["t5"].id, "Manuales impresos y refrigerios para taller", 25, 20000.0, 500000.0, "pending"),
        ]
        for tid, iname, qty, ucost, tcost, sstatus in supplies_specs:
            db.add(
                TaskSupply(
                    id=uuid.uuid4(),
                    task_id=tid,
                    item_name=iname,
                    quantity=qty,
                    unit_cost=ucost,
                    total_cost=tcost,
                    status=sstatus,
                )
            )

        # 14. Project Expenses (EVM / Finanzas)
        expenses_specs = [
            (components["COMP-02"].id, tasks["t3"].id, "equipment", "Adquisición 2 Switchers Blackmagic ATEM 4K (Factura FAC-2026-981)", 9000000.0, "paid", start_date + timedelta(days=15)),
            (components["COMP-01"].id, tasks["t2"].id, "network", "Routers MikroTik 10G y patch panels Panduit (Factura FAC-8821)", 3600000.0, "paid", start_date + timedelta(days=12)),
            (components["COMP-02"].id, tasks["t4"].id, "cables", "Cableado Belden 1694A y conectores Neutrik BNC (Factura FAC-7714)", 2550000.0, "paid", start_date + timedelta(days=22)),
            (components["COMP-03"].id, tasks["t6"].id, "software", "Suscripción CDN Cloudflare Stream y licencias vMix Pro 4K", 1600000.0, "paid", start_date + timedelta(days=25)),
        ]
        for cid, tid, cat, desc, amount, status, exp_date in expenses_specs:
            db.add(
                ProjectExpense(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    component_id=cid,
                    task_id=tid,
                    category=cat,
                    description=desc,
                    amount=amount,
                    date=exp_date,
                    status=status,
                    created_by=p_owner.id,
                    created_at=exp_date,
                )
            )

        # 15. Time Logs (Time Tracking)
        time_logs_specs = [
            (tasks["t1"].id, p_tech.id, 16.0, "Relevamiento de distancias de cableado y mapeo de patch panels en sede norte.", start_date + timedelta(days=4)),
            (tasks["t2"].id, p_tech.id, 18.0, "Configuración de switches y pruebas de ancho de banda VLAN de video.", start_date + timedelta(days=14)),
            (tasks["t3"].id, p_prod.id, 14.0, "Gestión de compra, desaduanaje e inventario físico de switchers 4K.", start_date + timedelta(days=16)),
            (tasks["t4"].id, p_prod.id, 12.0, "Instalación de cámaras PTZ y montaje en soportes de auditorio.", start_date + timedelta(days=24)),
            (tasks["t4"].id, p_audio.id, 8.0, "Sincronización de reloj maestro PTP y latencia de audio Dante.", start_date + timedelta(days=25)),
        ]
        for tid, per_id, hrs, desc, log_date in time_logs_specs:
            db.add(
                ProjectTimeLog(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    task_id=tid,
                    persona_id=per_id,
                    hours=hrs,
                    description=desc,
                    date=log_date,
                    is_billable=True,
                    created_at=log_date,
                )
            )

        # 16. Baseline (Línea Base para EVM y Curva S)
        baseline_snapshot = {
            "project_id": str(project.id),
            "planned_value_total": 25000000.0,
            "earned_value_current": 17800000.0,
            "actual_cost_current": 16750000.0,
            "cpi": 1.06,
            "spi": 1.02,
            "components": [
                {"code": "COMP-01", "pv": 8000000.0, "ev": 7200000.0, "ac": 3600000.0},
                {"code": "COMP-02", "pv": 12000000.0, "ev": 8600000.0, "ac": 11550000.0},
                {"code": "COMP-03", "pv": 5000000.0, "ev": 2000000.0, "ac": 1600000.0},
            ],
            "approved_at": start_date.isoformat(),
        }
        db.add(
            ProjectBaseline(
                id=uuid.uuid4(),
                project_id=project.id,
                name="Línea Base Inicial de Alcance, Costo y Tiempo (Aprobada CCB)",
                description="Línea base formal aprobada al inicio del proyecto para seguimiento de valor ganado EVM.",
                snapshot_data=baseline_snapshot,
                created_by=p_owner.id,
                created_at=start_date,
            )
        )

        # 17. DoD Acceptance Criteria (Definition of Done & Quality)
        db.add(
            ProjectDodAcceptance(
                id=uuid.uuid4(),
                project_id=project.id,
                task_id=tasks["t1"].id,
                specification_met=True,
                tests_no_critical_failures=True,
                evidence_archived=True,
                supervisor_sign_off=True,
                status="accepted",
                accepted_by=p_owner.id,
                accepted_at=start_date + timedelta(days=8),
                coq_classification="prevention",
                coq_amount=350000.0,
                sede_id=sede_id,
            )
        )
        db.add(
            ProjectDodAcceptance(
                id=uuid.uuid4(),
                project_id=project.id,
                task_id=tasks["t3"].id,
                specification_met=True,
                tests_no_critical_failures=True,
                evidence_archived=True,
                supervisor_sign_off=True,
                status="accepted",
                accepted_by=p_owner.id,
                accepted_at=start_date + timedelta(days=20),
                coq_classification="appraisal",
                coq_amount=200000.0,
                sede_id=sede_id,
            )
        )

        # 18. Comments & Discussion Messages (with Mentions & Pinned)
        c1 = ProjectComment(
            id=uuid.uuid4(),
            project_id=project.id,
            task_id=tasks["t2"].id,
            author_id=p_owner.id,
            content=(
                f"Excelente avance con el switch MikroTik. @{p_tech.nombre_completo or p_tech.nombres} recuerden "
                "que la VLAN 30 debe tener ancho de banda garantizado de 120Mbps sin compresión para el feed troncal."
            ),
            mentions=[str(p_tech.id)],
            is_pinned=True,
            pinned_at=start_date + timedelta(days=14),
            pinned_by=p_owner.id,
            created_at=start_date + timedelta(days=14),
        )
        db.add(c1)

        c2 = ProjectComment(
            id=uuid.uuid4(),
            project_id=project.id,
            task_id=tasks["t4"].id,
            author_id=p_prod.id,
            content=(
                "Las cámaras PTZ llegaron en perfecto estado. Ya probamos el control VISCA over IP con el joystick "
                "y la respuesta es inmediata (< 20ms). Adjuntamos el reporte de calibración."
            ),
            is_pinned=False,
            created_at=start_date + timedelta(days=23),
        )
        db.add(c2)

        # 19. Real PDF Generation & Project Files (Bóveda Documental / Drive / Attachments)
        pdf_arch_bytes = generate_styled_pdf(
            title="PLAN MAESTRO DE ARQUITECTURA DE STREAMING 4K",
            subtitle="Topología de Red, Protocolos Audiovisuales y Resiliencia Inter-Sedes",
            paragraphs=[
                "1. RESUMEN EJECUTIVO: El presente documento técnico detalla la arquitectura de distribución y difusión en Ultra Alta Definición (4K UHD) para Comunidad Cristiana El Faro. El objetivo primordial es interconectar la Sede Matriz Norte con Sede Sur y las sedes virtuales con cero latencia perceptible.",
                "2. TOPOLOGÍA DE RED Y PROTOCOLOS: Se implementa una red basada en fibra óptica oscura simétrica dedicada de 500Mbps. El protocolo de transporte primario entre salas de producción es SMPTE ST 2110 y NDI|HX3, complementado por enlaces físicos punto a punto mediante cableado coaxial 12G-SDI Belden 1694A.",
                "3. CONTROL DE CALIDAD Y OBSERVABILIDAD: Cada switcher Blackmagic ATEM Television Studio 4K cuenta con encoders ISO para grabación redundante en SSD NVMe. Se integra telemetría activa con Grafana y alertas push a la plataforma CCF ante cualquier fluctuación de framerate inferior a 59.94 fps.",
                "4. MATRIZ DE ASIGNACIÓN DE RECURSOS: Todo el equipamiento ha sido codificado bajo los estándares de inventario del Kernel de Bienes de Plataforma CCF y asignado a los roles autorizados en el acta de constitución.",
            ],
        )
        arch_url = storage_service.save_file(
            pdf_arch_bytes,
            "Plan_Maestro_Arquitectura_Streaming_4K_CCF.pdf",
            subfolder="projects/boveda",
        )

        pdf_manual_bytes = generate_styled_pdf(
            title="MANUAL DE PROCEDIMIENTOS OPERATIVOS EN VIVO",
            subtitle="Protocolo de Transmisión Dominical y Respuesta a Contingencias",
            paragraphs=[
                "1. PROTOCOLO PRE-SERVICIO (T-60 MINUTOS): Realizar verificación de sync Dante, comprobación de tally en cámaras PTZ 1 a 4, chequeo de retorno de audio en sala principal y ping continuo a servidores de CDN.",
                "2. PROCEDIMIENTO DURANTE LA TRANSMISIÓN: La dirección de cámaras debe apegarse al guión de iluminación y tiempos ministeriales. Transiciones suaves en cortes principales y mantenimiento de planos medios para oradores.",
                "3. CONTINGENCIAS Y FAILOVER: Ante una eventual caída del enlace de fibra primario, el router MikroTik activará la conmutación a enlace Starlink en menos de 3 segundos sin pérdida de sesión RTMP.",
            ],
        )
        manual_url = storage_service.save_file(
            pdf_manual_bytes,
            "Manual_Operativo_Transmision_CCF.pdf",
            subfolder="projects/boveda",
        )

        # Register in ProjectFiles (Bóveda Documental)
        file_arch = ProjectFile(
            id=uuid.uuid4(),
            project_id=project.id,
            name="Plan Maestro de Arquitectura de Streaming 4K",
            description="Especificación técnica de ingeniería, topología de red y cálculo de bitrate 4K.",
            category="ingenieria",
            file_source="local",
            file_url=arch_url,
            file_type="application/pdf",
            file_size=len(pdf_arch_bytes),
            phase_id=phases["fase-1-diag"].id,
            uploaded_by=p_owner.id,
            sede_id=sede_id,
            created_at=start_date + timedelta(days=2),
        )
        db.add(file_arch)

        file_manual = ProjectFile(
            id=uuid.uuid4(),
            project_id=project.id,
            name="Manual Operativo de Transmisión y Contingencias",
            description="Protocolo paso a paso para voluntarios y operadores de cabina dominical.",
            category="manuales",
            file_source="local",
            file_url=manual_url,
            file_type="application/pdf",
            file_size=len(pdf_manual_bytes),
            task_id=tasks["t5"].id,
            uploaded_by=p_prod.id,
            sede_id=sede_id,
            created_at=start_date + timedelta(days=28),
        )
        db.add(file_manual)

        # Register Cloud Google Drive Document
        file_drive = ProjectFile(
            id=uuid.uuid4(),
            project_id=project.id,
            name="Matriz de Presupuesto y Desglose Financiero (Google Sheets)",
            description="Hoja de cálculo en vivo vinculada con tesorería ministerial.",
            category="financiero",
            file_source="drive",
            file_url="https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit",
            drive_file_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            file_type="application/vnd.google-apps.spreadsheet",
            uploaded_by=p_owner.id,
            sede_id=sede_id,
            created_at=start_date + timedelta(days=5),
        )
        db.add(file_drive)

        # Register Task Attachments
        db.add(
            ProjectAttachment(
                id=uuid.uuid4(),
                task_id=tasks["t1"].id,
                filename="Plan_Maestro_Arquitectura_Streaming_4K_CCF.pdf",
                file_url=arch_url,
                file_type="application/pdf",
                file_size=len(pdf_arch_bytes),
                uploader_id=p_tech.id,
                created_at=start_date + timedelta(days=3),
            )
        )
        db.add(
            ProjectAttachment(
                id=uuid.uuid4(),
                task_id=tasks["t5"].id,
                filename="Manual_Operativo_Transmision_CCF.pdf",
                file_url=manual_url,
                file_type="application/pdf",
                file_size=len(pdf_manual_bytes),
                uploader_id=p_prod.id,
                created_at=start_date + timedelta(days=29),
            )
        )

        # 20. Advanced Indicators (CREMA / MGA Metodología General Ajustada)
        ind1 = ProjectIndicator(
            id=uuid.uuid4(),
            project_id=project.id,
            code="IND-STR-01",
            name="Porcentaje de Sedes CCF Transmitiendo en 4K con Cero Latencia",
            description="Mide la cobertura de la infraestructura 4K operativa en las sedes físicas principales.",
            level="PRODUCTO_PRINCIPAL",
            calculation_type="PORCENTAJE",
            unit_of_measure="% de sedes",
            baseline_value=0.0,
            target_value=100.0,
            current_value=50.0,
            frequency="quincenal",
            period_targets={
                "2026-Q4-P1": 25.0,
                "2026-Q4-P2": 50.0,
                "2026-Q4-P3": 75.0,
                "2026-Q4-P4": 100.0,
            },
            crema_score=94.0,
            crema_evaluation={
                "claro": {"score": 19, "rationale": "El enunciado define unívocamente la meta técnica de cobertura."},
                "relevante": {"score": 19, "rationale": "Mide directamente el entregable del proyecto."},
                "economico": {"score": 18, "rationale": "Se recolecta por telemetría automática sin costo adicional."},
                "medible": {"score": 19, "rationale": "Cálculo matemático directo sobre total de sedes auditadas."},
                "adecuado": {"score": 19, "rationale": "Permite tomar acciones correctivas antes de la clausura."},
                "execution_link": {
                    "component_id": str(components["COMP-02"].id),
                    "source_type": "component_sync",
                },
            },
            created_by=p_owner.id,
            sede_id=sede_id,
            created_at=start_date,
        )
        db.add(ind1)
        db.flush()

        # Indicator Progress Records
        db.add(
            ProjectIndicatorRecord(
                id=uuid.uuid4(),
                indicator_id=ind1.id,
                period="2026-Q4-P1",
                target_value=25.0,
                actual_value=25.0,
                spi=1.00,
                notes="Sede Norte - Matriz completamente instalada y transmitiendo feed piloto.",
                evidence_url=arch_url,
                reported_by=p_tech.id,
                reported_at=start_date + timedelta(days=15),
            )
        )
        db.add(
            ProjectIndicatorRecord(
                id=uuid.uuid4(),
                indicator_id=ind1.id,
                period="2026-Q4-P2",
                target_value=50.0,
                actual_value=50.0,
                spi=1.00,
                notes="Sede Sur conectada mediante enlace de fibra y router MikroTik 10G.",
                evidence_url=manual_url,
                reported_by=p_tech.id,
                reported_at=start_date + timedelta(days=28),
            )
        )

        # Operational KPIs
        db.add(
            ProjectKPI(
                id=uuid.uuid4(),
                project_id=project.id,
                title="Audiencia Concurrente en Transmisión",
                description="Número de espectadores simultáneos conectados a los campus online y sedes.",
                target_value=5000.0,
                current_value=3450.0,
                unit="espectadores",
                category="impact",
                due_date=target_date,
                created_at=start_date,
            )
        )
        db.add(
            ProjectKPI(
                id=uuid.uuid4(),
                project_id=project.id,
                title="Tasa de Estabilidad de Conexión (Zero Drop)",
                description="Porcentaje de paquetes de video entregados sin jitter ni pérdida.",
                target_value=99.8,
                current_value=99.6,
                unit="%",
                category="efficiency",
                due_date=target_date,
                created_at=start_date,
            )
        )

        # 21. Risk Matrix & Expected Monetary Value (EMV)
        risk_specs = [
            (
                "Falla en enlace primario de fibra óptica durante transmisión dominical",
                "tecnico",
                2,  # Probabilidad 2/5 (40%)
                5,  # Impacto 5/5
                10,
                "Contratación de enlace redundante satelital Starlink Business con failover automático.",
                "Conmutación en caliente en menos de 5 segundos con aviso automático al centro de medios.",
                40.0,
                4000000.0,  # $4M impacto -> EMV $1.6M
                "threat",
            ),
            (
                "Retraso en entrega aduanera de cables y conectores SDI especializados",
                "operativo",
                3,  # Probabilidad 3/5 (60%)
                3,  # Impacto 3/5
                9,
                "Adquisición temprana a proveedores con stock nacional en Bogotá.",
                "Uso de cableado coaxial estándar como bypass temporal.",
                60.0,
                1500000.0,  # $1.5M impacto -> EMV $900k
                "threat",
            ),
            (
                "Alianza estratégica de patrocinio para servidor CDN de alta velocidad",
                "financiero",
                3,  # Probabilidad 3/5 (60%)
                4,  # Impacto 4/5
                12,
                "Formalización de convenio con proveedor de conectividad cristiano internacional.",
                "Redirección de ahorros de CDN para adquisición de un tercer switcher 4K.",
                60.0,
                3000000.0,  # $3M ahorro potencial
                "opportunity",
            ),
        ]
        for r_title, r_cat, r_prob, r_imp, r_score, r_mit, r_cont, r_prob_pct, r_fimp, r_type in risk_specs:
            r = ProjectRisk(
                id=uuid.uuid4(),
                project_id=project.id,
                title=r_title,
                category=r_cat,
                probability=r_prob,
                impact=r_imp,
                severity_score=r_score,
                mitigation_plan=r_mit,
                contingency_plan=r_cont,
                owner_id=p_tech.id,
                status="active",
                risk_type=r_type,
                probability_pct=r_prob_pct,
                financial_impact=r_fimp,
                created_at=start_date,
            )
            db.add(r)

        # 22. Change Requests (CCB Governance)
        db.add(
            ProjectChangeRequest(
                id=uuid.uuid4(),
                project_id=project.id,
                title="CR-001: Adición de Protocolo NDI Bridge para Campus Online Remoto",
                justification=(
                    "Permite a los directores del campus virtual interactuar en vivo con la transmisión central "
                    "sin requerir enlaces SDI dedicados, reduciendo los costos de alquiler de satélite."
                ),
                change_type="scope",
                cost_impact_delta=850000.0,
                schedule_impact_days=2,
                scope_impact_summary="Incorporación de servidor gateway NDI Bridge y licencias de codificación.",
                status="approved",
                requested_by=p_tech.id,
                reviewed_by=p_owner.id,
                review_notes="Aprobado por el comité CCB. Alto retorno ministerial con impacto marginal en presupuesto.",
                reviewed_at=start_date + timedelta(days=18),
                sede_id=sede_id,
                created_at=start_date + timedelta(days=16),
            )
        )

        # 23. Project Whiteboard (Pizarra Visual)
        whiteboard_elements = [
            {"id": "node-1", "type": "rect", "x": 100, "y": 120, "width": 180, "height": 90, "label": "Auditorio Norte\n(Cámaras PTZ 4K)", "fill": "#e0f2fe", "stroke": "#0284c7"},
            {"id": "node-2", "type": "rect", "x": 380, "y": 120, "width": 190, "height": 90, "label": "Cabina Principal\n(Switcher ATEM 4K)", "fill": "#f3e8ff", "stroke": "#9333ea"},
            {"id": "node-3", "type": "rect", "x": 670, "y": 120, "width": 190, "height": 90, "label": "Core MikroTik 10G\n(Fibra + QoS Dante)", "fill": "#fef3c7", "stroke": "#d97706"},
            {"id": "node-4", "type": "rect", "x": 960, "y": 120, "width": 180, "height": 90, "label": "Sede Sur &\nCampus Online", "fill": "#dcfce7", "stroke": "#16a34a"},
            {"id": "edge-1", "type": "arrow", "from": "node-1", "to": "node-2", "label": "12G-SDI"},
            {"id": "edge-2", "type": "arrow", "from": "node-2", "to": "node-3", "label": "RTMP / NDI"},
            {"id": "edge-3", "type": "arrow", "from": "node-3", "to": "node-4", "label": "CDN 4K Ultra"},
        ]
        db.add(
            ProjectWhiteboard(
                id=uuid.uuid4(),
                project_id=project.id,
                title="Pizarra de Topología Audiovisual e Interconexión",
                elements_json=json.dumps(whiteboard_elements),
                created_at=start_date,
            )
        )

        # 24. Project Wiki / Technical Documentation
        wiki_content = f"""# Arquitectura y Guía Técnica: Streaming 4K CCF

Bienvenido a la documentación oficial del proyecto **{showcase_title}**.

---

## 1. Topología del Sistema
El sistema opera bajo un esquema híbrido de hardware y red gestionada:
- **Cámaras:** 4x Cámaras robóticas PTZ 4K con protocolo VISCA sobre IP.
- **Conmutación:** Switcher Blackmagic ATEM SDI Pro ISO 4K.
- **Audio:** Red Dante IP conectada a consola digital Behringer Wing con 32 canales a 48kHz / 24-bit.
- **Red:** Enlace simétrico de 500Mbps sobre router MikroTik Cloud Router Switch 10G con balanceo Starlink.

---

## 2. Mapa de Direccionamiento IP (VLAN 30 — Broadcast)
| Dispositivo | IP Estática | Máscara | Función |
| :--- | :--- | :--- | :--- |
| Gateway MikroTik | `192.168.30.1` | `/24` | Core Router y DNS |
| Switcher ATEM 4K | `192.168.30.10` | `/24` | Conmutador Central |
| Cámara PTZ 1 (Pastoral) | `192.168.30.21` | `/24` | Plano Principal Escenario |
| Cámara PTZ 2 (Banda) | `192.168.30.22` | `/24` | Plano Musical |
| Cámara PTZ 3 (Congregación) | `192.168.30.23` | `/24` | Reacción y Ambiente |
| Interfaz Dante Audio | `192.168.30.40` | `/24` | Canal Stereo Master |

---

## 3. Protocolos de Emergencia
1. **Pérdida de señal SDI:** Cambiar inmediatamente a cámara de respaldo mediante botón `CAM 4` en switcher.
2. **Caída de internet primario:** El failover opera en caliente a Starlink. Notificar a cabina sin detener el programa.
3. **Desincronización de audio:** Reiniciar el clock master desde el panel Dante Controller.
"""
        db.add(
            ProjectDocument(
                id=uuid.uuid4(),
                project_id=project.id,
                title="Wiki Técnica de Arquitectura y Operación",
                content=wiki_content,
                author_id=p_tech.id,
                created_at=start_date,
            )
        )

        # 25. Automation Rules
        db.add(
            ProjectAutomationRule(
                id=uuid.uuid4(),
                project_id=project.id,
                name="Notificar al Director cuando una tarea crítica se complete",
                description="Envía notificación interna cuando tareas con prioridad 'urgent' pasan a 'completed'.",
                trigger_event="task_completed",
                condition_data={"priority": "urgent"},
                action_type="send_notification",
                action_data={"recipient_role": "director", "channel": "inbox"},
                is_active=True,
                created_by=p_owner.id,
                sede_id=sede_id,
                created_at=start_date,
            )
        )
        db.add(
            ProjectAutomationRule(
                id=uuid.uuid4(),
                project_id=project.id,
                name="Auto-asignar etiqueta 'en_riesgo' ante retrasos en fecha límite",
                description="Si una tarea vence sin completarse, agrega automáticamente el tag 'en_riesgo'.",
                trigger_event="task_overdue",
                condition_data={},
                action_type="add_label",
                action_data={"label": "en_riesgo"},
                is_active=True,
                created_by=p_owner.id,
                sede_id=sede_id,
                created_at=start_date,
            )
        )

        # 26. Audit Activity Logs
        activities = [
            ("project_created", "Proyecto iniciado formalmente con aprobación de Acta de Constitución."),
            ("phase_started", "Fase 1: Diagnóstico e Ingeniería iniciada con relevamiento técnico."),
            ("task_completed", "Tarea 'Levantamiento de requerimientos' completada y validada con DoD."),
            ("expense_recorded", "Gasto de $9,000,000 COP registrado y pagado para switchers Blackmagic."),
            ("baseline_approved", "Línea Base inicial aprobada por el comité de control de cambios CCB."),
            ("file_uploaded", "Plan Maestro de Arquitectura y Manual Operativo en PDF subidos a Bóveda Documental."),
            ("indicator_recorded", "Avance de indicador IND-STR-01 registrado para Q4-P1 y Q4-P2 con SPI=1.0."),
        ]
        for atype, adesc in activities:
            db.add(
                ProjectActivityLog(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    persona_id=p_owner.id,
                    action_type=atype,
                    description=adesc,
                    created_at=start_date + timedelta(days=len(activities)),
                )
            )

        db.commit()
        print("\n==================================================================")
        print("🎉 PROYECTO SHOWCASE CREADO CON ÉXITO")
        print("==================================================================")
        print(f"ID del Proyecto:    {project.id}")
        print(f"Título:             {project.title}")
        print(f"Sede:               {sede.nombre} ({sede.id})")
        print(f"Ruta Frontend:      /plataforma/projects/{project.id}")
        print("------------------------------------------------------------------")
        print("HERRAMIENTAS POBLADAS Y CONFIGURADAS:")
        print("  ✓ Acta de Constitución (PMI Charter) & Gobernanza")
        print("  ✓ Registro de Interesados (Stakeholders 4 cuadrantes)")
        print("  ✓ 4 Fases con fechas y codificación visual")
        print("  ✓ 3 Componentes EDT Nivel 2 (Regla 100% Presupuestal)")
        print("  ✓ 4 Hitos clave")
        print("  ✓ 4 Miembros de equipo asignados")
        print("  ✓ 7 Tareas jerárquicas con subtareas, prioridades y estados")
        print("  ✓ 6 Conexiones de dependencias para Diagramas de Flujo (Flow) y Gantt")
        print("  ✓ 5 Insumos y materiales en tareas (Task Supplies)")
        print("  ✓ 4 Gastos registrados vinculados a EVM ($16.75M COP)")
        print("  ✓ 1 Línea Base aprobada con métricas CPI/SPI")
        print("  ✓ 5 Registros de horas reales (Time Tracking)")
        print("  ✓ 2 Criterios de Aceptación DoD y Costo de Calidad (CoQ)")
        print("  ✓ 2 Comentarios con menciones y comentario fijado (Pin)")
        print("  ✓ 2 Archivos PDF reales generados y subidos a Bóveda y Tareas")
        print("  ✓ 1 Enlace a Google Drive institucional")
        print("  ✓ 1 Indicador CREMA/MGA con 2 reportes de avance y SPI")
        print("  ✓ 2 KPIs operativos")
        print("  ✓ 3 Riesgos en Matriz con cálculo de EMV")
        print("  ✓ 1 Solicitud formal de cambio aprobada (CCB)")
        print("  ✓ 1 Pizarra (Whiteboard) con topología técnica")
        print("  ✓ 1 Wiki técnica completa en Markdown")
        print("  ✓ 2 Reglas de automatización activas")
        print("  ✓ 7 Entradas de auditoría en Activity Log")
        print("==================================================================")

        return {
            "project_id": str(project.id),
            "title": project.title,
            "sede_id": str(sede.id),
            "url": f"/plataforma/projects/{project.id}",
        }

    except Exception as e:
        db.rollback()
        print(f"ERROR creando el proyecto showcase: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_showcase_project()
