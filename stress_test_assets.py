import time
import concurrent.futures
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend import models
import random
import uuid

# Configuración del motor
db_url = 'sqlite:///d:/ccf/ccf_v2.db'
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

def simulate_file_upload(i):
    """Simula la subida de un archivo y registro de metadatos."""
    db = SessionLocal()
    try:
        # Generar metadatos de archivo simulados
        filename = f"recurso_pastoral_{uuid.uuid4().hex[:6]}.pdf"
        file_url = f"/uploads/academy/{filename}"
        
        asset = models.MediaAsset(
            filename=filename,
            url=file_url,
            mime_type="application/pdf",
            size_bytes=random.randint(1024, 1024*1024*5) # 1KB a 5MB
        )
        db.add(asset)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error en subida {i}: {e}")
        return False
    finally:
        db.close()

def run_asset_stress_test():
    print("📂 Iniciando PRUEBA DE CARGA MASIVA DE ARCHIVOS - CCF v3.9")
    print("Objetivo: 100 registros concurrentes de Media Assets (Metadatos)")
    
    start_time = time.time()
    
    # Ejecución concurrente
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(simulate_file_upload, range(100)))
    
    end_time = time.time()
    total_time = end_time - start_time
    success_count = results.count(True)
    
    print("\n" + "="*50)
    print("📊 RESULTADOS DEL REPORTE DE ARCHIVOS")
    print("="*50)
    print(f"Total de Archivos Registrados:  {success_count}")
    print(f"Tiempo Total de Procesamiento: {total_time:.2f} segundos")
    print(f"Velocidad de Escritura:        {success_count/total_time:.2f} archivos/seg")
    print(f"Integridad de Biblioteca:      {'SINCRONIZADA' if success_count == 100 else 'ERROR'}")
    print("="*50)

if __name__ == "__main__":
    run_asset_stress_test()
