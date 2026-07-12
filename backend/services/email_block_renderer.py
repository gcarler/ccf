"""Renderer de bloques JSON -> HTML responsive para emails."""
from __future__ import annotations

from html import escape
from typing import Any, Dict, List, Optional

from backend.services.email import _FALLBACK_BRAND, _brand_wrap


def _esc(val: str) -> str:
    return escape(val)


def _render_block(block: Dict[str, Any], brand: Dict[str, str]) -> str:
    btype = block.get("type", "")
    props = block.get("props", {})
    primary = brand.get("primary", _FALLBACK_BRAND["primary"])
    dark = brand.get("dark", _FALLBACK_BRAND["dark"])
    medium = brand.get("medium", _FALLBACK_BRAND["medium"])

    if btype == "header":
        title_color = props.get("titleColor") or dark
        bg_style = f"background:{props.get('bgColor', '')};" if props.get("bgColor") else ""
        subtitle = props.get("subtitle", "")
        subtitle_html = f'<p style="margin:4px 0 0;font-size:14px;opacity:0.7;">{_esc(str(subtitle))}</p>' if subtitle else ""
        return f'<tr><td style="padding:24px;text-align:{props.get("textAlign", "center")};{bg_style}"><h2 style="margin:0;font-size:24px;font-weight:bold;color:{title_color};">{_esc(str(props.get("title", "")))}</h2>{subtitle_html}</td></tr>'

    if btype == "text":
        return f'<tr><td style="padding:16px 24px;text-align:{props.get("textAlign", "left")};font-size:15px;line-height:1.7;color:#374151;">{str(props.get("content", ""))}</td></tr>'

    if btype == "button":
        bg = props.get("bgColor") or primary
        tc = props.get("textColor") or "#ffffff"
        r = props.get("borderRadius", 10)
        return f'<tr><td style="padding:16px 24px;text-align:{props.get("align", "center")};"><a href="{_esc(str(props.get("url", "#")))}" style="display:inline-block;padding:12px 32px;background:{bg};color:{tc};font-size:14px;font-weight:600;text-decoration:none;border-radius:{r}px;">{_esc(str(props.get("label", "")))}</a></td></tr>'

    if btype == "image":
        src = str(props.get("src", ""))
        if not src:
            return ""
        return f'<tr><td style="padding:16px 24px;"><img src="{_esc(src)}" alt="{_esc(str(props.get("alt", "")))}" style="width:{props.get("width", "100%")};display:block;" /></td></tr>'

    if btype == "divider":
        return f'<tr><td style="padding:8px 24px;"><hr style="border:none;border-top:{props.get("thickness", 1)}px {props.get("style", "solid")} {props.get("color", "#e5e7eb")};width:{props.get("width", "100%")};" /></td></tr>'

    if btype == "spacer":
        return f'<tr><td style="height:{props.get("height", 24)}px;"></td></tr>'

    if btype == "verse":
        ref_html = f'<p style="margin:8px 0 0;font-size:12px;font-weight:bold;color:{dark};letter-spacing:2px;text-transform:uppercase;">&mdash; {_esc(str(props.get("reference", "")))}</p>' if props.get("reference") else ""
        return f'<tr><td style="padding:16px 24px;"><div style="background:#f0f5fa;border-radius:12px;padding:20px;text-align:{props.get("textAlign", "center")};"><p style="margin:0;font-size:16px;font-style:italic;color:{medium};line-height:1.7;">&ldquo;{_esc(str(props.get("text", "")))}&rdquo;</p>{ref_html}</div></td></tr>'

    if btype == "columns":
        count = int(props.get("count", 2))
        cw = 100 / count
        cols = "".join(f'<td style="width:{cw:.1f}%;padding:0 4px;vertical-align:top;border:1px dashed #e5e7eb;min-height:40px;"></td>' for _ in range(count))
        return f'<tr><td style="padding:16px 24px;"><table width="100%" cellpadding="0" cellspacing="0"><tr>{cols}</tr></table></td></tr>'

    return ""


def render_blocks_to_html(blocks: List[Dict[str, Any]], brand: Optional[Dict[str, str]] = None) -> str:
    b = brand or _FALLBACK_BRAND
    body = "\n".join(_render_block(block, b) for block in blocks if _render_block(block, b))
    return _brand_wrap(body, b)


def is_blocks_json(content: str) -> bool:
    if not content:
        return False
    try:
        import json
        parsed = json.loads(content)
        return isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict) and "type" in parsed[0]
    except (json.JSONDecodeError, IndexError, TypeError):
        return False
