
import requests
import json

BASE_URL = "http://localhost:8000"

def create_admin_if_missing():
    print("👤 Asegurando existencia de usuario administrador...")
    payload = {
        "username": "admin_mesh_cii",
        "email": "admin.mesh@example.com",
        "password": "admin1234",
        "role": "admin"
    }
    response = requests.post(f"{BASE_URL}/users/", json=payload)
    if response.status_code == 200:
        print("✅ Usuario administrador creado.")
    elif response.status_code == 400:
        print("ℹ️ El usuario administrador ya existe.")
    else:
        print(f"⚠️ Nota sobre usuario: {response.text}")

def get_admin_token():
    print("🔑 Autenticando como administrador...")
    response = requests.post(f"{BASE_URL}/auth/login", data={
        "username": "admin.mesh@example.com",
        "password": "admin1234"
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Error de autenticación: {response.text}")
        return None

def register_organ(name, description, tools, inputs, outputs, token):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": name,
        "description": description,
        "version": "1.0.0",
        "tools_schema": json.dumps(tools),
        "input_metadata": json.dumps(inputs),
        "output_metadata": json.dumps(outputs)
    }
    response = requests.post(f"{BASE_URL}/mesh/register", json=payload, headers=headers)
    if response.status_code == 200:
        print(f"✅ Organ '{name}' encarnado con éxito.")
    else:
        print(f"❌ Error al encarnar '{name}': {response.text}")

# 1. Órgano de Reportes (Fórmula: Nodo, no Destino)
report_tools = [
    {
        "name": "generate_academic_report",
        "description": "Genera reportes de progreso para cursos formales o no formales.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {"type": "integer"},
                "format": {"type": "string", "enum": ["pdf", "csv"]}
            }
        }
    }
]

# 2. Órgano de Análisis (Sustento para Estrategia)
analysis_tools = [
    {
        "name": "analyze_retention_trends",
        "description": "Analiza tendencias de deserción basadas en logs de comunicación.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string"}
            }
        }
    }
]

if __name__ == "__main__":
    print("Iniciando 'CII' (Integración Continua de Inteligencia)...")
    create_admin_if_missing()
    token = get_admin_token()
    if not token:
        exit(1)
    
    # 1. LMS Coordinator
    register_organ(
        "lms-coordinator", 
        "Gestiona el ciclo de vida académico, incluyendo cursos, lecciones, inscripciones, evaluaciones y certificaciones.", 
        [
            {"name": "list_courses", "description": "Descubre la oferta formal y no formal."},
            {"name": "create_enrollment", "description": "Inscribe a un estudiante en un curso."},
            {"name": "close_acta", "description": "Cierre formal de cohorte para certificación masiva."}
        ], 
        {"requires": "user_id, course_id", "modality": "formal | no_formal"}, 
        {"provides": "enrollment_status, certificate_id"},
        token
    )
    
    # 2. CRM Manager
    register_organ(
        "crm-manager", 
        "Administra el ecosistema de comunidad, gestionando familias, miembros, asistencia a eventos y comunicaciones omnicanal.", 
        [
            {"name": "register_family", "description": "Crea un nuevo núcleo familiar."},
            {"name": "record_attendance", "description": "Registra asistencia a eventos del ecosistema."},
            {"name": "send_mesh_message", "description": "Envía comunicación omnicanal (WhatsApp/SMS/Email)."}
        ], 
        {"requires": "family_data, contact_info"}, 
        {"provides": "communication_log, attendance_metrics"},
        token
    )

    # 3. Reporting Engine
    register_organ(
        "reporting-engine", 
        "Nodo especializado en la generación de documentos y reportes estructurados a partir de datos académicos y de comunidad.", 
        [
            {"name": "generate_progress_report", "description": "Genera reporte de avance académico."},
            {"name": "export_member_data", "description": "Exporta datos de comunidad para auditoría."}
        ], 
        {"requires": "enrollment_data | member_data"}, 
        {"provides": "structured_report_file"},
        token
    )

    # 4. Analysis Brain
    register_organ(
        "analysis-brain", 
        "Nodo de inteligencia estratégica que analiza tendencias, retención y desempeño para sugerir optimizaciones en el ecosistema.", 
        [
            {"name": "analyze_retention", "description": "Identifica patrones de deserción."},
            {"name": "recommend_optimizations", "description": "Genera insights estratégicos basándose en métricas."}
        ], 
        {"requires": "report_data"}, 
        {"provides": "strategic_insights"},
        token
    )
