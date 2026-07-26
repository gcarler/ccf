# API Contracts — Analytics

**Creado:** 2026-07-26

---

## GET /api/analytics/radar

**Auth:** `require_pastor_or_admin`

**Response 200 — `PastorRadarSchema`:**

```json
{
    "membresia_viva": 0,
    "bautismos_este_anio": 0,
    "estudiantes_activos": 0,
    "recaudacion_mes": 0.0
}
```

**Response 401/403:** Sin autenticación o sin permisos pastorales.

---

## GET /api/analytics/dashboard-metrics

**Auth:** `require_pastor_or_admin`

**Response 200 — `DashboardMetrics`:**

```json
{
    "active_students": 0,
    "completion_rate": 0.0,
    "certificates_issued": 0,
    "cards": [],
    "formal_stats": {},
    "no_formal_stats": {},
    "top_courses": []
}
```

**Response 401/403:** Sin autenticación o sin permisos pastorales.

---

## GET /api/analytics/events/summary

**Auth:** `require_pastor_or_admin`

**Response 200:**

```json
{
    "total_events": 0,
    "total_attendees": 0,
    "upcoming_events": 0
}
```

**Response 401/403:** Sin autenticación o sin permisos pastorales.

---

## Multi-tenant (Axioma 3)

Todos los endpoints filtran por `sede_id` del usuario autenticado vía `get_user_sede_id()`. Un superadmin sin sede ve todas las sedes.
