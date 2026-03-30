# Web + CMS Release Checklist

## Pre-deploy
- Confirmar rama y commit objetivo.
- Verificar que `backend/app.py` incluya routers `cms` y `content`.
- Confirmar que el backend actual no tenga proceso zombie en el puerto de despliegue.

## Deploy
- Levantar API:
  - `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000`
- Validar que el puerto este escuchando:
  - `python -c "import subprocess;print([l for l in subprocess.check_output(['netstat','-ano'], text=True, errors='ignore').splitlines() if ':8000' in l and 'LISTENING' in l])"`

## Post-deploy gates (obligatorio)
- Smoke publico:
  - `python scripts/web_cms_smoke.py --base-url http://127.0.0.1:8000`
- Smoke autenticado (editor/admin):
  - `python scripts/web_cms_smoke.py --base-url http://127.0.0.1:8000 --username admin_ccf --password admin123`
- Lint alcance Web+CMS:
  - `npm run lint -- --file "src/app/cms/page.tsx" --file "src/app/cms/content/page.tsx" --file "src/app/cms/media/page.tsx" --file "src/app/cms/events/page.tsx" --file "src/app/cms/testimonials/page.tsx" --file "src/components/public/FaroNavbar.tsx" --file "src/app/(public)/faro/page.tsx" --file "src/app/(public)/faro/eventos/page.tsx" --file "src/app/(public)/faro/testimonios/page.tsx"`

## QA funcional rapido
- Editar `faro_home_hero` en `/cms/content` y validar reflejo en `/faro`.
- Editar `faro_public_events` en `/cms/events` y validar `/faro/eventos`.
- Crear anuncio en `/admin/announcements/new` y validar `/community/announcements`.
- Moderar testimonio en `/admin/testimonials` y validar feed publico.

## Rollback
- Si smoke falla, no publicar cambios editoriales nuevos.
- Volver al commit anterior estable de backend/frontend.
- Reiniciar API y repetir smoke.

## Evidencias de cierre
- Guardar salida de smoke (publico + autenticado).
- Capturas de QA funcional rapido.
- Registrar resultado final en `docs/web_cms_super_quality_report.md`.
