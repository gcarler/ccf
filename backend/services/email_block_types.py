"""Block type definitions for the CRM email builder."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

BLOCK_TYPES = {
    "header": {"label": "Encabezado", "icon": "Type", "category": "content", "default_props": {"title": "Tu titulo aqui", "subtitle": "", "textAlign": "center", "titleColor": "", "bgColor": ""}},
    "text": {"label": "Texto", "icon": "AlignLeft", "category": "content", "default_props": {"content": "<p>Escribe tu mensaje aqui...</p>", "textAlign": "left"}},
    "button": {"label": "Boton CTA", "icon": "MousePointerClick", "category": "content", "default_props": {"label": "Haz clic aqui", "url": "#", "align": "center", "bgColor": "", "textColor": "#ffffff", "borderRadius": 10}},
    "image": {"label": "Imagen", "icon": "Image", "category": "content", "default_props": {"src": "", "alt": "", "width": "100%", "href": ""}},
    "divider": {"label": "Divisor", "icon": "Minus", "category": "layout", "default_props": {"color": "#e5e7eb", "thickness": 1, "style": "solid", "width": "100%"}},
    "spacer": {"label": "Espacio", "icon": "Space", "category": "layout", "default_props": {"height": 24}},
    "verse": {"label": "Versiculo", "icon": "BookOpen", "category": "content", "default_props": {"text": "Jeremias 29:11", "reference": "Jeremias 29:11", "textAlign": "center"}},
    "columns": {"label": "Columnas", "icon": "Columns", "category": "layout", "default_props": {"count": 2, "columns": [{"blocks": []}, {"blocks": []}]}},
}

@dataclass
class EmailBlock:
    id: str
    type: str
    props: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "type": self.type, "props": self.props}

def get_block_types() -> Dict[str, Dict]:
    return dict(BLOCK_TYPES)

def get_default_props(block_type: str) -> Dict[str, Any]:
    bt = BLOCK_TYPES.get(block_type)
    return dict(bt["default_props"]) if bt else {}
