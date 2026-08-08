"""Validación server-side de formularios dinámicos (CmsForm).

Valida el JSON ``fields`` de un ``CmsForm`` y los datos de un submit público
contra ese contrato. Es la fuente de verdad — el frontend replica la misma
lógica en cliente, pero el backend NO confía en el cliente.

Conceptos
=========
- ``CmsFormFieldSpec``: contrato versionado de un campo (tipo, label, reglas
  de validación, lógica condicional). Se valida en el admin al guardar.
- ``validate_submission``: valida los datos de un submit público contra los
  ``fields`` del ``CmsForm``. Aplica ``required``, tipos, regex, min/max,
  opciones válidas y ``visible_if`` (condicionales — los campos no visibles
  no se aceptan).
- ``_OPERATORS``: tabla de operadores para lógica condicional.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Iterable, Mapping, Optional

import httpx

from backend.core.config import get_settings

log = logging.getLogger(__name__)


FIELD_TYPES = (
    # básicos existentes
    "text",
    "email",
    "phone",
    "textarea",
    "select",
    "checkbox",
    # nuevos básicos
    "number",
    "date",
    "datetime",
    "url",
    # nuevas opciones
    "select_multiple",
    "radio",
    # nuevas escalas
    "rating",
    "slider",
    # nuevo adjunto
    "file",
    # nuevos agrupadores / utilitarios (no sumiten datos reales)
    "section",
    "page",
    "divider",
    "captcha",
)

# Tipos que producen un valor a validar contra ``data``.
_VALUE_TYPES = {
    "text",
    "email",
    "phone",
    "textarea",
    "select",
    "checkbox",
    "number",
    "date",
    "datetime",
    "url",
    "select_multiple",
    "radio",
    "rating",
    "slider",
    "file",
}
# Tipos que NO producen valor (metadata/layout) — ignorados en la validación de submit.
_META_TYPES = {"section", "page", "divider", "captcha"}

OPERATORS = (
    "eq",
    "neq",
    "in",
    "not_in",
    "contains",
    "gt",
    "lt",
    "gte",
    "lte",
    "checked",
    "empty",
    "not_empty",
)


class ValidationError(Exception):
    """Error de validación con código + detalle (HTTP 422)."""

    def __init__(self, code: str, detail: str, field_id: Optional[str] = None):
        self.code = code
        self.detail = detail
        self.field_id = field_id
        super().__init__(f"{code}: {detail}")


# ── Validación de la definición del campo (al guardar el formulario) ────────


def validate_field_spec(spec: Mapping[str, Any]) -> None:
    """Valida que un dict represente un ``CmsFormFieldSpec`` coherente.

    Se invoca desde el endpoint admin al crear/actualizar un ``CmsForm``.
    """
    ftype = spec.get("type")
    if ftype not in FIELD_TYPES:
        raise ValidationError("INVALID_FIELD_TYPE", f"Tipo de campo inválido: {ftype}")

    label = (spec.get("label") or "").strip()
    if not label:
        raise ValidationError("MISSING_LABEL", "El campo debe tener una etiqueta", spec.get("id"))
    if len(label) > 200:
        raise ValidationError("LABEL_TOO_LONG", "La etiqueta no puede exceder 200 caracteres", spec.get("id"))

    fid = (spec.get("id") or "").strip()
    if not fid:
        raise ValidationError("MISSING_FIELD_ID", "Cada campo debe tener un id", spec.get("id"))
    if len(fid) > 80:
        raise ValidationError("FIELD_ID_TOO_LONG", "El id no puede exceder 80 caracteres", spec.get("id"))

    # Opciones requeridas para select/radio/select_multiple
    if ftype in {"select", "radio", "select_multiple"}:
        options = spec.get("options") or []
        if not isinstance(options, list) or not options:
            raise ValidationError("OPTIONS_REQUIRED", "Este campo requiere opciones", fid)
        if any(not isinstance(o, str) or not o.strip() for o in options):
            raise ValidationError("INVALID_OPTION", "Las opciones deben ser texto no vacío", fid)

    # validate visible_if structure
    vis = spec.get("visible_if")
    if vis is not None:
        if not isinstance(vis, Mapping):
            raise ValidationError("INVALID_CONDITION", "visible_if debe ser un objeto", fid)
        if "field_id" not in vis or "operator" not in vis:
            raise ValidationError("INVALID_CONDITION", "visible_if requiere field_id y operator", fid)
        if vis["operator"] not in OPERATORS:
            raise ValidationError("INVALID_OPERATOR", f"Operador inválido: {vis['operator']}", fid)


# ── Validación de un submit público contra los fields del formulario ─────────


def validate_submission(
    fields: Iterable[Mapping[str, Any]],
    data: Mapping[str, Any],
    *,
    honeypot_value: Optional[str] = None,
    honeypot_enabled: bool = True,
) -> dict[str, Any]:
    """Valida los datos de un submit contra los ``fields``.

    Returns:
        ``dict`` limpio con los valores validados (solo campos visibles y
        válidos). Lanza ``ValidationError`` en cualquier fallo.
    """
    if honeypot_enabled and honeypot_value:
        # honeypot rellenado → bot; no persistir. Manejado por el endpoint.
        raise ValidationError("HONEYPOT_TRIGGERED", "Submission rechazada (spam detectado)")

    clean: dict[str, Any] = {}
    by_id: dict[str, Mapping[str, Any]] = {(f.get("id") or ""): f for f in fields if f.get("id")}
    data_keys = set(data.keys())

    # Detectar claves extra que no corresponden a ningún campo del formulario.
    unknown = data_keys - set(by_id.keys())
    if unknown:
        # En modo tolerante (back-compat con schema anterior sin id), las claves
        # pueden corresponder a labels previos. Aceptamos las que matcheen un
        # label. Si no matchean, se rechazan.
        label_to_id = {
            (_un_((f.get("label") or ""))): (f.get("id") or f.get("label") or "")
            for f in fields
            if f.get("type") in _VALUE_TYPES
        }
        for k in list(unknown):
            if _un_(k) in label_to_id:
                # mapear al id real
                real_id = label_to_id[_un_(k)]
                if real_id and real_id not in clean:
                    data = {**data, real_id: data[k]}
                unknown.discard(k)
    if unknown:
        raise ValidationError("UNKNOWN_FIELD", f"Campo no definido en el formulario: {sorted(unknown)[0]}")

    for fid, field in by_id.items():
        ftype = field.get("type")
        if ftype in _META_TYPES:
            continue
        if not _is_visible(field, by_id, data):
            # Campo condicionalmente oculto: si el cliente lo envió igual,
            # lo rechazamos (defensa en profundidad) — excepto si es vacío, lo
            # ignoramos silenciosamente para no romper UX.
            if data.get(fid) not in (None, "", [], {}):
                raise ValidationError("HIDDEN_FIELD_SENT", f"El campo {fid} no debería enviarse (oculto)", fid)
            continue

        value = data.get(fid)
        required = bool(field.get("required"))
        if _is_empty(value):
            if required:
                raise ValidationError("REQUIRED_FIELD", f"El campo '{field.get('label')}' es obligatorio", fid)
            continue

        # coercion + tipo
        validated = _validate_value(field, value)
        clean[fid] = validated

    return clean


_VALID_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_VALID_URL = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


def _validate_value(field: Mapping[str, Any], value: Any) -> Any:
    ftype = field.get("type")
    fid = field.get("id")
    if ftype == "text" or ftype == "textarea":
        v = str(value).strip()
        _check_length(field, v, fid)
        _check_regex(field, v, fid)
        return v
    if ftype == "email":
        v = str(value).strip()
        if not _VALID_EMAIL.match(v):
            raise ValidationError("INVALID_EMAIL", "Correo electrónico inválido", fid)
        _check_length(field, v, fid)
        return v
    if ftype == "phone":
        v = str(value).strip()
        if not re.match(r"^[+]?[\d\s\-().]{6,20}$", v):
            raise ValidationError("INVALID_PHONE", "Teléfono inválido", fid)
        return v
    if ftype == "url":
        v = str(value).strip()
        if not _VALID_URL.match(v):
            raise ValidationError("INVALID_URL", "URL inválida (debe empezar con http:// o https://)", fid)
        return v
    if ftype == "number":
        try:
            if isinstance(value, bool):
                # bool no es número válido en este contexto
                raise ValueError
            num = float(value) if not isinstance(value, (int, float)) else value
        except (TypeError, ValueError):
            raise ValidationError("INVALID_NUMBER", "Se esperaba un número", fid)
        _check_numeric_range(field, num, fid)
        return num
    if ftype in {"date", "datetime"}:
        v = str(value).strip()
        # aceptar ISO YYYY-MM-DD o YYYY-MM-DDTHH:MM
        pattern = r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?)?$" if ftype == "datetime" else r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(pattern, v):
            raise ValidationError("INVALID_DATE", "Fecha inválida (use YYYY-MM-DD)", fid)
        return v
    if ftype == "checkbox":
        # acepta true/false/"true"/"false"/"1"/"0"/1/0
        truthy = {True, "true", "True", 1, "1"}
        falsy = {False, "false", "False", 0, "0"}
        if value in truthy:
            return True
        if value in falsy:
            return False
        raise ValidationError("INVALID_CHECKBOX", "Se esperaba verdadero/falso", fid)
    if ftype in {"select", "radio"}:
        v = str(value).strip()
        options = field.get("options") or []
        if v not in options:
            # permitir "+ Otra" si allow_other
            if field.get("allow_other") and v:
                return v
            raise ValidationError("INVALID_OPTION", f"'{v}' no es una opción válida", fid)
        return v
    if ftype == "select_multiple":
        if not isinstance(value, list):
            # aceptar string separado por coma como fallback
            value = [s.strip() for s in str(value).split(",") if s.strip()]
        options = field.get("options") or []
        clean_vals = []
        for v in value:
            vs = str(v).strip()
            if vs in options or (field.get("allow_other") and vs):
                clean_vals.append(vs)
            else:
                raise ValidationError("INVALID_OPTION", f"'{vs}' no es una opción válida", fid)
        return clean_vals
    if ftype == "rating":
        try:
            num = int(value) if not isinstance(value, (int, float)) else int(value)
        except (TypeError, ValueError):
            raise ValidationError("INVALID_RATING", "Rating debe ser un entero", fid)
        _check_numeric_range(field, num, fid)
        return num
    if ftype == "slider":
        try:
            num = float(value) if not isinstance(value, (int, float)) else value
        except (TypeError, ValueError):
            raise ValidationError("INVALID_SLIDER", "Slider debe ser un número", fid)
        _check_numeric_range(field, num, fid)
        return num
    if ftype == "file":
        # el archivo se sube aparte; aquí guardamos metadata {name, mime, size, url}
        if not isinstance(value, Mapping):
            raise ValidationError("INVALID_FILE", "Archivo inválido", fid)
        max_mb = field.get("max_file_mb")
        if max_mb and isinstance(value.get("size"), (int, float)) and value["size"] > max_mb * 1024 * 1024:
            raise ValidationError("FILE_TOO_LARGE", f"Archivo excede {max_mb} MB", fid)
        accept = field.get("accept")
        if accept and isinstance(value.get("mime"), str):
            # accept es tipo "image/*" o "image/png,image/jpeg"
            allowed = [a.strip() for a in accept.split(",")]
            mime = value["mime"]
            if not any(_mime_match(mime, a) for a in allowed):
                raise ValidationError("FILE_TYPE_NOT_ALLOWED", f"Tipo MIME no permitido: {mime}", fid)
        return dict(value)
    raise ValidationError("UNSUPPORTED_TYPE", f"Tipo no soportado: {ftype}", fid)


def _mime_match(mime: str, pattern: str) -> bool:
    if pattern == "*/*":
        return True
    if pattern.endswith("/*"):
        return mime.startswith(pattern[:-1])
    return mime == pattern


def _check_length(field: Mapping[str, Any], v: str, fid: str | None) -> None:
    mn = field.get("min_length")
    mx = field.get("max_length")
    if mn is not None and len(v) < mn:
        raise ValidationError("TOO_SHORT", f"El campo debe tener al menos {mn} caracteres", fid)
    if mx is not None and len(v) > mx:
        raise ValidationError("TOO_LONG", f"El campo no puede exceder {mx} caracteres", fid)


def _check_numeric_range(field: Mapping[str, Any], num: float, fid: str | None) -> None:
    mn = field.get("min_value")
    mx = field.get("max_value")
    if mn is not None and num < mn:
        raise ValidationError("BELOW_MIN", f"El valor debe ser ≥ {mn}", fid)
    if mx is not None and num > mx:
        raise ValidationError("ABOVE_MAX", f"El valor debe ser ≤ {mx}", fid)


def _check_regex(field: Mapping[str, Any], v: str, fid: str | None) -> None:
    pattern = field.get("regex_pattern")
    if not pattern:
        return
    try:
        if not re.fullmatch(pattern, v):
            msg = field.get("regex_message") or "El valor no cumple el patrón esperado"
            raise ValidationError("REGEX_FAIL", msg, fid)
    except re.error as exc:
        # patrón roto en la definición del campo — falla safe
        raise ValidationError("INVALID_REGEX", f"Patrón de validación inválido: {exc}", fid)


def _is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    if isinstance(v, (list, dict, tuple)) and len(v) == 0:
        return True
    return False


def _is_visible(
    field: Mapping[str, Any],
    by_id: Mapping[str, Mapping[str, Any]],
    data: Mapping[str, Any],
) -> bool:
    cond = field.get("visible_if")
    if not cond:
        return True
    target_id = cond.get("field_id")
    operator = cond.get("operator")
    target_val = data.get(target_id)
    ref_val = cond.get("value")

    if operator == "eq":
        return target_val == ref_val
    if operator == "neq":
        return target_val != ref_val
    if operator == "in":
        return target_val in (ref_val or [])
    if operator == "not_in":
        return target_val not in (ref_val or [])
    if operator == "contains":
        return isinstance(target_val, str) and str(ref_val) in target_val
    if operator == "gt":
        return _to_num(target_val) > _to_num(ref_val)
    if operator == "lt":
        return _to_num(target_val) < _to_num(ref_val)
    if operator == "gte":
        return _to_num(target_val) >= _to_num(ref_val)
    if operator == "lte":
        return _to_num(target_val) <= _to_num(ref_val)
    if operator == "checked":
        return bool(target_val) is True
    if operator == "not_checked":
        return bool(target_val) is False
    if operator == "empty":
        return _is_empty(target_val)
    if operator == "not_empty":
        return not _is_empty(target_val)
    return True


def _to_num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("-inf")


def _un_(s: str) -> str:
    """Normaliza un label para matching tolerante (lowercase, sin acentos/espacios)."""
    s = s.lower().strip()
    table = str.maketrans("áéíóúüñ", "aeiouun")
    return s.translate(table).replace(" ", "_")


# ── hCaptcha siteverify ────────────────────────────────────────────────────


async def verify_hcaptcha(token: str, *, remote_ip: str | None = None) -> bool:
    """Verifica un token de hCaptcha contra la API oficial.

    Returns True si el captcha es válido. False si el token es inválido o
    la configuración faltante. Lanza si hay error de red persistente.
    """
    settings = get_settings()
    secret = settings.hcaptcha_secret_key
    if not secret:
        log.warning("hCaptcha siteverify llamado pero HCAPTCHA_SECRET_KEY no configurado")
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {"secret": secret, "response": token}
            if remote_ip:
                payload["remoteip"] = remote_ip
            resp = await client.post("https://api.hcaptcha.com/siteverify", data=payload)
            resp.raise_for_status()
            result = resp.json()
            return bool(result.get("success", False))
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("hCaptcha siteverify failed: %s", exc)
        return False
