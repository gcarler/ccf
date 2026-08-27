# Sandbox Docker de CCF

Este Compose levanta una copia aislada de la plataforma para validar la
containerización sin tocar los procesos PM2, PostgreSQL, Redis, SeaweedFS ni
los volúmenes de producción.

## Arranque

1. Copiar `.env.docker.example` a `.env.docker` y reemplazar los valores de
   sandbox.
2. Ejecutar:

```bash
docker compose --env-file .env.docker up -d --build
```

La API queda publicada solo en `127.0.0.1:18001` y el frontend en
`127.0.0.1:13001`.

## Verificación

```bash
docker compose --env-file .env.docker ps
curl http://127.0.0.1:18001/healthz
curl -I http://127.0.0.1:13001/
```

El servicio `migrate` crea el esquema desde el baseline canónico y registra la
revisión `20260822_0002_evangelism_sede_indexes`. Sus volúmenes son nombrados
con el prefijo del proyecto y no reutilizan `uploads`, `storage`, `analytics`
ni las bases de producción.

El backend instala `requirements.docker.lock`; para actualizar dependencias se
regenera el lock en una revisión controlada y se vuelve a construir la imagen.

La prueba de recuperación ejecutada para este sandbox fue: `pg_dump` en formato
custom, validación con `pg_restore --list` y restauración completa en una base
temporal. El resultado fue 205 tablas restauradas.

## Estado de la migración

Este artefacto valida el sandbox y el rollback técnico. No configura Nginx ni
realiza cutover productivo. Antes de producción todavía deben cerrarse la
gestión de secretos, el backup/restauración probado, el versionado reproducible
de dependencias y la integración de almacenamiento SeaweedFS con
`StorageService` (el servicio se levanta en el sandbox, pero el backend sigue
usando `UPLOADS_DIR`).

Para retirar exclusivamente el sandbox:

```bash
docker compose --env-file .env.docker down -v
```
