# Plataforma CCF

[![CCF CI/CD Pipeline](https://github.com/gcarler/ccf/actions/workflows/ci.yml/badge.svg)](https://github.com/gcarler/ccf/actions/workflows/ci.yml)

Plataforma institucional de la Comunidad Cristiana El Faro (CCF): sitio público, workspace autenticado, CRM pastoral, evangelismo, Academia, proyectos, CMS, finanzas, agenda, comunidad y servicios transversales.

> **Documentación principal en español:** [Guía general de la plataforma CCF](docs/GUIA_GENERAL_CCF.md)

## Inicio rápido de documentación

- [Guía general: arquitectura, módulos y flujos](docs/GUIA_GENERAL_CCF.md)
- [Reglas de arquitectura](REGLAS.md)
- [Glosario oficial](GLOSSARY.md)
- [Glosario de frontend](FRONTEND_GLOSARIO.md)
- [Arranque modular](docs/ARRANQUE_MODULAR_CCF.md)
- [Estado de arquitectura](docs/ESTADO_ARQUITECTURA_CCF.md)
- [Plataforma compartida: Auth, RBAC y UI base](docs/ESTADO_PLATAFORMA_COMPARTIDA.md)
- [Arquitectura MCP y herramientas privadas](docs/MCP_ARQUITECTURA_CCF.md)
- [Readiness de producción](PRODUCTION_READINESS.md)
- [Cambios recientes](CHANGELOG.md)

## Arquitectura resumida

- **Backend:** FastAPI, SQLAlchemy, Pydantic y Alembic en `backend/`.
- **Frontend:** Next.js 15.5.18, React y TypeScript en `frontend/`.
- **Base de datos:** SQLite para desarrollo/pruebas y PostgreSQL para staging/producción.
- **Identidad:** `personas.id` es el UUID canónico; `auth_users.id` comparte ese UUID.
- **Seguridad:** JWT, cookies HttpOnly, refresh coordinado, permisos modulares y aislamiento por `sede_id`.
- **API:** routers modulares registrados en `backend/app.py`.
- **MCP:** gateway de descubrimiento en `/mcp/platform`, contenido público/CMS en `/mcp` y `/mcp/cms`, y conexión MCP para los 32 módulos de la plataforma mediante rutas especializadas o `/mcp/{modulo}`, protegidas con JWT y RBAC de CCF.
- **Calidad:** pytest, Ruff, Vitest, Playwright, gates por módulo y CI/CD.

## Requisitos locales

- Python 3.12 o compatible con el entorno del proyecto.
- Node.js compatible con la configuración vigente del frontend.
- Dependencias Python de `requirements.txt`.
- Dependencias frontend de `frontend/package.json`.
- PostgreSQL para validar comportamiento equivalente a staging/producción.

## Comandos habituales

### Backend

```bash
# Desde la raíz del repositorio
python -m pytest -q -o addopts='' tests/test_smoke.py tests/test_structural_contracts.py
ruff check backend/
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm run typecheck
npm run lint
npm run test
npm run build
```

Para las pruebas E2E existen comandos por módulo en `frontend/package.json`, por ejemplo:

```bash
npm run test:e2e:platform
npm run test:e2e:crm
npm run test:e2e:academy
npm run test:e2e:cms
npm run test:e2e:evangelism
```

## CI/CD

El pipeline está definido en [`.github/workflows/ci.yml`](.github/workflows/ci.yml) y valida, según el job:

- calidad del backend: lint, tipado, tests y seguridad;
- calidad del frontend: lint, typecheck, tests y smoke E2E;
- migraciones de base de datos;
- pruebas funcionales de CRM y módulos críticos;
- build y readiness de despliegue;
- despliegue a staging/producción conforme a los gates configurados.

Consulta el [badge de CI/CD](https://github.com/gcarler/ccf/actions/workflows/ci.yml) para ver las ejecuciones recientes.

## Regla de trabajo

Antes de modificar código:

1. leer la [guía general](docs/GUIA_GENERAL_CCF.md);
2. identificar el módulo y leer su `ESTADO_*`, contrato API, matriz RBAC y checklist QA;
3. comprobar si el cambio afecta plataforma compartida, identidad, permisos o `sede_id`;
4. ejecutar el gate proporcional al cambio;
5. actualizar la documentación cuando cambie un contrato o flujo.

Para cambios en autenticación, permisos, `personas.id`, `sede_id`, `apiFetch`, layouts o componentes UI base, el owner es **plataforma compartida**, aunque el síntoma aparezca dentro de otro módulo.
