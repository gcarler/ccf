"""
Module Isolation Middleware — Aislamiento de fallos por módulo en el backend.

Si un módulo falla (evangelism, crm, academy, projects, etc.), el error se
captura y se retorna un 500 con detalle del módulo, sin tumbar todo el servidor.
"""
import logging
import time
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("module_isolation")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)

# Circuit breaker state: module_name -> {failures: int, last_failure: float, open: bool}
_circuit_breakers: dict[str, dict] = {}
CIRCUIT_THRESHOLD = 5  # fallos consecutivos antes de abrir circuito
CIRCUIT_TIMEOUT = 60   # segundos antes de intentar reconectar


def get_circuit_state(module: str) -> dict:
    """Obtiene el estado del circuit breaker para un módulo."""
    if module not in _circuit_breakers:
        _circuit_breakers[module] = {"failures": 0, "last_failure": 0, "open": False}
    return _circuit_breakers[module]


def extract_module(path: str) -> str:
    """Extrae el nombre del módulo desde la ruta de la API."""
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "api":
        return parts[1].split("/")[0]
    return "system"


async def module_isolation_middleware(request: Request, call_next):
    """
    Middleware que aísla fallos por módulo.
    
    Si un módulo falla repetidamente, se abre el circuit breaker y se rechazan
    peticiones rápidamente hasta que el módulo se recupere.
    """
    module = extract_module(request.url.path)
    circuit = get_circuit_state(module)
    
    # Si el circuito está abierto, rechazar rápidamente
    if circuit["open"]:
        elapsed = time.time() - circuit["last_failure"]
        if elapsed < CIRCUIT_TIMEOUT:
            return JSONResponse(
                status_code=503,
                content={
                    "error": f"El módulo '{module}' está temporalmente indisponible",
                    "module": module,
                    "retry_after": int(CIRCUIT_TIMEOUT - elapsed),
                }
            )
        else:
            # Timeout alcanzado, intentar reconectar (half-open)
            circuit["open"] = False
            circuit["failures"] = 0
    
    try:
        response = await call_next(request)
        # Si la respuesta es exitosa, resetear el circuit breaker
        if response.status_code < 500:
            circuit["failures"] = 0
        return response
    except Exception as e:
        circuit["failures"] += 1
        circuit["last_failure"] = time.time()

        tb_str = traceback.format_exc()
        logger.error(f"[{module}] Request failed ({circuit['failures']}/{CIRCUIT_THRESHOLD}): {e}\n{tb_str}")
        
        # Abrir circuito si supera el threshold
        if circuit["failures"] >= CIRCUIT_THRESHOLD:
            circuit["open"] = True
            logger.warning(f"[{module}] Circuit breaker OPEN after {circuit['failures']} failures")
        
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Error interno en el módulo {module}",
                "module": module,
                "detail": str(e)[:500],
            }
        )


def get_module_health() -> dict:
    """Retorna el estado de salud de todos los módulos."""
    result = {}
    for module, circuit in _circuit_breakers.items():
        result[module] = {
            "status": "open" if circuit["open"] else "closed",
            "failures": circuit["failures"],
            "last_failure": circuit["last_failure"],
        }
    return result


def register_module_isolation(app: FastAPI):
    """Registra el middleware de aislamiento en la app FastAPI."""
    app.middleware("http")(module_isolation_middleware)
