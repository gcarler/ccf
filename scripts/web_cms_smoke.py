from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class SmokeContext:
    base_url: str
    token: str | None = None


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _request(
    ctx: SmokeContext,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    auth: bool = False,
) -> tuple[int, Any]:
    url = f"{ctx.base_url}{path}"
    headers: dict[str, str] = {"Accept": "application/json"}
    payload = None

    if auth and ctx.token:
        headers["Authorization"] = f"Bearer {ctx.token}"

    if body is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url=url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw) if raw else None
            return response.getcode(), parsed
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        parsed = None
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
        return error.code, parsed


def _login(base_url: str, username: str, password: str) -> str:
    data = urllib.parse.urlencode({"username": username, "password": password}).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    candidates = [
        f"{base_url}/api/auth/login",
        f"{base_url}/api/auth/auth/login",
    ]

    last_error: Exception | None = None
    for login_url in candidates:
        req = urllib.request.Request(url=login_url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            token = payload.get("access_token")
            if not token:
                raise RuntimeError("Login succeeded but access_token is missing")
            return str(token)
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    raise RuntimeError(f"Login failed for known auth routes: {last_error}")


def _assert_status(label: str, status_code: int, expected: int) -> None:
    if status_code != expected:
        raise RuntimeError(f"{label}: expected {expected}, got {status_code}")


def run_smoke(ctx: SmokeContext) -> None:
    print("[1/8] Public content endpoint")
    status, _ = _request(ctx, "GET", "/api/content/faro_home_hero")
    _assert_status("GET /api/content/faro_home_hero", status, 200)

    print("[2/8] Public CMS testimonials endpoint")
    status, _ = _request(ctx, "GET", "/api/cms/testimonials")
    _assert_status("GET /api/cms/testimonials", status, 200)

    print("[3/8] Legacy testimonials alias removed")
    status, _ = _request(ctx, "GET", "/api/testimonials")
    _assert_status("GET /api/testimonials", status, 404)

    print("[4/8] Public CMS announcements endpoint")
    status, _ = _request(ctx, "GET", "/api/cms/announcements")
    _assert_status("GET /api/cms/announcements", status, 200)

    print("[5/8] Legacy announcements alias removed")
    status, _ = _request(ctx, "GET", "/api/announcements")
    _assert_status("GET /api/announcements", status, 404)

    print("[6/8] Protected admin endpoint without auth")
    status, _ = _request(ctx, "GET", "/api/admin/testimonials")
    _assert_status("GET /api/admin/testimonials (no auth)", status, 401)

    print("[7/8] Protected versions endpoint without auth")
    status, _ = _request(ctx, "GET", "/api/content/faro_home_hero/versions")
    _assert_status("GET /api/content/faro_home_hero/versions (no auth)", status, 401)

    if ctx.token:
        print("[8/8] Protected write endpoint with auth")
        status, _ = _request(
            ctx,
            "PATCH",
            "/api/content/faro_home_hero",
            body={
                "title": "Smoke Title",
                "content": json.dumps(
                    {
                        "eyebrow": "Comunidad FARO",
                        "title_lead": "Ilumina tu",
                        "title_accent": "Camino",
                        "description": "Smoke validation payload",
                        "primary_cta": "Ver",
                        "secondary_cta": "Participar",
                    },
                    ensure_ascii=False,
                ),
            },
            auth=True,
        )
        _assert_status("PATCH /api/content/faro_home_hero", status, 200)
    else:
        print("[8/8] Auth write test skipped (no credentials)")

    print("WEB_CMS_SMOKE_OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test for Web FARO + CMS endpoints")
    parser.add_argument("--base-url", default=os.getenv("CCF_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--username", default=os.getenv("CCF_SMOKE_USER"))
    parser.add_argument("--password", default=os.getenv("CCF_SMOKE_PASS"))
    args = parser.parse_args()

    base_url = _normalize_base_url(args.base_url)
    token = None
    if args.username and args.password:
        token = _login(base_url, args.username, args.password)

    ctx = SmokeContext(base_url=base_url, token=token)
    run_smoke(ctx)


if __name__ == "__main__":
    main()
