"""Coverage tests for the YouTube module.

Covers:
- GET /api/youtube/videos (public endpoint)
- Cache behavior, empty state, response shape
- Edge cases
"""

from __future__ import annotations

# No conftest imports needed — youtube endpoint is public


# ══════════════════════════════════════════════════════════════════════
# A. YouTube videos endpoint tests
# ══════════════════════════════════════════════════════════════════════


def test_youtube_videos_public(client):
    """GET /youtube/videos es público (no requiere auth) y devuelve la estructura esperada.

    En test mode, el external HTTP está deshabilitado, por lo que el
    endpoint devuelve un dict con {videos, total, channel, error}.
    """
    resp = client.get("/api/youtube/videos")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert isinstance(data, dict)
    # En test mode, esperamos el fallback con lista vacía
    assert "videos" in data
    assert "total" in data
    assert "channel" in data
    assert isinstance(data["videos"], list)
    assert isinstance(data["total"], int)
    assert isinstance(data["channel"], str)


def test_youtube_videos_response_shape(client):
    """GET /youtube/videos → cada video (si existe) tiene las claves esperadas."""
    resp = client.get("/api/youtube/videos")
    assert resp.status_code == 200
    data = resp.json()
    expected_video_keys = {
        "id", "title", "description", "published_at",
        "view_count", "thumbnail_hq", "thumbnail_mq", "url", "embed_url",
    }
    if data["total"] > 0:
        for video in data["videos"]:
            missing = expected_video_keys - set(video.keys())
            assert not missing, f"Video missing keys: {missing}"


def test_youtube_videos_returns_dict_not_list(client):
    """GET /youtube/videos devuelve un dict, no una lista plana."""
    resp = client.get("/api/youtube/videos")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict), "Response should be a dict"
    assert "videos" in data
    assert "total" in data


def test_youtube_videos_total_matches_list_length(client):
    """El campo 'total' debe coincidir con len(videos)."""
    resp = client.get("/api/youtube/videos")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == len(data["videos"]), (
        f"total={data['total']} != len(videos)={len(data['videos'])}"
    )


def test_youtube_videos_channel_name(client):
    """El campo 'channel' contiene el handle de YouTube."""
    resp = client.get("/api/youtube/videos")
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel"] == "@Ministeriosfarooficial"


def test_youtube_videos_no_error_on_normal_call(client):
    """Incluso sin datos, la respuesta no debe tener un error 500."""
    resp = client.get("/api/youtube/videos")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    # No debe crashear


def test_youtube_videos_called_twice_returns_stable(client):
    """Llamar dos veces seguidas no debe cambiar la forma de la respuesta."""
    resp1 = client.get("/api/youtube/videos")
    resp2 = client.get("/api/youtube/videos")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    data1 = resp1.json()
    data2 = resp2.json()
    # Ambas respuestas deben tener la misma estructura
    assert set(data1.keys()) == set(data2.keys())
    assert isinstance(data1["videos"], list)
    assert isinstance(data2["videos"], list)
