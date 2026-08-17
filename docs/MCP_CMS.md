# MCP del CMS CCF

## Endpoint

El servidor MCP está embebido en FastAPI y se publica en:

```text
/api/mcp/
```

El transporte utilizado es Streamable HTTP. Todas las peticiones requieren un
token JWT de CCF en el encabezado:

```text
Authorization: Bearer <CCF_ACCESS_TOKEN>
```

El token se valida con el mismo resolver de autenticación que la API REST. El
usuario debe estar activo y conservar los permisos CMS correspondientes.

## Herramientas

### Lectura

- `list_sites`
- `list_pages`
- `get_page`
- `preview_page`
- `list_themes`
- `list_menus`

### Escritura

- `create_page_draft`
- `update_page_draft`
- `publish_page`

Las herramientas de escritura reutilizan las funciones del CMS v2. No acceden
directamente a la base de datos y conservan validaciones, scope por `sede_id`,
workflow, caché e indexación.

## Permisos

| Operación | Permiso | Rol adicional |
|---|---|---|
| Lectura CMS | `cms:read` | Ninguno |
| Crear o editar draft | `cms:edit` | Rol editor CMS |
| Publicar, despublicar o archivar | `cms:edit` | Rol publisher CMS |

Las anotaciones MCP marcan las lecturas como `readOnlyHint` y las operaciones
de workflow como `destructiveHint`, para que el cliente pueda aplicar sus
controles de aprobación.

## Conexión con ChatGPT

1. Desplegar el backend con HTTPS.
2. Configurar la aplicación MCP personalizada del workspace de ChatGPT.
3. Usar la URL completa del endpoint, por ejemplo `https://dominio/api/mcp/`.
4. Configurar el envío del token CCF como `Authorization: Bearer ...`.
5. Probar primero `list_sites` y `get_page`.
6. Habilitar las herramientas de escritura después de validar el scope de sede.

El token JWT actual de CCF tiene la duración configurada para los access tokens
de la plataforma. Para una conexión persistente de usuarios de ChatGPT, el
siguiente endurecimiento recomendado es añadir un proveedor OAuth MCP que
delegue el login en Auth v3 y emita tokens MCP de corta duración.

## Pruebas

```bash
./venv/bin/pytest -q tests/test_mcp_cms.py
```
