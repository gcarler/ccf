
import sys
import os
import random
from datetime import datetime, timedelta
import uuid

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import models, schemas, crud
from backend.core.database import SessionLocal, engine, Base
from backend.core.security import get_password_hash

def seed_ultimate():
    print("💎 Iniciando INYECCIÓN MAESTRA DE DIVERSIDAD (Estado Real 100%)...")
    
    # Reset Físico para aplicar nuevos campos
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # --- INFRAESTRUCTURA ---
        print("🛠️ Roles, Niveles y Badges...")
        roles_db = [
            models.Role(name="admin", permissions={"all": True}),
            models.Role(name="docente", permissions={"academy": True}),
            models.Role(name="coordinador", permissions={"crm": True}),
            models.Role(name="estudiante", permissions={"academy": "read"})
        ]
        db.add_all(roles_db)
        db.commit()

        # --- CUERPO PASTORAL PRINCIPAL ---
        pwd = get_password_hash("admin123")
        
        def create_ministerial_user(first, last, email, role_name, username):
            u = models.User(username=username, email=email, password_hash=pwd, role="admin", xp=10000)
            db.add(u)
            db.commit()
            db.refresh(u)
            m = models.Member(first_name=first, last_name=last, email=email, church_role=role_name, is_baptized=True, spiritual_status="Servidor", user_id=u.id)
            db.add(m)
            db.commit()
            return m

        print("👥 Creando Liderazgo Superior...")
        pastor_luis = create_ministerial_user("LUIS RICARDO", "MEZA GUTIERREZ", "luis.meza@ccf.la", "Pastor Principal", "luis_meza")
        pastora_histar = create_ministerial_user("HISTAR", "ARIZA HERRERA", "histar.ariza@ccf.la", "Pastora Principal", "histar_ariza")
        
        # Otros Pastores
        pastor_alex = create_ministerial_user("ALEX", "CABARCAS", "alex.cabarcas@ccf.la", "Pastor", "alex_cabarcas")
        pastora_elivia = create_ministerial_user("ELIVIA", "ANGULO", "elivia.angulo@ccf.la", "Pastora", "elivia_angulo")
        pastor_camilo = create_ministerial_user("CAMILO", "PAJARO", "camilo.pajaro@ccf.la", "Pastor", "camilo_pajaro")
        pastora_alba = create_ministerial_user("ALBA", "ESTRADA", "alba.estrada@ccf.la", "Pastora", "alba_estrada")
        pastor_nehemias = create_ministerial_user("NEHEMIAS", "HERNANDEZ", "nehemias.hernandez@ccf.la", "Pastor", "nehemias_h")
        pastor_fernando = create_ministerial_user("FERNANDO", "HERNANDEZ", "fernando.hernandez@ccf.la", "Pastor", "fernando_h")

        # --- GENERACIÓN MASIVA DIVERSA ---
        print("👥 Generando 600 Miembros con diversidad de roles y estados...")
        apellidos = ["Rodríguez", "García", "Martínez", "López", "González", "Pérez", "Sánchez", "Castro", "Mendoza", "Vargas"]
        nombres = ["Juan", "Elena", "Carlos", "Sofía", "Ricardo", "María", "Mateo", "Lucía", "Andrés", "Valeria"]
        
        oficios = ["Profeta", "Maestro", "Evangelista", "Servidor", "Miembro", "Diácono"]
        pesos_oficios = [2, 5, 3, 20, 60, 10] # Porcentajes aprox
        
        estados_espirituales = ["Nuevo", "Creyente", "Discípulo", "Servidor"]
        
        miembros_lista = [pastor_luis, pastora_histar, pastor_alex, pastora_elivia, pastor_camilo, pastora_alba, pastor_nehemias, pastor_fernando]
        
        # 200 Familias
        familias_lista = []
        for i in range(200):
            fam = models.Family(name=f"Familia {random.choice(apellidos)} {i}")
            db.add(fam)
            familias_lista.append(fam)
        db.commit()

        for i in range(600):
            u_id = None
            email = f"persona{i}@ccf.la"
            # Asignar rol aleatorio
            rol_iglesia = random.choices(oficios, weights=pesos_oficios)[0]
            baptized = random.random() > 0.3 # 70% bautizados
            spiritual = random.choice(estados_espirituales)
            
            # Algunos tienen usuario (100 personas)
            if i < 100:
                u = models.User(username=f"user{i}", email=email, password_hash=pwd, role="estudiante", xp=random.randint(0, 500))
                db.add(u)
                db.commit()
                db.refresh(u)
                u_id = u.id
            
            m = models.Member(
                first_name=random.choice(nombres), 
                last_name=random.choice(apellidos),
                email=email, 
                family_id=random.choice(familias_lista).id,
                church_role=rol_iglesia, 
                is_baptized=baptized,
                spiritual_status=spiritual,
                user_id=u_id
            )
            db.add(m)
            miembros_lista.append(m)
            if i % 100 == 0: print(f"   ... {i} personas procesadas")
        
        db.commit()

        # --- ACADEMIA (LMS) ---
        print("📚 Cursos y diversidad de progreso...")
        c1 = models.Course(code="FUND-1", title="Fundamentos de la Fe", modality="formal")
        c2 = models.Course(code="MAESTRIA-1", title="Formación de Maestros", modality="formal")
        db.add_all([c1, c2])
        db.commit()
        db.refresh(c1)
        db.refresh(c2)
        
        l1 = models.Lesson(course_id=c1.id, title="La Gracia", content="Contenido...", order_index=1)
        db.add(l1)
        db.commit()
        db.refresh(l1)

        # Matricular solo a una parte (diversidad académica)
        usuarios_est = db.query(models.User).filter(models.User.role == "estudiante").all()
        # 40% están en Fundamentos, 10% en Maestría, 50% NO hacen curso aún
        print("🎓 Distribuyendo estudiantes en cursos...")
        for idx, u in enumerate(usuarios_est):
            if idx < 40: # Fundamentos
                db.add(models.Enrollment(user_id=u.id, course_id=c1.id, status="active", progress_percent=random.randint(10, 90)))
            elif idx < 50: # Maestría (ya completaron algo)
                db.add(models.Enrollment(user_id=u.id, course_id=c2.id, status="completed", approved=True, progress_percent=100))
            # El resto se queda sin enrollment para probar filtros de "Sin Curso"
        
        db.commit()

        # --- CRM OTROS ---
        print("🏗️ Finalizando detalles de CRM...")
        db.add(models.Ministry(name="Enseñanza", description="Cuerpo de Maestros", leader_id=miembros_lista[0].id))
        db.add(models.Ministry(name="Profético", description="Cuerpo de Profetas", leader_id=miembros_lista[1].id))
        db.add(models.CrmEvent(title="Gran Bautismo", event_date=datetime.now() + timedelta(days=15), location="Sede Central"))
        
        db.commit()
        print("\n🏆 ¡OPERACIÓN EXITOSA! Diversidad ministerial inyectada.")
        print(f"   - Pastores Principales: Luis Meza e Histar Ariza")
        print(f"   - Población: 600 miembros con roles de Profeta, Maestro, Servidor, etc.")
        print(f"   - Estados: Bautizados y No Bautizados incluidos.")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_ultimate()
