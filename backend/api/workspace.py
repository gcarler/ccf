from fastapi import APIRouter

from backend.api.workspace_audit import router as workspace_audit_router
from backend.api.workspace_compliance import router as workspace_compliance_router
from backend.api.workspace_config import router as workspace_config_router
from backend.api.workspace_flags import router as workspace_flags_router
from backend.api.workspace_incidents import router as workspace_incidents_router

router = APIRouter(tags=["workspace"])
router.include_router(workspace_config_router)
router.include_router(workspace_flags_router)
router.include_router(workspace_audit_router)
router.include_router(workspace_incidents_router)
router.include_router(workspace_compliance_router)
