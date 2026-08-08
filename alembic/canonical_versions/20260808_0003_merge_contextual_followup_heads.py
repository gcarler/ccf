"""merge_contextual_followup_heads

Fusiona las dos cabezas divergentes de la cadena canonical:

- ``20260808_0002_event_campaign_defaults`` (rama del clasificador contextual +
  followup/identity, que crea ``event_communication_deliveries`` y
  ``event_identity_challenges``).
- ``20260804_0004_event_crm_followup`` (rama que enlaza registros de evento con
  CRM: ``personas.origen_evento_id``, ``crm_events.attendance_closed_*``,
  ``event_registrations.crm_case_id`` y ``crm_casos.origen_evento_id``).

Ambas ramas descienden de ``20260804_0003_event_registration_waitlist_unique``,
por lo que un ``alembic upgrade head`` sin esta merge dejaria una rama huerfana
(migraciones no aplicadas -> tablas/columnas ausentes -> backend cae al arranque,
p.ej. ``column personas.origen_evento_id does not exist``).

Esta revision no aplica cambios de esquema: solo cierra el branchpoint para que
exista un unico head.

Revision ID: 20260808_0003_merge_contextual_followup_heads
Revises: 20260804_0004_event_crm_followup, 20260808_0002_event_campaign_defaults
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "20260808_0003_merge_contextual_followup_heads"
down_revision: Union[str, Sequence[str], None] = (
    "20260804_0004_event_crm_followup",
    "20260808_0002_event_campaign_defaults",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
