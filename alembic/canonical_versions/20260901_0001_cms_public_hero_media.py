"""Move the published public hero media into the CMS source of truth.

The public home and about pages used these existing production media URLs as
frontend fallbacks.  They are copied into the already-published CMS hero
sections so the visible content is preserved while becoming editable.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260901_0001"
down_revision: Union[str, None] = "20260822_0002_evangelism_sede_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


HOME_SLIDES = [
    {"src": "/api/static/cms/public-site/645a6f5cfc2e41a290ace6da2bd16b55.webp", "alt": "Comunidad reunida en adoración"},
    {"src": "/api/static/cms/public-site/e96c6969f75347878c48ec968518c4a7.webp", "alt": "Comunidad reunida en oración"},
    {"src": "/api/static/cms/public-site/f5b69d948d934412a9470f557faf4f7f.webp", "alt": "Comunidad celebrando junta"},
    {"src": "/api/static/cms/public-site/5fff1d0f797e40c09b42873b6973bf7e.webp", "alt": "Mensaje en comunidad"},
]

ABOUT_SLIDES = [
    {"src": "/api/static/cms/public-site/1930936676f84f6b97df83da209fd657.webp", "alt": "Comunidad Cristiana El Faro — Nosotros"},
    {"src": "/api/static/cms/public-site/a663278641a340028b26d6831b08f063.webp", "alt": "Comunidad Cristiana El Faro — Nosotros"},
    {"src": "/api/static/cms/public-site/7ca9cbaf381a48bc841a6f858abae2cb.webp", "alt": "Comunidad Cristiana El Faro — Nosotros"},
]


def upgrade() -> None:
    # Use a JSON literal through the driver rather than interpolating URLs in
    # SQL.  The helper below is intentionally kept data-only and idempotent.
    import json

    bind = op.get_bind()
    for slug, slides in (("home", HOME_SLIDES), ("about", ABOUT_SLIDES)):
        bind.execute(
            sa.text(
                """
                UPDATE cms_sections
                   SET props_json = CAST((CAST(props_json AS jsonb) || CAST(:payload AS jsonb)) AS json),
                       updated_at = CURRENT_TIMESTAMP
                 WHERE page_id = (
                           SELECT p.id
                             FROM cms_pages p
                             JOIN cms_sites s ON s.id = p.site_id
                            WHERE s.site_key = 'ccf' AND p.slug = :slug
                            ORDER BY p.updated_at DESC, p.id DESC
                            LIMIT 1
                       )
                   AND section_key = 'hero'
                   AND (props_json->'slides' IS NULL OR json_array_length(props_json->'slides') = 0)
                """
            ),
            {"slug": slug, "payload": json.dumps({"slides": slides})},
        )


def downgrade() -> None:
    import json

    bind = op.get_bind()
    for slug, slides in (("home", HOME_SLIDES), ("about", ABOUT_SLIDES)):
        bind.execute(
            sa.text(
                """
                UPDATE cms_sections
                   SET props_json = props_json - 'slides',
                       updated_at = CURRENT_TIMESTAMP
                 WHERE page_id = (
                           SELECT p.id
                             FROM cms_pages p
                             JOIN cms_sites s ON s.id = p.site_id
                            WHERE s.site_key = 'ccf' AND p.slug = :slug
                            ORDER BY p.updated_at DESC, p.id DESC
                            LIMIT 1
                       )
                   AND section_key = 'hero'
                   AND props_json->'slides' = CAST(:slides AS jsonb)
                """
            ),
            {"slug": slug, "slides": json.dumps(slides)},
        )
