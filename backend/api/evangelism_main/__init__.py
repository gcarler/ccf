"""Evangelism Main package — split from evangelism.py.

Sub-modules:
- main_estrategias.py: CRUD de estrategias, generación de sesiones
- main_roles.py: roles personalizados + motivos de excusa
- main_utils.py: helpers compartidos (_channel_label, _serialize_crm_task, etc.)
"""
from fastapi import APIRouter

estrategias_router = APIRouter(tags=["Evangelismo - Estrategias"])
roles_router = APIRouter(tags=["Evangelismo - Roles y Excusas"])

from backend.api.evangelism_main import main_estrategias
from backend.api.evangelism_main import main_roles

estrategias_router.include_router(main_estrategias.estrategias_router)
roles_router.include_router(main_roles.roles_router)
