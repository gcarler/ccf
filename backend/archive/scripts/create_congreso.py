import datetime
import os
import sys

# Add root directory to path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend import models
from backend.core.database import SessionLocal


def get_or_create_user(db):
    user = db.query(models.User).filter_by(username="admin").first()
    if not user:
        user = db.query(models.User).first()
    return user

def main():
    db = SessionLocal()
    try:
        user = get_or_create_user(db)
        if not user:
            print("No user found. Please ensure there is at least one user in the DB.")
            return

        # 1. Create Project
        project = models.Project(
            title="Congreso de Damas 2026: Resplandecientes",
            description="Lema Bíblico: Isaías 60:1 ('Levántate, resplandece; porque ha venido tu luz...').\n\nCongreso integral para mujeres de la congregación e invitadas.",
            status="active",
            owner_id=user.id,
            color="rose",
            icon="Crown"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"Project created with ID: {project.id}")

        # Task definitions
        phases = [
            {
                "title": "Fase I: Alistamiento y Cimentación",
                "description": "Base legal, financiera y creativa del evento.",
                "start_date": datetime.date(2026, 5, 1),
                "due_date": datetime.date(2026, 6, 30),
                "subtasks": [
                    {"title": "Definición del presupuesto base", "desc": "Meta mínima de asistencia y costos operativos por persona. Responsable: Tesorería.", "due": datetime.date(2026, 5, 15)},
                    {"title": "Desarrollo de la identidad visual", "desc": "Logotipo oficial, paleta de colores y fuentes para redes. Responsable: Equipo Creativo.", "due": datetime.date(2026, 5, 20)},
                    {"title": "Finalización de cotizaciones hoteleras", "desc": "Presentar 3 opciones con capacidad de 100 a 200 personas. Responsable: Logística.", "due": datetime.date(2026, 5, 30)},
                    {"title": "Selección y reserva de transporte", "desc": "Comparar al menos 3 propuestas de buses de turismo. Responsable: Logística.", "due": datetime.date(2026, 6, 5)},
                    {"title": "Gestión de expositoras", "desc": "Contacto inicial, validación de agenda y pre-reserva de conferencistas. Responsable: Comité Espiritual.", "due": datetime.date(2026, 6, 15)},
                    {"title": "Lanzamiento oficial de preventa", "desc": "Precio especial de 'pronto pago'. Responsable: Comunicaciones.", "due": datetime.date(2026, 6, 25)}
                ]
            },
            {
                "title": "Fase II: Recaudación y Promoción",
                "description": "Generar liquidez para pagos anticipados y asegurar cupos.",
                "start_date": datetime.date(2026, 7, 1),
                "due_date": datetime.date(2026, 8, 31),
                "subtasks": [
                    {"title": "Bazar Gastronómico", "desc": "'Sabores con Propósito'. Actividad Pro-Fondos.", "due": datetime.date(2026, 7, 12)},
                    {"title": "Cierre precio preventa", "desc": "Fecha límite para el precio de preventa.", "due": datetime.date(2026, 7, 31)},
                    {"title": "Inicio inscripciones tarifa regular", "desc": "Inicia la tarifa regular de inscripción.", "due": datetime.date(2026, 8, 1)},
                    {"title": "Tarde de Té y Talentos", "desc": "Actividad Pro-Fondos.", "due": datetime.date(2026, 8, 2)},
                    {"title": "Pago de anticipos críticos", "desc": "30% al hotel y 20% al transporte para blindar la fecha.", "due": datetime.date(2026, 8, 15)}
                ]
            },
            {
                "title": "Fase III: Gestión Logística Crítica",
                "description": "Ajuste de detalles operativos y preparación de materiales.",
                "start_date": datetime.date(2026, 9, 1),
                "due_date": datetime.date(2026, 9, 30),
                "subtasks": [
                    {"title": "Cierre definitivo de inscripciones", "desc": "No se procesan más pagos para garantizar la logística de alimentación y hospedaje.", "due": datetime.date(2026, 9, 5)},
                    {"title": "Elaboración del listado final de habitaciones", "desc": "Organizando a las asistentes por grupos de afinidad o edad.", "due": datetime.date(2026, 9, 10)},
                    {"title": "Adquisición de suministros (kits)", "desc": "Bolsos, papelería, distintivos.", "due": datetime.date(2026, 9, 15)},
                    {"title": "Reunión general de voluntarios", "desc": "Capacitación en protocolo, ujieres y logística de emergencia.", "due": datetime.date(2026, 9, 20)},
                    {"title": "Ensamblaje final de kits", "desc": "Revisión de inventario logístico.", "due": datetime.date(2026, 9, 30)}
                ]
            },
            {
                "title": "Fase IV: Cronograma de Ejecución",
                "description": "El congreso en sí.",
                "start_date": datetime.date(2026, 10, 8),
                "due_date": datetime.date(2026, 10, 11),
                "subtasks": [
                    {"title": "Día 1: El Encuentro", "desc": "08am Salida, 12pm Arribo, 07pm Apertura 'Encendiendo la Llama'.", "due": datetime.date(2026, 10, 8)},
                    {"title": "Día 2: Sanidad y Restauración", "desc": "Plenaria 'Sanando las heridas del pasado', talleres, Noche de Ministración.", "due": datetime.date(2026, 10, 9)},
                    {"title": "Día 3: Empoderamiento", "desc": "Plenaria 'Mujer de Influencia', Gala de Clausura (Fiesta Blanca), Fogata.", "due": datetime.date(2026, 10, 10)},
                    {"title": "Día 4: El Envío", "desc": "Clausura 'Comisionadas para Brillar', Check-out, Retorno.", "due": datetime.date(2026, 10, 11)}
                ]
            },
            {
                "title": "Fase V: Post-Congreso",
                "description": "Cierre de cuentas y seguimiento pastoral.",
                "start_date": datetime.date(2026, 10, 12),
                "due_date": datetime.date(2026, 10, 30),
                "subtasks": [
                    {"title": "Recolección de feedback", "desc": "Encuestas digitales de satisfacción.", "due": datetime.date(2026, 10, 15)},
                    {"title": "Balance financiero", "desc": "Entrega del balance detallado a la junta directiva.", "due": datetime.date(2026, 10, 20)},
                    {"title": "Servicio especial de testimonios", "desc": "Socializar resultados espirituales en la iglesia.", "due": datetime.date(2026, 10, 25)},
                    {"title": "Cierre de ciclo", "desc": "Cartas de agradecimiento a patrocinadores y equipo de trabajo.", "due": datetime.date(2026, 10, 30)}
                ]
            }
        ]

        order_idx = 0
        for phase in phases:
            parent_task = models.ProjectTask(
                project_id=project.id,
                title=phase["title"],
                description=phase["description"],
                start_date=phase["start_date"],
                due_date=phase["due_date"],
                status="todo",
                priority="medium",
                order_index=order_idx,
                labels="Fase"
            )
            db.add(parent_task)
            db.commit()
            db.refresh(parent_task)
            order_idx += 100

            sub_order_idx = 0
            for sub in phase["subtasks"]:
                child_task = models.ProjectTask(
                    project_id=project.id,
                    parent_id=parent_task.id,
                    title=sub["title"],
                    description=sub["desc"],
                    due_date=sub["due"],
                    status="todo",
                    priority="high" if "crítico" in sub["title"].lower() or "cierre" in sub["title"].lower() else "medium",
                    order_index=sub_order_idx
                )
                db.add(child_task)
                sub_order_idx += 10
            
            db.commit()

        print("Project and all tasks successfully created!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
