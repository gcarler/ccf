from contextvars import ContextVar
from typing import Optional

# Almacena el rol del usuario actual para validación en schemas
user_role_context: ContextVar[Optional[str]] = ContextVar("user_role_context", default=None)
