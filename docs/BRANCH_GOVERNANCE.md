# Gobierno de ramas y worktrees CCF

**Estado:** vigente
**Corte del inventario:** 2026-08-23 (actualizado tras integrar tipografía pastoral)
**Rama canónica:** `main`
**`origin/main` actual:** `43ee8ae1`

Este documento es el mapa operativo para todos los agentes que trabajen en el
repositorio CCF. Complementa `AGENTS_RULES_CCF.md`, `REGLAS.md` y la sección de
commit/push de `docs/RUNBOOK_PRODUCCION.md`.

## Reglas invariantes

1. `origin/main` es la única base canónica de integración y producción.
2. Cada módulo trabaja desde su rama propietaria y, cuando sea necesario, su
   propio worktree.
3. Una rama activa no se borra ni se archiva por antigüedad: primero se revisa
   su divergencia, su último commit y si tiene trabajo pendiente.
4. Una rama se archiva solo cuando su trabajo está integrado o existe una copia
   archivada verificable. El nombre de archivo remoto es
   `archive/merged/<rama-normalizada>`.
5. Los worktrees con cambios sin commit pertenecen al agente que los creó. No
   se eliminan ni se reutilizan sin revisión explícita.
6. Las ramas nuevas se publican desde una base limpia de `origin/main` y pasan
   `scripts/push_branch.sh`; no se publica una rama histórica que mezcle varios
   módulos para “rescatar” un commit.

## Ramas remotas activas

Estas ramas contienen trabajo pendiente y no deben fusionarse automáticamente:

| Área | Rama |
|---|---|
| Estructural | `feature/modulo-estructural` |
| Academy | `feature/academy` |
| Contextual / eventos | `feat/contextual-roles-recovery` |
| Evangelismo QA | `feature/evangelism-quality` |
| Eventos Evangelismo | `feature/events-evangelism` |
| Mensajería | `feature/messaging` |
| CMS | `feat/cms-quality-improvements` |
| CMS / Nosotros histórico | `feat/cms-nosotros-stats` |
| Frontend UI | `feature/frontend-ui` |
| Proyectos / Whiteboard | `feature/projects-whiteboard` |
| Seguridad | `feature/security-hardening` |
| Paleta | `fix/color-palette-regression` |
| Workspace | `chore/ignore-dev-build` |

La pertenencia a esta tabla no significa que una rama esté lista para merge.
Cada integración debe revisar conflictos, ownership, tests y contrato del
módulo. El protocolo vigente está integrado en `main` y en
`AGENTS_RULES_CCF.md`.

## Resultado de la auditoría de integración

Al comparar cada rama contra `origin/main` con `git merge-tree` el 2026-08-23:

- `feature/ops-push-protocol` y `docs/branch-governance`: integrables sin
  conflictos; fueron reunidas en `integration/branch-governance-to-main` y ya
  están integradas en `main`.
- Las siguientes ramas tienen conflictos y requieren un plan propio; no se
  fusionan automáticamente:

| Rama | Conflictos detectados |
|---|---:|
| `chore/ignore-dev-build` | 9 |
| `feat/cms-nosotros-stats` | 229 |
| `feat/cms-quality-improvements` | 22 |
| `feat/contextual-roles-recovery` | 1 |
| `feature/academy` | 7 |
| `feature/evangelism-quality` | 5 |
| `feature/events-evangelism` | 16 |
| `feature/frontend-ui` | 2 |
| `feature/messaging` | 232 |
| `feature/modulo-estructural` | 31 |
| `feature/projects-whiteboard` | 2 |
| `feature/security-hardening` | 3 |
| `fix/color-palette-regression` | 7 |

Un conflicto no implica que el trabajo sea descartable: indica que debe
extraerse por commits funcionales o reconstruirse sobre `origin/main` con QA
del módulo. La rama conflictiva permanece activa hasta cerrar esa revisión.

Los contadores son evidencia del análisis de `merge-tree` en este corte, no una
estimación del número de archivos que deben conservarse. La decisión de
integración se toma por commit funcional y ownership del módulo.

## Integraciones cerradas en este corte

Estas unidades ya pasaron su gate, fueron integradas en `main` y no deben
republicarse como ramas activas:

- Expiración de QR de inscripción a 365 días en check-in y ticket público.
- Fix y contenido de testimonios pastorales públicos, incluido Luis Ricardo.
- Normalización de color e interlineado en todas las vistas públicas de pastores.

Los SHA funcionales de referencia son `dc16819d`, `365d7f5a` y `e479607c`;
el merge vigente de `main` es `43ee8ae1`.

## Ramas archivadas

Las ramas integradas se conservan bajo `origin/archive/merged/` para trazabilidad
y rollback documental. No se recrea una rama activa con el mismo nombre salvo
que exista una tarea nueva y una base explícita en `origin/main`.

La integración de gobierno quedó archivada en:

- `archive/merged/feature-ops-push-protocol`
- `archive/merged/docs-branch-governance`
- `archive/merged/integration-branch-governance-to-main`
- `archive/merged/integration-pastores-production`
- `archive/merged/integration-qr-expiry-into-main`
- `archive/merged/integration-qr-expiry-main-final`
- `archive/merged/fix-pastores-typography`
- `archive/merged/docs-branch-governance-current`
- `archive/merged/docs-branch-governance-archive-list`

## Procedimiento de mantenimiento

Ejecutar desde un worktree limpio:

```bash
git fetch origin --prune
git branch -r --merged origin/main
git worktree list
git status --short --branch
```

Para cada rama activa, registrar:

- divergencia respecto a `origin/main`;
- último commit y propietario;
- worktree asociado y si está limpio;
- decisión: integrar, mantener activa o archivar;
- evidencia de tests y revisión.

Nunca usar `git branch -D`, borrar una rama remota o forzar un push como método
de limpieza general. Las excepciones deben tener objetivo exacto, respaldo o
archivo remoto y registro en el commit/documento de la operación.

## Criterio de cierre del inventario

El inventario está ordenado cuando:

- `main` apunta a la última integración aprobada;
- cada rama activa tiene propietario y propósito identificable;
- no existen worktrees detached temporales sin propósito;
- los residuos locales con remoto archivado fueron retirados;
- los pushes se hicieron con `scripts/push_branch.sh` y SHA confirmado;
- las decisiones pendientes están registradas aquí o en el documento del módulo.
