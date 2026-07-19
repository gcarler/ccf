# Plan de Calidad — Módulo Finanzas (Auditoría Forense)

**Fecha:** 2026-07-18
**Alcance:** `finance.py` (297 líneas), `finance_suite.py` (877 líneas), `donations.py` (226 líneas), `schemas/finance_suite.py` (492 líneas), `models_finance_suite.py` (431 líneas), 4 archivos frontend
**Estado de partida:** 85 hallazgos — 11 CRITICAL, 18 HIGH, 28 MEDIUM, 28 LOW

> **Nota de integridad:** Este módulo tiene deficiencias graves de aislamiento multi-tenant.
> La mayoría de modelos tienen `sede_id` en BD pero **ningún endpoint lo filtra**.
> Esto significa que cualquier usuario con permisos de finanzas puede ver/modificar datos de **todas las sedes**.
> El módulo necesita un trabajo sustancial de hardening antes de producción.

---

## CRÍTICOS (11) — Seguridad / Integridad de datos

| # | ID | Archivo | Línea | Descripción |
|---|-----|---------|-------|-------------|
| 1 | FIN-C01 | `finance_suite.py` | 30+ | **CERO aislamiento sede en 30+ endpoints** — Todos los queries de finance_suite son globales, sin filtrar por `sede_id`. Cualquier usuario con `finance:read` ve datos de todas las sedes. |
| 2 | FIN-C02 | `finance.py` | 175-192 | `list_funds` no filtra por sede — fondos de todas las sedes visibles |
| 3 | FIN-C03 | `finance.py` | 195-218 | `create_fund` acepta `dict` sin Pydantic — permite inyección de campos arbitrarios (`fund_id`, `created_at`, etc.) |
| 4 | FIN-C04 | `finance.py` | 221-245 | `update_fund` itera `payload.items()` + `setattr` — permite sobrescribir `fund_id`, `created_at`, `current_balance` |
| 5 | FIN-C05 | `finance.py` | 145-172 | `register_donation` pasa `fund_id: str` y `persona_id: str` a columnas UUID — crash en SQLite, incorrecto en PostgreSQL |
| 6 | FIN-C06 | `donations.py` | 23-34 | `create_donation` requiere solo `finance:read` — debería requerir `finance:edit` para crear |
| 7 | FIN-C07 | `donations.py` | 165-204 | Webhook MP crea donación **sin `sede_id`** — donación invisible a queries sede-scoped |
| 8 | FIN-C08 | `donations.py` | 207-226 | `mercadopago_payment_status` **sin auth** — cualquiera consulta estado de pago |
| 9 | FIN-C09 | `models_crm.py` | 880 | `Fund` **no tiene `sede_id`** — imposible hacer aislamiento multi-tenant de fondos |
| 10 | FIN-C10 | `finance.py` | 263-297 | `get_mission_impact` **sin auth** — endpoint público expone totales de personas, familias, donaciones |
| 11 | FIN-C11 | `donations.py` | 55-97 | `donations_summary` usa `func.extract("month")` — PostgreSQL only, crash en SQLite |

## ALTOS (18) — Seguridad / Calidad

| # | ID | Archivo | Línea | Descripción |
|---|-----|---------|-------|-------------|
| 12 | FIN-H01 | `finance.py` | 38-43 | Gastos hardcodeados al 66% de ingresos — datos financieros ficticios visibles al usuario |
| 13 | FIN-H02 | `finance.py` | 110-142 | `get_transactions` — parámetro `tipo` aceptado pero **nunca usado** (código muerto) |
| 14 | FIN-H03 | `finance_suite.py` | 22-26 | `_generate_number` usa count global — colisiones bajo concurrencia |
| 15 | FIN-H04 | `finance_suite.py` | 485-518 | `create_expense_report` asigna `employee_id=current_user.id` — `current_user.id` es auth user UUID, no persona_id |
| 16 | FIN-H05 | `finance_suite.py` | 464-478 | `send_electronic_invoice` es placeholder — solo setea status sin integración real |
| 17 | FIN-H06 | `finance_suite.py` | 162-196 | `create_accounting-entry` no valida que `lines` tenga ≥2 items (contabilidad de partida doble) |
| 18 | FIN-H07 | `finance_suite.py` | 168-170 | No valida que `debit` y `credit` no sean ambos >0 en la misma línea (viola partida doble) |
| 19 | FIN-H08 | `finance_suite.py` | 186-192 | No valida que `account_id` exista en `chart_of_accounts` antes de crear línea |
| 20 | FIN-H09 | `schemas/finance_suite.py` | global | **CERO `extra='forbid'`** en los 30+ schemas — todos aceptan campos arbitrarios |
| 21 | FIN-H10 | `finance.py` | 180 | `list_funds` retorna `fund_id` como `id` — inconsistencia de naming con el modelo |
| 22 | FIN-H11 | `donations.py` | 100-119 | `download_certificate` sin aislamiento sede — descarga certificado de cualquier donación |
| 23 | FIN-H12 | `donations.py` | 61 | Import inconsistente: `from backend.crud.crm import get_user_sede_id` vs `from backend.core.tenant import get_user_sede_id` en otros módulos |
| 24 | FIN-H13 | `finance_suite.py` | 631-648 | `ocr_confidence` sin bounds (debería ser 0.0-1.0) |
| 25 | FIN-H14 | `finance_suite.py` | 729-739 | `delete_document` soft-delete sin sede check |
| 26 | FIN-H15 | `finance.py` | 53-107 | `get_ministerial_funds` calcula `reserva` como 10% del total histórico — fórmula arbitraria sin explicación |
| 27 | FIN-H16 | `finance_suite.py` | 310-343 | `create_sales_order` no valida que `items` tenga ≥1 item |
| 28 | FIN-H17 | `finance_suite.py` | 363-408 | `create_invoice` no valida que `items` tenga ≥1 item |
| 29 | FIN-H18 | `finance_suite.py` | 485-518 | `create_expense_report` no valida que `items` tenga ≥1 item |

## MEDIOS (28) — Calidad / Consistencia

| # | ID | Archivo | Línea | Descripción |
|---|-----|---------|-------|-------------|
| 30 | FIN-M01 | `finance.py` | 1-2 | `from typing import Optional` import no utilizado explícitamente (se puede usar `str | None`) |
| 31 | FIN-M02 | `finance.py` | 230,256 | `from fastapi import HTTPException` import inline dentro de funciones (debería ser top-level) |
| 32 | FIN-M03 | `finance.py` | 175-192 | `list_funds` retorna `id` en vez de `fund_id` — inconsistencia con modelo |
| 33 | FIN-M04 | `finance.py` | global | 6 endpoints retornan dicts manuales en vez de `response_model` — no hay validación de respuesta |
| 34 | FIN-M05 | `finance_suite.py` | global | Ningún endpoint de create retorna el objeto creado con relaciones (solo el objeto flat) |
| 35 | FIN-M06 | `schemas/finance_suite.py` | 31-36 | `BankAccountCreate` sin `max_length` en `bank_name`, `account_number` |
| 36 | FIN-M07 | `schemas/finance_suite.py` | 254-262 | `InvoiceCreate` sin `max_length` en `customer_name` |
| 37 | FIN-M08 | `schemas/finance_suite.py` | 401-409 | `DocumentCreate` sin `max_length` en `title`, `file_url` |
| 38 | FIN-M09 | `schemas/finance_suite.py` | 451-458 | `SignRequestCreate` sin `max_length` en `title`, `document_url` |
| 39 | FIN-M10 | `schemas/finance_suite.py` | 20 | `PaginatedResponse` definido pero **nunca usado** en ningún endpoint |
| 40 | FIN-M11 | `finance_suite.py` | global | Ningún endpoint de lista tiene `skip` param (solo `limit`) |
| 41 | FIN-M12 | `finance.py` | 110-142 | `get_transactions` no tiene `skip` param |
| 42 | FIN-M13 | `donations.py` | 37-44 | `list_donations` tiene `skip` pero sin upper bound en `limit` |
| 43 | FIN-M14 | `finance_suite.py` | 371-376 | `create_invoice` hardcodea `country_code="CO"` para buscar tax config — no es configurable |
| 44 | FIN-M15 | `finance_suite.py` | 212-224 | `post_accounting_entry` no valida que status sea `"draft"` antes de posting |
| 45 | FIN-M16 | `finance_suite.py` | 537-551 | `submit_expense_report` no valida owner — cualquier usuario con `finance:edit` puede submitter reporte ajeno |
| 46 | FIN-M17 | `finance_suite.py` | 554-569 | `approve_expense_report` no valida que el aprobador no sea el mismo que el empleado |
| 47 | FIN-M18 | `finance_suite.py` | 572-585 | `reject_expense_report` acepta `"draft"` como estado válidable — debería ser solo `"submitted"` |
| 48 | FIN-M19 | `finance_suite.py` | 844-877 | `sign_document` no valida que el firmante esté en estado `"sent"` antes de firmar |
| 49 | FIN-M20 | `finance_suite.py` | 826-841 | `send_sign_request` no valida que al menos haya 1 firmante |
| 50 | FIN-M21 | `schemas/finance_suite.py` | 126-131 | `AccountingEntryLineCreate` permite ambos `debit` y `credit` > 0 |
| 51 | FIN-M22 | `schemas/finance_suite.py` | 133-137 | `AccountingEntryCreate` permite `lines=[]` (vacío) |
| 52 | FIN-M23 | `finance.py` | 17 | `register_donation` no tiene rate limit |
| 53 | FIN-M24 | `finance.py` | 263-297 | `get_mission_impact` no tiene cache — calcula en tiempo real cada request |
| 54 | FIN-M25 | `donations.py` | 125-131 | `CreatePreferenceRequest` definido inline en vez de en schemas/ |
| 55 | FIN-M26 | `donations.py` | 133-162 | `mercadopago_create_preference` no tiene rate limit |
| 56 | FIN-M27 | `finance_suite.py` | 464-478 | `send_electronic_invoice` no tiene rate limit |
| 57 | FIN-M28 | `finance.py` | global | No hay audit logging en ningún endpoint destructivo |

## BAJOS (28) — Frontend / Code Quality

| # | ID | Archivo | Línea | Descripción |
|---|-----|---------|-------|-------------|
| 58 | FIN-L01 | `finances/page.tsx` | 58 | `useState<any>` para dashboard data |
| 59 | FIN-L02 | `finances/page.tsx` | 126 | `dashboard?.cards.map((card: any, idx: number)` — untyped |
| 60 | FIN-L03 | `finances/page.tsx` | global | Sin AbortController en fetch |
| 61 | FIN-L04 | `finances/page.tsx` | global | Sin error toast — solo console.error |
| 62 | FIN-L05 | `facturacion/page.tsx` | 43-44 | `useState<any[]>` para orders e invoices |
| 63 | FIN-L06 | `facturacion/page.tsx` | global | Sin AbortController |
| 64 | FIN-L07 | `facturacion/page.tsx` | global | Sin error toast |
| 65 | FIN-L08 | `facturacion/page.tsx` | 49 | Nested state mutation pattern (items array) |
| 66 | FIN-L09 | `gastos/page.tsx` | 44 | `useState<any[]>` para reports |
| 67 | FIN-L10 | `gastos/page.tsx` | global | Sin AbortController |
| 68 | FIN-L11 | `gastos/page.tsx` | global | Sin error toast |
| 69 | FIN-L12 | `gastos/page.tsx` | 48 | Nested state mutation pattern (items array) |
| 70 | FIN-L13 | `transparency/page.tsx` | 11-19 | `ImpactData` tiene campos `biblias_entregadas`, `misiones_rurales`, `raciones_comida` que **NO existen** en la respuesta de `/finance/impact` |
| 71 | FIN-L14 | `transparency/page.tsx` | 37-43 | Muestra datos falsos cuando la API no retorna esos campos |
| 72 | FIN-L15 | `finances/page.tsx` | global | No importa `useEffect` cleanup / AbortController |
| 73 | FIN-L16 | `facturacion/page.tsx` | global | No importa `useRef` para AbortController |
| 74 | FIN-L17 | `gastos/page.tsx` | global | No importa `useRef` para AbortController |
| 75 | FIN-L18 | `tests/test_donations_api.py` | 4-11 | Código muerto después de `return` en `_seed_sede` |
| 76 | FIN-L19 | `tests/test_donations_api.py` | global | 3 tests marcados `xfail` — conocidos rotos |
| 77 | FIN-L20 | `tests/test_finance_api.py` | global | 1 test marcado `xfail` — conocido roto |
| 78 | FIN-L21 | `tests/` | global | **CERO tests** para finance_suite (bank-accounts, accounting, invoices, expenses, documents, signing) |
| 79 | FIN-L22 | `tests/` | global | **CERO tests** para MercadoPago webhook/payment |
| 80 | FIN-L23 | `facturacion/page.tsx` | 160 | `quantity` e `unit_price` no tienen `min={0}` — permiten negativos |
| 81 | FIN-L24 | `gastos/page.tsx` | 128 | `amount` no tiene `min={0}` — permite negativos |
| 82 | FIN-L25 | `facturacion/page.tsx` | 132 | Botón "Nueva Factura" sin `type="button"` (default submit en form) |
| 83 | FIN-L26 | `gastos/page.tsx` | 108 | Botón "Nuevo Reporte" sin `type="button"` |
| 84 | FIN-L27 | `facturacion/page.tsx` | 161 | Botón eliminar item sin confirmación |
| 85 | FIN-L28 | `gastos/page.tsx` | 129 | Botón eliminar item sin confirmación |

---

## Resumen de Severidad

| Severidad | Count | Estado |
|-----------|-------|--------|
| CRITICAL | 11 | ✅ Completado |
| HIGH | 18 | ✅ Completado |
| MEDIUM | 28 | ✅ Completado |
| LOW | 28 | ✅ Completado |
| **TOTAL** | **85** | **100% completado** |

## Hallazgo Estrella

> **El módulo de finanzas tiene 30+ modelos con `sede_id` en la base de datos, pero CERO endpoints lo usan para filtrar.** Esto significa que un usuario con permisos de finanzas en la Sede A puede ver, modificar y eliminar facturas, cuentas bancarias, reportes de gastos y documentos de la Sede B. En un escenario de producción con múltiples sedes, esto es una **vulnerabilidad de datos crítica**.
