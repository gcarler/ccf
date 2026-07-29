# CI/CD – Decisiones y Convenciones

**Última actualización:** 2026-07-29

Este documento registra decisiones de diseño del pipeline de CI/CD que no caben en un comentario de YAML y que pueden afectar el rendimiento o la corrección de los jobs.

## `fetch-depth` condicional en `frontend-quality`

En el job `frontend-quality` de `.github/workflows/ci.yml`, el paso `actions/checkout@v4` usa:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: ${{ github.event_name == 'pull_request' && 0 || 1 }}
```

### ¿Por qué?

- **`pull_request` necesita historial completo.** El paso *Detect new `any` in frontend test files* compara el HEAD del PR con la rama base (`origin/<base_ref>`) mediante `git diff origin/<base_ref>...HEAD`. Para calcular correctamente el diff entre dos refs separadas por muchos commits, el checkout debe contener suficiente historial; `fetch-depth: 0` (sin límite, historial completo) garantiza que el merge-base entre ambas ramas esté disponible.
- **`push` no necesita historial.** El paso *Detect new `any` in frontend test files* solo se ejecuta en `pull_request`:

  ```yaml
  - name: Detect new `any` in frontend test files
    if: github.event_name == 'pull_request'
    run: |
      git fetch origin ${{ github.base_ref }}:${{ github.base_ref }}
      python3 scripts/check-frontend-test-any.py --base-branch origin/${{ github.base_ref }}
  ```

  Por lo tanto, en los eventos de push a `main` o `develop` el job solo corre lint, type-check, tests y build. Ninguno de esos pasos requiere diff contra otra rama, así que un checkout superficial (`fetch-depth: 1`) es suficiente y mejora el tiempo de checkout.

### Comportamiento esperado

| Evento           | `fetch-depth` | Razón                                      |
|------------------|---------------|--------------------------------------------|
| `pull_request`   | `0`           | Permite `git diff` contra la rama base.    |
| `push`           | `1`           | Checkout superficial; diff no se usa.      |

El intercambio es que los builds de PR son ligeramente más lentos por descargar el historial completo, mientras que los builds de push se benefician del checkout superficial.

### Script afectado

- `scripts/check-frontend-test-any.py` (invocado con `--base-branch origin/<base_ref>`).

### Jobs con checkout superficial

Los demás jobs del workflow (`backend-quality`, `migrations-check`, `crm-tests`, `deploy-staging` y `deploy-production`) usan `fetch-depth: 1` porque no ejecutan ningún paso que requiera diff de git:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 1
```

Esto reduce el tiempo de checkout en builds de push y PR para todos los jobs que no necesitan historial completo.

## Monitoreo post-merge: Codecov con `fetch-depth: 1`

Los jobs `backend-quality` y `crm-tests` suben cobertura a Codecov v4 después de correr los tests. Tras cambiar sus checkouts a `fetch-depth: 1`, se debe verificar que Codecov sigue pudiendo resolver el commit base en pull requests. Según la documentación de Codecov, `fetch-depth: 1` es muy probable que cause problemas en PRs porque Codecov necesita historial para identificar el base commit.

### Indicadores a revisar tras el primer PR/push

1. **Mensajes de error en el step "Upload coverage" o "Upload CRM coverage":**
   - Warnings del tipo `Missing base report`.
   - Errores como `Could not find a usable base commit`.
2. **Comentario de Codecov en el PR:**
   - ¿Muestra "Diff" / "Patch" coverage?
   - ¿Aparece la comparación contra la rama base?
3. **Dashboard de Codecov:**
   - ¿Se asoció correctamente el reporte al SHA del commit?
   - ¿Se calculó el delta de cobertura en el PR?

### Fallback si hay problemas

Si Codecov no puede resolver el base commit con `fetch-depth: 1`, cambiar los jobs que suben cobertura a una profundidad condicional:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: ${{ github.event_name == 'pull_request' && 2 || 1 }}
```

O, si se prefiere una solución más robusta, usar `fetch-depth: 0` solo para PRs en esos jobs, igual que en `frontend-quality`.

### Referencias

- `.github/workflows/ci.yml` – jobs `frontend-quality`, `backend-quality`, `migrations-check`, `crm-tests`, `deploy-staging`, `deploy-production`.
- `scripts/check-frontend-test-any.py` – lógica de detección de `any` en tests.
- [Codecov Docs: Environment Specific Requirements](https://docs.codecov.com/docs/environment-specific-requirements)
