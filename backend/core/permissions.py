from typing import List, Dict

# Taxonoma de permisos granulares disponibles en el sistema
PERMISSIONS = {
    # System / General
    "system:config": "Acceso total para configurar el sistema (Super Admin)",
    "profile:manage": "Permite al usuario gestionar su propia informacin personal",
    
    # CRM
    "crm:manage": "Permite gestionar informacin, eventos y miembros en el CRM",
    "crm:read": "Permite solo lectura de la informacin del CRM",
    
    # Finanzas
    "finance:manage": "Permite gestionar transacciones, donaciones y presupuestos",
    "finance:read": "Permite solo lectura del mdulo de finanzas",
    
    # Proyectos
    "projects:manage": "Permite gestionar proyectos, tareas y tableros",
    "projects:read": "Permite solo lectura de los proyectos",
    
    # CMS / Contenido Web
    "cms:manage": "Permite gestionar el contenido web, pginas y multimedia",
    "cms:read": "Permite ver borradores y contenido interno del CMS",
    
    # Academia (LMS)
    "academy:manage": "Permite crear y gestionar cursos, lecciones y calificaciones",
    "academy:study": "Permite inscribirse en cursos, consumir contenido y desarrollar evaluaciones",
}

# Matriz de roles por defecto (Seed inicial basado en requerimientos)
DEFAULT_ROLES = [
    {
        "name": "Super administrador",
        "label": "Super administrador",
        "permissions": [
            "system:config", "crm:manage", "finance:manage", 
            "projects:manage", "cms:manage", "academy:manage",
            "academy:study", "profile:manage"
        ]
    },
    {
        "name": "Administrador",
        "label": "Administrador",
        "permissions": [
            "crm:manage", "finance:manage", "projects:manage", 
            "cms:manage", "academy:manage", "academy:study", "profile:manage"
        ]
    },
    {
        "name": "Gestor",
        "label": "Gestor",
        "permissions": [
            "crm:manage", "projects:manage", "academy:manage", 
            "academy:study", "profile:manage"
        ]
    },
    {
        "name": "Usuario_t1",
        "label": "miembro_1",
        "permissions": [
            "profile:manage", "academy:study"
        ]
    },
    {
        "name": "Usuario_t2",
        "label": "miembro_2",
        "permissions": [
            "academy:study"
        ]
    }
]

def get_all_permissions() -> Dict[str, str]:
    return PERMISSIONS

def get_default_roles() -> List[Dict]:
    return DEFAULT_ROLES
