# Projects API QA Battery

This checklist validates the full `Projects` module flow in backend (`/api/projects`).

## Prerequisites

- Backend running (default: `http://localhost:8000`)
- A valid bearer token with `staff/admin` permissions for create/update/delete operations

```bash
export BASE_URL="http://localhost:8000"
export TOKEN="<paste_access_token_here>"
```

## Automated Smoke Script

Use the scripted smoke flow when you want fast end-to-end validation:

```bash
python scripts/projects_api_smoke.py --base-url "$BASE_URL" --token "$TOKEN"
```

Optional auth mode (without pre-generated token):

```bash
python scripts/projects_api_smoke.py --base-url "$BASE_URL" --username "admin@example.com" --password "<password>"
```

Optional keep generated test data:

```bash
python scripts/projects_api_smoke.py --base-url "$BASE_URL" --token "$TOKEN" --keep-data
```

## 1) Projects CRUD

### 1.1 Create project

```bash
curl -sS -X POST "$BASE_URL/api/projects/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "QA Proyecto Integral",
    "description": "Proyecto para validar flujos de QA",
    "status": "planning",
    "color": "#2563eb"
  }'
```

Expected:
- `201 Created`
- response includes `id`, `title`, `status`, `created_at`

Save `project_id` from response.

### 1.2 List projects

```bash
curl -sS "$BASE_URL/api/projects/?q=QA%20Proyecto&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
- `200 OK`
- array contains created project

### 1.3 Get project detail

```bash
curl -sS "$BASE_URL/api/projects/<project_id>" \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
- `200 OK`
- object contains `tasks` (array)

### 1.4 Update project

```bash
curl -sS -X PATCH "$BASE_URL/api/projects/<project_id>" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"active","description":"Proyecto QA actualizado"}'
```

Expected:
- `200 OK`
- `status` changed to `active`

## 2) Tasks CRUD

### 2.1 Create task from project route

```bash
curl -sS -X POST "$BASE_URL/api/projects/<project_id>/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Tarea QA principal",
    "description":"Validar flujo Kanban",
    "status":"todo",
    "priority":"high"
  }'
```

Expected:
- `201 Created`
- response includes `id`, `project_id`

Save `task_id` from response.

### 2.2 List tasks by project

```bash
curl -sS "$BASE_URL/api/projects/<project_id>/tasks" \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
- `200 OK`
- array contains `task_id`

### 2.3 Global tasks list with filters

```bash
curl -sS "$BASE_URL/api/projects/tasks?project_id=<project_id>&status=todo" \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
- `200 OK`
- all returned tasks match filter

### 2.4 Update task status (kanban)

```bash
curl -sS -X PATCH "$BASE_URL/api/projects/tasks/<task_id>" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"in_progress"}'
```

Expected:
- `200 OK`
- `status = in_progress`

### 2.5 Get single task

```bash
curl -sS "$BASE_URL/api/projects/tasks/<task_id>" \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
- `200 OK`
- object contains `supplies` array

## 3) Supplies CRUD

### 3.1 Create supply

```bash
curl -sS -X POST "$BASE_URL/api/projects/tasks/<task_id>/supplies" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item_name":"Cable HDMI","quantity":2,"status":"pending"}'
```

Expected:
- `201 Created`
- response includes `id`, `task_id`

Save `supply_id`.

### 3.2 List supplies

```bash
curl -sS "$BASE_URL/api/projects/tasks/<task_id>/supplies" \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
- `200 OK`
- array contains `supply_id`

### 3.3 Update supply

```bash
curl -sS -X PATCH "$BASE_URL/api/projects/tasks/<task_id>/supplies/<supply_id>" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"ready","quantity":3}'
```

Expected:
- `200 OK`
- values updated

### 3.4 Delete supply

```bash
curl -sS -X DELETE "$BASE_URL/api/projects/tasks/<task_id>/supplies/<supply_id>" \
  -H "Authorization: Bearer $TOKEN" -i
```

Expected:
- `204 No Content`

## 4) Inbox, activity and analytics

### 4.1 Inbox

```bash
curl -sS "$BASE_URL/api/projects/inbox?limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
- `200 OK`
- array of items with `type`, `project`, `content`, `is_read`

### 4.2 Activities

```bash
curl -sS "$BASE_URL/api/projects/activities?limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
- `200 OK`
- array of activity rows

### 4.3 Portfolio summary

```bash
curl -sS "$BASE_URL/api/projects/summary" \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
- `200 OK`
- array with `project_status`, `total_projects`, `completion_ratio`

### 4.4 Workload summary

```bash
curl -sS "$BASE_URL/api/projects/workload" \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
- `200 OK`
- array with `assignee_id`, `open_tasks`, `overdue_tasks`

## 5) Comments collaboration

### 5.1 Create project comment

```bash
curl -sS -X POST "$BASE_URL/api/projects/<project_id>/comments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Comentario QA","task_id":<task_id>}'
```

Expected:
- `201 Created`
- response includes `id`, `author_name`, `is_resolved=false`

Save `comment_id`.

### 5.2 List project comments

```bash
curl -sS "$BASE_URL/api/projects/<project_id>/comments?unresolved_only=true" \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
- `200 OK`
- array contains `comment_id`

### 5.3 Resolve comment

```bash
curl -sS -X PATCH "$BASE_URL/api/projects/comments/<comment_id>" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_resolved":true}'
```

Expected:
- `200 OK`
- `is_resolved = true`

### 5.4 Mark inbox item as read

```bash
curl -sS -X POST "$BASE_URL/api/projects/inbox/comment-<comment_id>/read" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_read":true}' -i
```

Expected:
- `204 No Content`

## 6) Cleanup

### 6.1 Delete comment

```bash
curl -sS -X DELETE "$BASE_URL/api/projects/comments/<comment_id>" \
  -H "Authorization: Bearer $TOKEN" -i
```

Expected:
- `204 No Content`

### 6.2 Delete task

```bash
curl -sS -X DELETE "$BASE_URL/api/projects/tasks/<task_id>" \
  -H "Authorization: Bearer $TOKEN" -i
```

Expected:
- `204 No Content`

### 6.3 Delete project

```bash
curl -sS -X DELETE "$BASE_URL/api/projects/<project_id>" \
  -H "Authorization: Bearer $TOKEN" -i
```

Expected:
- `204 No Content`

## 7) Permission checks (negative)

Run create/update/delete requests with a non-staff token.

Expected:
- `403 Forbidden` on protected operations (`POST/PATCH/DELETE` sensitive endpoints)
