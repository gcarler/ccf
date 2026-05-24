from backend.core.database import SessionLocal
from backend.services.intelligence import IntelligenceMESH


def trigger_intelligence():
    db = SessionLocal()
    try:
        print("🧠 Iniciando Motores de Inteligencia MESH...")
        count = IntelligenceMESH.run_full_analysis(db)
        print(
            f"✅ Análisis completado. Se generaron/actualizaron {count} insights para los agentes."
        )
    except Exception as e:
        print(f"❌ Error en los motores de inteligencia: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    trigger_intelligence()
