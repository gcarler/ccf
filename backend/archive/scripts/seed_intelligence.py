import sqlite3
import json
import datetime as dt
import duckdb
from pathlib import Path

# Paths
SQLITE_DB = 'd:/ccf/ccf_v2.db'
DUCKDB_PATH = 'd:/ccf/analytics/warehouse.duckdb'

def seed_agent_data():
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    # Create tables if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR NOT NULL,
        description TEXT,
        status VARCHAR DEFAULT 'pending' NOT NULL,
        source VARCHAR NOT NULL,
        assignee VARCHAR,
        priority VARCHAR DEFAULT 'medium' NOT NULL,
        extra TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR NOT NULL,
        insight_type VARCHAR NOT NULL,
        payload TEXT NOT NULL,
        acknowledged BOOLEAN DEFAULT 0 NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Clean
    cursor.execute("DELETE FROM agent_tasks")
    cursor.execute("DELETE FROM agent_insights")
    
    tasks = [
        ("Optimizar Retenci??n Academia", "Se detect?? una ca??da del 15% en la finalizaci??n del M??dulo 2. Sugerido: Campa??a de recordatorio v??a WhatsApp.", "pending", "Intelligence Engine", "Pastoral Care", "high"),
        ("Auditor??a de Ofrendas", "Desviaci??n inusual detectada en la zona norte. Verificar registros manuales vs digitales.", "pending", "Financial Agent", "Admin Finance", "medium"),
        ("Bienvenida Autom??tica", "5 nuevos leads en etapa 'new' sin contacto por > 24h.", "pending", "CRM Agent", "Liderazgo Local", "high")
    ]
    
    cursor.executemany("""
        INSERT INTO agent_tasks (title, description, status, source, assignee, priority)
        VALUES (?, ?, ?, ?, ?, ?)
    """, tasks)
    
    insights = [
        ("Crecimiento Exponencial", "Growth", json.dumps({"metric": "Miembros", "increase": "22%", "period": "Feb-Mar"}), 0),
        ("Alerta de Deserci??n", "Retention", json.dumps({"impact": "M??dulo 2 Academia", "risk": "High", "recommendation": "Webinar de refuerzo"}), 0),
        ("Eficiencia Operativa", "Finance", json.dumps({"saving": "$450/mo", "insight": "Automatizaci??n de comprobantes completada"}), 0)
    ]
    
    cursor.executemany("""
        INSERT INTO agent_insights (title, insight_type, payload, acknowledged)
        VALUES (?, ?, ?, ?)
    """, insights)
    
    conn.commit()
    conn.close()
    print("??? SQLite Agent data seeded.")

def seed_analytics_data():
    Path('d:/ccf/analytics').mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(DUCKDB_PATH)
    
    conn.execute("DROP TABLE IF EXISTS domain_events")
    conn.execute("""
        CREATE TABLE domain_events (
            event_time TIMESTAMP,
            event_name TEXT,
            payload JSON
        )
    """)
    
    events = []
    now = dt.datetime.now(dt.timezone.utc)
    
    # Generate mock events for the last 30 days
    for i in range(100):
        days_ago = i % 30
        time = now - dt.timedelta(days=days_ago, hours=i%24)
        
        event_types = ['EnrollmentCreated', 'CertificateIssued', 'AssessmentSubmitted', 'UserRegistered', 'DonationCompletada']
        name = event_types[i % len(event_types)]
        
        payload = {"course_id": (i % 5) + 1}
        if name == 'AssessmentSubmitted':
            payload["passed"] = (i % 2 == 0)
        if name == 'DonationCompletada':
            payload["amount"] = 50 + (i * 10)
            
        events.append((time, name, json.dumps(payload)))
    
    conn.executemany("INSERT INTO domain_events VALUES (?, ?, ?)", events)
    conn.close()
    print("??? DuckDB Analytics data seeded.")

if __name__ == "__main__":
    seed_agent_data()
    seed_analytics_data()
    print("???? All Intelligence Content seeded 100%.")
