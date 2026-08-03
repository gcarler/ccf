"""Run via: cd /root/ccf && ./venv/bin/python tests/test_pastoral_helpers_direct.py"""
import sys

sys.path.insert(0, '/root/ccf')

from backend.api.crm.pastoral import _get_user_role, _stage_to_estado
from backend.models_crm_pipeline import EstadoCasoEnum


def test_stage_to_estado_all():
    # RESUELTO_EXITO
    assert _stage_to_estado("consolidated") == EstadoCasoEnum.RESUELTO_EXITO
    assert _stage_to_estado("integrated") == EstadoCasoEnum.RESUELTO_EXITO
    assert _stage_to_estado("converted") == EstadoCasoEnum.RESUELTO_EXITO
    # CERRADO_PERDIDO
    assert _stage_to_estado("lost") == EstadoCasoEnum.CERRADO_PERDIDO
    assert _stage_to_estado("closed") == EstadoCasoEnum.CERRADO_PERDIDO
    assert _stage_to_estado("discarded") == EstadoCasoEnum.CERRADO_PERDIDO
    # ESPERANDO_RESPUESTA
    assert _stage_to_estado("call") == EstadoCasoEnum.ESPERANDO_RESPUESTA
    assert _stage_to_estado("contacted") == EstadoCasoEnum.ESPERANDO_RESPUESTA
    # EN_PROGRESO
    assert _stage_to_estado("visit") == EstadoCasoEnum.EN_PROGRESO
    assert _stage_to_estado("visited") == EstadoCasoEnum.EN_PROGRESO
    assert _stage_to_estado("discipleship") == EstadoCasoEnum.EN_PROGRESO
    assert _stage_to_estado("in_process") == EstadoCasoEnum.EN_PROGRESO
    # DEFAULT
    assert _stage_to_estado("") == EstadoCasoEnum.ABIERTO
    assert _stage_to_estado("unknown") == EstadoCasoEnum.ABIERTO


def test_get_user_role_all():
    user = type("U", (), {"role": "ADMIN"})()
    assert _get_user_role(user) == "admin"
    role = type("R", (), {"nombre": "pastor"})()
    user2 = type("U", (), {"role": "", "rol_plataforma": role})()
    assert _get_user_role(user2) == "pastor"
    user3 = type("U", (), {"role": "", "rol_plataforma": None})()
    assert _get_user_role(user3) == ""


if __name__ == "__main__":
    test_stage_to_estado_all()
    test_get_user_role_all()
    print(f"\n{'='*50}")
    print("ALL PASTORAL HELPER TESTS PASSED")
    print(f"{'='*50}")
