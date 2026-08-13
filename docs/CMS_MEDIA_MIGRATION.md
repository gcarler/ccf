# Migración de imágenes públicas al CMS

Las imágenes editoriales que antes vivían en `frontend/public/images/convenccion/`
se conservan como fuentes de migración en:

```text
scripts/assets/public-site/images/convenccion/
```

Ese directorio **no se sirve como contenido público**. El runtime debe usar los
`CmsMediaItem` correspondientes, servidos por `/api/static/cms/public-site/...`.

## Ejecución por entorno

La migración es idempotente y funciona en modo lectura por defecto:

```bash
python scripts/migrate_public_images_to_cms.py --dry-run
```

En cada entorno (staging primero y después producción), con la base de datos,
el almacenamiento persistente y el usuario CMS del propio entorno:

```bash
python scripts/migrate_public_images_to_cms.py --apply
```

El comando:

1. registra o reconcilia los archivos como `CmsMediaItem`;
2. reemplaza referencias vivas en secciones CMS, posts, SEO, tema y perfiles
   pastorales;
3. crea una nueva versión únicamente para páginas publicadas afectadas;
4. conserva intactos los snapshots históricos;
5. deja los archivos fuente archivados para poder repetir la operación.

No usar `--remove-source` en despliegues normales: el archivo de fuentes es el
respaldo versionado de la migración. Si una operación excepcional requiere
retirarlo, primero debe verificarse que los blobs de almacenamiento son
persistentes, que cada URL CMS responde `200` y que no quedan referencias vivas.

## Verificación posterior

```bash
python scripts/audit_public_media_cms.py
```

Además, comprobar las rutas públicas y los endpoints CMS públicos con los
checks de contrato existentes. El auditor solo considera estáticos legítimos
el favicon, iconos PWA, `noise.svg` y `og-default.png`; cualquier imagen
editorial bajo `frontend/public/` debe hacer fallar el gate.

## Alcance

Este proceso centraliza los assets editoriales locales y las imágenes de posts,
perfiles pastorales, cursos y secciones CMS. Los feeds JSON de eventos/cursos
exponen sus rutas de imagen al selector de biblioteca del builder. Las
miniaturas de YouTube siguen siendo URLs oficiales generadas por YouTube y no
son assets institucionales gestionados por este CMS.
