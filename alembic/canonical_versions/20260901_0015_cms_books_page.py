"""Move the legacy public books catalog into the CMS."""

from __future__ import annotations

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260901_0015"
down_revision: Union[str, None] = "20260901_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BOOKS = [
    {"id": "1", "title": "El Discípulo Comprometido", "author": "Juan Carlos Ortiz", "category": "Discipulado", "rating": 4.9, "free": True, "cover": "from-[hsl(var(--info))] to-[hsl(var(--info))]", "desc": "Un clásico que revolucionará tu comprensión del verdadero discipulado."},
    {"id": "2", "title": "Liderazgo con Propósito", "author": "Rick Warren", "category": "Liderazgo", "rating": 4.8, "free": False, "cover": "from-[hsl(var(--success))] to-[hsl(var(--domain-teal))]", "desc": "Descubre cómo liderar con propósito eterno en cada área de tu vida."},
    {"id": "3", "title": "La Oración que Mueve a Dios", "author": "E.M. Bounds", "category": "Oración", "rating": 4.7, "free": True, "cover": "from-[hsl(var(--info))] to-[hsl(var(--info))]", "desc": "Las enseñanzas más profundas sobre el poder transformador de la oración."},
    {"id": "4", "title": "Gracia Divina para el Matrimonio", "author": "Tim Keller", "category": "Familia", "rating": 4.8, "free": False, "cover": "from-[hsl(var(--danger))] to-[hsl(var(--domain-pink))]", "desc": "Una perspectiva bíblica profunda sobre el matrimonio como reflejo del evangelio."},
    {"id": "5", "title": "Finanzas con Fe", "author": "Equipo CCF", "category": "Mayordomía", "rating": 4.6, "free": True, "cover": "from-[hsl(var(--warning))] to-orange-600", "desc": "Manual práctico para manejar las finanzas con principios del Reino de Dios."},
    {"id": "6", "title": "Sanidad Interior", "author": "Leanne Payne", "category": "Consejería", "rating": 4.7, "free": False, "cover": "from-[hsl(var(--surface-3))] to-[hsl(var(--bg-muted))]", "desc": "Un camino bíblico hacia la restauración emocional y espiritual profunda."},
]

FEED = {"eyebrow": "Biblioteca Digital", "title_lead": "Libros que", "title_accent": "Transforman Mentes", "description": "Colección cuidadosamente seleccionada de los mejores recursos para tu crecimiento espiritual e intelectual.", "search_placeholder": "Buscar libro o autor...", "all_label": "Todos", "free_only_label": "Solo Gratuitos", "free_label": "Gratis", "download_label": "Descargar", "more_label": "Ver más", "books": BOOKS}


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("""
        INSERT INTO cms_pages (id, site_id, slug, title, status, seo_json, locale, created_at, updated_at)
        SELECT gen_random_uuid(), s.id, 'books', 'Libros', 'published', '{}'::json, 'es', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM cms_sites s WHERE s.site_key='ccf'
          AND NOT EXISTS (SELECT 1 FROM cms_pages p WHERE p.site_id=s.id AND p.slug='books')
    """))
    bind.execute(sa.text("""
        INSERT INTO cms_sections (id,page_id,section_key,type,props_json,sort_order,is_visible,status,locale,created_at,updated_at)
        SELECT gen_random_uuid(),p.id,'feed','feed',CAST(:props AS json),0,TRUE,'active','es',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
        FROM cms_pages p JOIN cms_sites s ON s.id=p.site_id
        WHERE s.site_key='ccf' AND p.slug='books'
          AND NOT EXISTS (SELECT 1 FROM cms_sections x WHERE x.page_id=p.id AND x.section_key='feed')
    """), {"props": json.dumps(FEED, ensure_ascii=False)})
    bind.execute(sa.text("""
        INSERT INTO cms_page_versions (id,page_id,version_number,snapshot_json,notes,created_at)
        SELECT gen_random_uuid(),p.id,1,json_build_object('page',json_build_object('id',p.id,'slug',p.slug,'title',p.title,'status',p.status,'seo_json',COALESCE(p.seo_json,'{}'::json)), 'sections',COALESCE((SELECT json_agg(json_build_object('id',s.id,'section_key',s.section_key,'type',s.type,'props_json',s.props_json,'sort_order',s.sort_order,'is_visible',s.is_visible,'status',s.status) ORDER BY s.sort_order) FROM cms_sections s WHERE s.page_id=p.id),'[]'::json)), 'Initial migration from legacy books route', CURRENT_TIMESTAMP
        FROM cms_pages p JOIN cms_sites st ON st.id=p.site_id
        WHERE st.site_key='ccf' AND p.slug='books' AND p.published_version_id IS NULL
    """))
    bind.execute(sa.text("""
        UPDATE cms_pages p SET published_version_id=(SELECT v.id FROM cms_page_versions v WHERE v.page_id=p.id ORDER BY v.version_number DESC LIMIT 1), updated_at=CURRENT_TIMESTAMP
        FROM cms_sites st WHERE st.id=p.site_id AND st.site_key='ccf' AND p.slug='books' AND p.published_version_id IS NULL
    """))


def downgrade() -> None:
    op.execute("DELETE FROM cms_pages WHERE site_id=(SELECT id FROM cms_sites WHERE site_key='ccf') AND slug='books'")
