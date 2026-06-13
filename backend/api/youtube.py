"""
YouTube RSS proxy para el canal de El Faro.
Sin API key — usa el feed RSS público de YouTube + resolución automática de channel ID.
Caché en memoria de 1 hora para no martillar YouTube en cada request.
"""
import re
import time
import logging
import xml.etree.ElementTree as ET
from typing import Optional

import httpx
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

YOUTUBE_HANDLE = "@Ministeriosfarooficial"

_NS = {
    "atom":  "http://www.w3.org/2005/Atom",
    "yt":    "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

_channel_id_cache: Optional[str] = None
_videos_cache: Optional[dict] = None
_cache_ts: float = 0
_CACHE_TTL = 3600  # 1 hora


async def _resolve_channel_id(handle: str) -> Optional[str]:
    """Obtiene el channel ID leyendo la página del canal y extrayendo el JSON incrustado."""
    url = f"https://www.youtube.com/{handle}"
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"
                    ),
                    "Accept-Language": "es-CO,es;q=0.9",
                },
            )
        if resp.status_code != 200:
            logger.warning("YouTube channel page returned %s", resp.status_code)
            return None
        # channelId aparece varias veces en el HTML como JSON embebido
        for pattern in (
            r'"channelId":"(UC[A-Za-z0-9_-]{22})"',
            r'"externalId":"(UC[A-Za-z0-9_-]{22})"',
            r'channel_id=(UC[A-Za-z0-9_-]{22})',
        ):
            m = re.search(pattern, resp.text)
            if m:
                return m.group(1)
    except Exception as exc:
        logger.error("Error resolving YouTube channel ID: %s", exc)
    return None


async def _fetch_rss(channel_id: str) -> list[dict]:
    """Parsea el RSS de YouTube y devuelve lista de videos."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

    root = ET.fromstring(resp.content)
    videos: list[dict] = []

    for entry in root.findall("atom:entry", _NS):
        vid_el   = entry.find("yt:videoId",          _NS)
        title_el = entry.find("atom:title",           _NS)
        pub_el   = entry.find("atom:published",       _NS)
        desc_el  = entry.find(".//media:description", _NS)
        views_el = entry.find(".//yt:statistics",     _NS)

        if vid_el is None or title_el is None:
            continue

        video_id   = vid_el.text or ""
        title      = title_el.text or ""
        published  = pub_el.text if pub_el is not None else ""
        description = (desc_el.text or "").strip()[:300] if desc_el is not None else ""
        view_count  = int(views_el.attrib.get("views", 0)) if views_el is not None else 0

        videos.append({
            "id":           video_id,
            "title":        title,
            "description":  description,
            "published_at": published,
            "view_count":   view_count,
            "thumbnail_hq": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "thumbnail_mq": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
            "url":          f"https://www.youtube.com/watch?v={video_id}",
            "embed_url":    f"https://www.youtube.com/embed/{video_id}?rel=0&autoplay=1",
        })

    return videos


@router.get("/youtube/videos")
async def get_youtube_videos():
    """
    Devuelve los últimos videos del canal de YouTube de El Faro.
    Caché de 1 hora en memoria — sin API key requerida.
    """
    global _channel_id_cache, _videos_cache, _cache_ts

    now = time.time()
    if _videos_cache and (now - _cache_ts) < _CACHE_TTL:
        return _videos_cache

    if not _channel_id_cache:
        _channel_id_cache = await _resolve_channel_id(YOUTUBE_HANDLE)
        if not _channel_id_cache:
            return {"videos": [], "channel": YOUTUBE_HANDLE, "error": "canal_no_resuelto"}

    try:
        videos = await _fetch_rss(_channel_id_cache)
    except Exception as exc:
        logger.error("Error fetching YouTube RSS: %s", exc)
        if _videos_cache:
            return _videos_cache  # sirve caché vieja si hay error transitorio
        return {"videos": [], "channel": YOUTUBE_HANDLE, "error": "rss_error"}

    _videos_cache = {
        "videos":  videos,
        "total":   len(videos),
        "channel": YOUTUBE_HANDLE,
        "cached_at": int(now),
    }
    _cache_ts = now
    return _videos_cache
