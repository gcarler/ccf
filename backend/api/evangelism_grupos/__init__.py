"""Evangelism Grupos package — split from evangelism_grupos.py.

Sub-modules:
- grupos_main.py: CRUD de grupos, analytics, seasons, visitors, metrics
- grupos_sesiones.py: sesiones, gobernanza, helpers de ausencias
- grupos_asistencias.py: asistencia, seguimiento/follow-up
"""
from fastapi import APIRouter

router = APIRouter(tags=["Evangelismo - Grupos"])

from backend.api.evangelism_grupos import grupos_asistencias, grupos_main, grupos_sesiones

router.include_router(grupos_main.router)
router.include_router(grupos_sesiones.router)
router.include_router(grupos_asistencias.router)
