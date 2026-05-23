import concurrent.futures
import random
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import models

# Configuración
db_url = "sqlite:///d:/ccf/ccf_v2.db"
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)


def simulate_qr_scan(member_id):
    """Simula la lógica de validación del endpoint /scanner/validate."""
    db = SessionLocal()
    start = time.time()
    try:
        # Simular búsqueda de miembro por ID extraído del QR
        member = db.query(models.Member).filter(models.Member.id == member_id).first()
        duration = time.time() - start
        return True, duration
    except Exception as e:
        print(f"Error: {e}")
        return False, 0
    finally:
        db.close()


def run_qr_test():
    print("📱 Iniciando PRUEBA DE VELOCIDAD: ESCÁNER QR - CCF v3.9")
    print("Objetivo: 50 escaneos concurrentes (Simulación de entrada a evento)")

    db = SessionLocal()
    member_ids = [m.id for m in db.query(models.Member).limit(50).all()]
    db.close()

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(simulate_qr_scan, member_ids))

    end_time = time.time()
    total_time = end_time - start_time
    success_count = sum(1 for r in results if r[0])
    avg_latency = sum(r[1] for r in results) / len(results)

    print("\n" + "=" * 50)
    print("📊 RESULTADOS DEL ESCÁNER")
    print("=" * 50)
    print(f"Escaneos Exitosos: {success_count}/50")
    print(f"Latencia Promedio: {avg_latency*1000:.2f} ms")
    print(f"Tiempo Total:      {total_time:.2f} segundos")
    print(f"Estado:            {'INSTANTÁNEO' if avg_latency < 0.1 else 'LENTO'}")
    print("=" * 50)


if __name__ == "__main__":
    run_qr_test()
