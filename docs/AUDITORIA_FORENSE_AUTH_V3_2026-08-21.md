# Auditoría Forense y Re-Certificación: Módulo Auth v3, Seguridad Global y RBAC

**Fecha:** 21 de agosto de 2026  
**Ecosistema:** Plataforma CCF (Comunidad Cristiana El Faro)  
**Alcance:** Frontend Auth (`AuthContext`, `workspaceAccess`, formularios), Backend FastAPI (`/api/v3/auth/*`), Modelos de Identidad (Axiomas 1 y 2), Matriz RBAC (`permissions.py`), Trazabilidad de Auditoría y Zero-Trust.  
**Equipo Auditor:** Enjambre de Auditoría Forense CCF (`ccf-forensic-master-auditor`).

---

## 1. Tabla de Estados — El Octógono Forense

| # | Dimensión Forense | Especialista Pericial | Estado Inicial | Estado Final (Re-certificación) |
|---|---|---|:---:|:---:|
| **1** | **Frontend Auth & Sesión** | `ccf-forensic-frontend-auditor` | 🔴 FALLÓ | 🟢 **PASÓ** |
| **2** | **Backend Auth v3 & RBAC** | `ccf-forensic-backend-auditor` | 🟢 PASÓ | 🟢 **PASÓ** |
| **3** | **Base de Datos & Identidad** | `ccf-forensic-db-auditor` | 🟢 PASÓ | 🟢 **PASÓ** |
| **4** | **Integración y Contratos** | `ccf-forensic-integration-auditor` | 🟢 PASÓ | 🟢 **PASÓ** |
| **5** | **Seguridad Zero-Trust** | `ccf-forensic-security-auditor` | 🟢 PASÓ | 🟢 **PASÓ** |
| **6** | **Trazabilidad & Observabilidad** | `ccf-forensic-traceability-auditor` | 🔴 FALLÓ | 🟢 **PASÓ** |
| **7** | **Resiliencia & Tolerancia** | `ccf-forensic-resilience-auditor` | 🟢 PASÓ | 🟢 **PASÓ** |
| **8** | **Rendimiento & Eficiencia** | `ccf-forensic-performance-auditor` | 🟢 PASÓ | 🟢 **PASÓ** |

---

## 2. Remediaciones Ejecutadas y Evidencia Forense

### A. Capa Frontend & Contratos de Runtime
1. **Página de Registro Público (`/register`):**
   * Eliminada la invocación al endpoint obsoleto `POST /v3/auth/register`.
   * Integrado el flujo de onboarding institucional con **Google SSO** (`/api/v3/auth/google`) y panel explicativo de aprovisionamiento ministerial para líderes y docentes.
2. **Validación de Longitud de Contraseñas:**
   * Estandarizada la longitud mínima a `>= 8 caracteres` en `frontend/src/app/reset-password/page.tsx` y `frontend/src/app/auth/reset/page.tsx` tanto en lógica de formulario como en atributos `minLength={8}`.
3. **Redirección Post-Login Compatible con RBAC:**
   * Eliminada la redirección ciega a `/plataforma/messages` en `login/page.tsx`, `auth/callback/page.tsx` y `plataforma/page.tsx`. Estandarizado el destino seguro a `/plataforma/academy` (accesible por todos los roles autenticados, incluidos estudiantes).
4. **Detección de Sesión Expirada:**
   * Normalizado el parsing de query parameters en `login/page.tsx` para aceptar tanto `?expired=1` como `?expired=true`.

### B. Capa Backend & Trazabilidad de Seguridad
5. **Auditoría de Intentos Fallidos en Usuarios Inexistentes:**
   * Actualizado el modelo `LogSeguridad.user_id` a `nullable=True` en `backend/models_auth.py`.
   * Habilitado `_log_security` para registrar eventos `LOGIN_FALLIDO_NO_EXISTE` ante ataques de diccionario o fuerza bruta sobre correos no registrados.
6. **Instrumentación de Logs de Seguridad:**
   * Inyectadas llamadas a `_log_security` en: `PATCH /me`, `POST /logout`, `POST /sessions/{id}/revoke`, `POST /sessions/revoke-all`, `POST /forgot-password` y `POST /reset-password`.
7. **Prevención de Reutilización de Contraseñas:**
   * Implementada validación contra las últimas 5 contraseñas de `HistorialContrasena` tanto en `PATCH /me` como en `POST /reset-password`, insertando el nuevo hash tras cada cambio exitoso.

---

## 3. Dictamen Final y Certificación

> **VEREDICTO:** El subsistema **Auth v3, Seguridad Global y Control de Acceso (RBAC)** cumple con el 100% de los criterios del Octógono Forense. El módulo se encuentra plenamente acoplado, libre de fracturas de contrato y **CERTIFICADO PARA DESPLIEGUE A PRODUCCIÓN (PRODUCTION-READY)**.
