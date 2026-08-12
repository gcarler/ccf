"""Proxy de Google Photos para incrustación en iframe.

Google Photos bloquea la incrustación en iframes externos con
``x-frame-options: SAMEORIGIN``. Este endpoint hace de proxy: hace fetch
del álbum compartido, remueve los headers restrictivos y devuelve el HTML
para que el iframe del frontend funcione sin error 403.

Uso: ``GET /api/cms/embed/photos?url=<photos.app.goo.gl/...>``
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["cms_embed"])

# Solo permitir dominios de Google Photos para evitar SSRF.
_ALLOWED_HOSTS = ("photos.app.goo.gl", "photos.google.com")


@router.get("/embed/photos", response_class=HTMLResponse)
async def embed_google_photos(
    url: str = Query(..., description="URL corta o completa de Google Photos"),
):
    """Sirve el contenido de un álbum de Google Photos sin x-frame-options."""
    # Validar que la URL sea de Google Photos
    if not any(host in url for host in _ALLOWED_HOSTS):
        raise HTTPException(status_code=400, detail="URL must be from Google Photos")
    if not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="URL must be HTTPS")

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=10.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; CCF-Embed/1.0)"},
        ) as client:
            resp = await client.get(url)
            html = resp.text
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch Google Photos: {exc}")

    # Inyectar <base target="_blank"> para que los enlaces abran en nueva pestaña
    # y no intenten navegar dentro del iframe.
    html = html.replace("<head>", '<head><base target="_blank">', 1)

    return HTMLResponse(
        content=html,
        headers={
            # No enviar x-frame-options ni content-security-policy → permite embed
            "Cache-Control": "public, max-age=300",
        },
    )