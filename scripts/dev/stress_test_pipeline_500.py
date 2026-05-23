
import time
import random
import uuid
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from backend import models

# Configuración profesional del entorno de prueba
db_url = 'sqlite:///d:/ccf/ccf_v2.db'
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

def seed_pipeline_leads(count=500):
    """Inyecta 500 prospectos reales en el motor de consolidación corrigiendo los campos."""
    db = SessionLocal()
    print(f"📥 Sembrando {count} prospectos en el Pipeline...")
    start = time.time()
    
    stages = ['new', 'contacted', 'visited', 'integrated']
    sources = ['Noche de Milagros', 'Redes Sociales', 'Invitación Directa', 'Página Web']
    
    try:
        for i in range(count):
            lead = models.ConsolidationPipeline(
                first_name=f"Visitante_{uuid.uuid4().hex[:5]}",
                last_name=f"Apellido_{i}",
                phone=f"+57300{random.randint(1000000, 9999999)}",
                source=random.choice(sources),
                stage=random.choice(stages),
                notes=f"Interés en formación técnica y discipulado. Folio de estrés #{i}"
            )
            db.add(lead)
        
        db.commit()
        end = time.time()
        print(f"✅ Sembrado completado en {end - start:.2f}s")
    except Exception as e:
        db.rollback()
        print(f"❌ Error en el sembrado: {e}")
    finally:
        db.close()

def test_query_pressure():
    """Mide el rendimiento de la tubería bajo presión de 500+ registros."""
    db = SessionLocal()
    print("\n🔍 Midiendo presión de consulta masiva (Simulación Dashboard Pastor)...")
    
    start = time.time()
    
    # 1. Conteo por etapas (Dashboard)
    pipeline_stats = db.query(
        models.ConsolidationPipeline.stage, 
        func.count(models.ConsolidationPipeline.id)
    ).group_by(models.ConsolidationPipeline.stage).all()
    
    # 2. Carga total para renderizado de Kanban
    leads = db.query(models.ConsolidationPipeline).all()
    
    end = time.time()
    duration = end - start
    
    print("="*50)
    print("📊 REPORTE DE PRESIÓN HIDRÁULICA (DATOS)")
    print("="*50)
    print(f"Registros en Pipeline: {len(leads)}")
    print(f"Tiempo de Respuesta:  {duration*1000:.2f} ms")
    print(f"Eficiencia de Índices: {'ÓPTIMA (< 100ms)' if duration < 0.1 else 'REVISAR FRAGMENTACIÓN'}")
    
    for stage, count in pipeline_stats:
        print(f" - Etapa {stage:12}: {count} leads")
    print("="*50)
    db.close()

if __name__ == "__main__":
    seed_pipeline_leads(500)
    test_query_pressure()
