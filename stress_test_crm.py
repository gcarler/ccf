import time
import concurrent.futures
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend import models, crud, schemas
import random
import uuid

# Configuración del motor para la prueba
db_url = 'sqlite:///d:/ccf/ccf_v2.db'
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

def simulate_pastoral_action(member_id):
    """Simula una ráfaga de acciones para un miembro específico."""
    db = SessionLocal()
    try:
        # 1. Registro de Comunicación (WhatsApp)
        log = models.CommunicationLog(
            member_id=member_id,
            channel="WhatsApp",
            content=f"Mensaje de prueba de estrés {uuid.uuid4().hex[:8]}",
            outcome="sent"
        )
        db.add(log)
        
        # 2. Actualización de Salud Espiritual (Simulada via Note)
        member = db.query(models.Member).filter(models.Member.id == member_id).first()
        if member:
            member.pastoral_notes = f"Auto-audit completed at {time.ctime()}"
            
        # 3. Donación masiva
        if random.random() > 0.7:
            donation = models.Donation(
                member_id=member_id,
                amount=float(random.randint(50, 500)),
                donation_type="Diezmo",
                donor_name=f"{member.first_name} {member.last_name}" if member else "Donor Stress"
            )
            db.add(donation)
            
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error en acción para miembro {member_id}: {e}")
        return False
    finally:
        db.close()

def run_stress_test():
    print("🚀 Iniciando PRUEBA DE ESTRÉS INDUSTRIAL - CRM CCF v3.9")
    print("Objetivo: 600 operaciones concurrentes (Mensajería + Finanzas + Notas)")
    
    # Obtener IDs de miembros
    db = SessionLocal()
    member_ids = [m.id for m in db.query(models.Member).limit(600).all()]
    db.close()
    
    if not member_ids:
        print("❌ No hay miembros suficientes para la prueba.")
        return

    start_time = time.time()
    
    # Ejecución concurrente usando hilos para simular ráfagas de API
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(simulate_pastoral_action, member_ids))
    
    end_time = time.time()
    total_time = end_time - start_time
    success_count = results.count(True)
    
    print("\n" + "="*50)
    print("📊 RESULTADOS DEL REPORTE DE ESTRÉS")
    print("="*50)
    print(f"Total de Operaciones Intentadas: {len(member_ids)}")
    print(f"Operaciones Exitosas:           {success_count}")
    print(f"Tiempo Total:                   {total_time:.2f} segundos")
    print(f"Velocidad de Procesamiento:     {len(member_ids)/total_time:.2f} ops/seg")
    print(f"Estado de la Base de Datos:     {'SALUDABLE' if success_count == len(member_ids) else 'REVISAR INTEGRIDAD'}")
    print("="*50)

if __name__ == "__main__":
    run_stress_test()
