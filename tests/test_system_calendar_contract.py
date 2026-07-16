from pathlib import Path


SYSTEM_API_PATH = Path("/root/ccf/backend/api/system.py")


def test_system_calendar_uses_frontend_canonical_crm_types():
    source = SYSTEM_API_PATH.read_text()
    assert '"type": "consolidation_case"' in source
    assert '"type": "consolidation_task"' in source
    assert '"type": "crm_caso"' not in source
    assert '"type": "crm_tarea"' not in source


def test_system_calendar_uses_canonical_platform_hrefs():
    source = SYSTEM_API_PATH.read_text()
    assert '/plataforma/projects/' in source
    assert '/plataforma/evangelism/strategies/' in source
    assert '/plataforma/proyectos/' not in source
    assert '/plataforma/evangelism/estrategias/' not in source
