# 📖 Glosario Rápido de Frontend CCF

**Para usar cuando un agente de IA toque el frontend.**

## Términos Correctos en UI

| Contexto | Término UI correcto | Evitar |
|---|---|---|
| Cualquier persona en el sistema | persona, integrante, participante | miembro, member |
| Grupo pequeño comunitario | Grupo Pequeño / Comunidad | Cell Group, Célula |
| Grupo de evangelismo | Grupo de Evangelismo / Casa de Gloria | Glory House |
| Líder de grupo | Líder | no hay tabla "líderes" |
| Cantidad de personas en grupo | total_personas, Integrantes | members_count, Miembros |
| Usuario de la plataforma | usuario (solo para login) | no confundir con persona |

## Convenciones de UI

- **Drawers laterales** para detalles (nunca modales)
- **Tokens semánticos** para colores (nunca colores fijos)
- **Carga por pestañas** en perfiles (nunca full-profile)
- **apiFetch** para llamadas API (nunca fetch directo)
- **Rutas** siempre bajo `/plataforma/{modulo}`
- **DS Components** del design system (DSButton, DSCard, etc.)

## Regla de oro

> Si el backend dice "personas", el frontend dice "personas". 
> Nunca inventes términos que no existen en el kernel.
