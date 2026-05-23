from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class SmokeContext:
    base_url: str
    token: str
    project_id: int | None = None
    task_id: int | None = None
    supply_id: int | None = None
    comment_id: int | None = None


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _request(
    ctx: SmokeContext,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    expect_status: int | None = None,
) -> tuple[int, Any]:
    url = f"{ctx.base_url}{path}"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {ctx.token}"}
    payload = None

    if body is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url=url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw) if raw else None
            status_code = response.getcode()
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        parsed = None
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
        status_code = error.code

    if expect_status is not None and status_code != expect_status:
        raise RuntimeError(
            f"Request failed: {method} {path} expected {expect_status} got {status_code} payload={parsed}"
        )
    return status_code, parsed


def _login(base_url: str, username: str, password: str) -> str:
    login_url = f"{base_url}/api/auth/login"
    data = urllib.parse.urlencode({"username": username, "password": password}).encode(
        "utf-8"
    )
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    req = urllib.request.Request(
        url=login_url, data=data, headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read().decode("utf-8")
        payload = json.loads(raw)
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Login succeeded but access_token is missing")
    return str(token)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_smoke(ctx: SmokeContext, keep_data: bool = False) -> None:
    print("[1/13] Creating project...")
    _, project = _request(
        ctx,
        "POST",
        "/api/projects/",
        body={
            "title": "QA Proyecto Integral (Smoke)",
            "description": "Validacion automatizada de endpoints",
            "status": "planning",
            "color": "#2563eb",
        },
        expect_status=201,
    )
    _assert(isinstance(project, dict), "Project create did not return JSON object")
    ctx.project_id = int(project["id"])

    print("[2/13] Listing projects...")
    _, projects = _request(
        ctx,
        "GET",
        "/api/projects/?q=QA%20Proyecto%20Integral%20(Smoke)&limit=10",
        expect_status=200,
    )
    _assert(isinstance(projects, list), "Projects list must be an array")
    _assert(
        any(int(row.get("id", -1)) == ctx.project_id for row in projects),
        "Created project not found in list",
    )

    print("[3/13] Reading project detail...")
    _, project_detail = _request(
        ctx, "GET", f"/api/projects/{ctx.project_id}", expect_status=200
    )
    _assert(
        project_detail.get("title") == "QA Proyecto Integral (Smoke)",
        "Project detail title mismatch",
    )

    print("[4/13] Updating project status...")
    _, updated_project = _request(
        ctx,
        "PATCH",
        f"/api/projects/{ctx.project_id}",
        body={"status": "active", "description": "Proyecto actualizado por smoke"},
        expect_status=200,
    )
    _assert(updated_project.get("status") == "active", "Project status update failed")

    print("[5/13] Creating project task...")
    _, task = _request(
        ctx,
        "POST",
        f"/api/projects/{ctx.project_id}/tasks",
        body={
            "title": "Tarea smoke",
            "description": "Tarea creada para QA automatizada",
            "status": "todo",
            "priority": "high",
        },
        expect_status=201,
    )
    _assert(isinstance(task, dict), "Task create did not return JSON object")
    ctx.task_id = int(task["id"])

    print("[6/13] Listing tasks by project...")
    _, project_tasks = _request(
        ctx, "GET", f"/api/projects/{ctx.project_id}/tasks", expect_status=200
    )
    _assert(isinstance(project_tasks, list), "Project tasks list must be an array")
    _assert(
        any(int(row.get("id", -1)) == ctx.task_id for row in project_tasks),
        "Created task not found in project tasks",
    )

    print("[7/13] Updating task state...")
    _, updated_task = _request(
        ctx,
        "PATCH",
        f"/api/projects/tasks/{ctx.task_id}",
        body={"status": "in_progress"},
        expect_status=200,
    )
    _assert(updated_task.get("status") == "in_progress", "Task status update failed")

    print("[8/13] Creating and updating supply...")
    _, supply = _request(
        ctx,
        "POST",
        f"/api/projects/tasks/{ctx.task_id}/supplies",
        body={"item_name": "Cable HDMI", "quantity": 2, "status": "pending"},
        expect_status=201,
    )
    _assert(isinstance(supply, dict), "Supply create did not return JSON object")
    ctx.supply_id = int(supply["id"])

    _, updated_supply = _request(
        ctx,
        "PATCH",
        f"/api/projects/tasks/{ctx.task_id}/supplies/{ctx.supply_id}",
        body={"status": "ready", "quantity": 3},
        expect_status=200,
    )
    _assert(updated_supply.get("status") == "ready", "Supply status update failed")

    print("[9/13] Creating and resolving project comment...")
    _, comment = _request(
        ctx,
        "POST",
        f"/api/projects/{ctx.project_id}/comments",
        body={"content": "Comentario QA automatizado", "task_id": ctx.task_id},
        expect_status=201,
    )
    _assert(isinstance(comment, dict), "Comment create did not return object")
    ctx.comment_id = int(comment["id"])

    _, comments = _request(
        ctx,
        "GET",
        f"/api/projects/{ctx.project_id}/comments?limit=20",
        expect_status=200,
    )
    _assert(isinstance(comments, list), "Comments list must be an array")
    _assert(
        any(int(row.get("id", -1)) == ctx.comment_id for row in comments),
        "Created comment not found",
    )

    _, resolved_comment = _request(
        ctx,
        "PATCH",
        f"/api/projects/comments/{ctx.comment_id}",
        body={"is_resolved": True},
        expect_status=200,
    )
    _assert(bool(resolved_comment.get("is_resolved")), "Comment resolve failed")

    print("[10/13] Checking inbox read toggle and activities...")
    _, inbox = _request(ctx, "GET", "/api/projects/inbox?limit=10", expect_status=200)
    _, activities = _request(
        ctx, "GET", "/api/projects/activities?limit=10", expect_status=200
    )
    _assert(isinstance(inbox, list), "Inbox must return an array")
    _assert(isinstance(activities, list), "Activities must return an array")
    _assert(
        any(row.get("id") == f"comment-{ctx.comment_id}" for row in inbox),
        "Comment not reflected in inbox",
    )

    _request(
        ctx,
        "POST",
        f"/api/projects/inbox/comment-{ctx.comment_id}/read",
        body={"is_read": True},
        expect_status=204,
    )

    _, inbox_after_read = _request(
        ctx, "GET", "/api/projects/inbox?limit=20", expect_status=200
    )
    for item in inbox_after_read:
        if item.get("id") == f"comment-{ctx.comment_id}":
            _assert(bool(item.get("is_read")), "Inbox read toggle not persisted")
            break

    print("[11/13] Checking summary and workload analytics...")
    _, summary = _request(ctx, "GET", "/api/projects/summary", expect_status=200)
    _, workload = _request(ctx, "GET", "/api/projects/workload", expect_status=200)
    _assert(isinstance(summary, list), "Summary must return an array")
    _assert(isinstance(workload, list), "Workload must return an array")

    if keep_data:
        print("[12/13] Skipping cleanup (--keep-data enabled)")
        print(
            f"Done. project_id={ctx.project_id} task_id={ctx.task_id} supply_id={ctx.supply_id} comment_id={ctx.comment_id}"
        )
        return

    print("[12/13] Cleaning up created records...")
    if ctx.comment_id is not None:
        _request(
            ctx, "DELETE", f"/api/projects/comments/{ctx.comment_id}", expect_status=204
        )
    if ctx.supply_id is not None and ctx.task_id is not None:
        _request(
            ctx,
            "DELETE",
            f"/api/projects/tasks/{ctx.task_id}/supplies/{ctx.supply_id}",
            expect_status=204,
        )
    if ctx.task_id is not None:
        _request(ctx, "DELETE", f"/api/projects/tasks/{ctx.task_id}", expect_status=204)
    if ctx.project_id is not None:
        _request(ctx, "DELETE", f"/api/projects/{ctx.project_id}", expect_status=204)

    print("[13/13] Cleanup complete")
    print("Smoke QA completed successfully.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Runs automated smoke tests for /api/projects endpoints"
    )
    parser.add_argument(
        "--base-url", default=os.getenv("BASE_URL", "http://localhost:8000")
    )
    parser.add_argument("--token", default=os.getenv("TOKEN"))
    parser.add_argument("--username", default=os.getenv("QA_USERNAME"))
    parser.add_argument("--password", default=os.getenv("QA_PASSWORD"))
    parser.add_argument(
        "--keep-data", action="store_true", help="Do not delete created records"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = _normalize_base_url(args.base_url)
    token = args.token

    if not token:
        if args.username and args.password:
            token = _login(base_url, args.username, args.password)
            print("Authenticated via /api/auth/login")
        else:
            print(
                "Missing credentials. Provide --token or both --username and --password."
            )
            return 2

    ctx = SmokeContext(base_url=base_url, token=token)
    try:
        run_smoke(ctx, keep_data=args.keep_data)
        return 0
    except Exception as exc:
        print(f"Smoke QA failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
