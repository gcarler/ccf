"""
Public Contact Tracking Service (Task 3.1)

Reusable service that encapsulates the pattern:
  "find-or-create Member, create ConsolidationCase/Pipeline lead, track source"

All public-facing endpoints should use this service instead of inline duplication.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models

logger = logging.getLogger(__name__)


@dataclass
class ContactRecord:
    """Input record for a public contact."""
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    source: str = "web"
    landing_page: Optional[str] = None
    campaign: Optional[str] = None
    notes: Optional[str] = None
    spiritual_status: str = "Nuevo"
    church_role: str = "Visitante"
    # Optional: extra notes to append (e.g. book title, course name)
    extra_notes: list[str] = field(default_factory=list)


@dataclass
class ContactResult:
    """Output record after tracking a contact."""
    member: Optional[models.Member] = None
    member_created: bool = False
    case: Optional[models.ConsolidationCase] = None
    case_created: bool = False


def _normalize(val: Optional[str]) -> Optional[str]:
    if val is None:
        return None
    v = val.strip()
    return v if v else None


class PublicContactTracker:
    """
    Tracks every public contact into the CRM pipeline consistently.

    Usage:
        tracker = PublicContactTracker()
        result = tracker.record_contact(db, ContactRecord(...))
    """

    def record_contact(self, db: Session, record: ContactRecord) -> ContactResult:
        result = ContactResult()

        email = _normalize(record.email)
        phone = _normalize(record.phone)

        # 1. Find existing Member by phone or email
        member = self._find_member(db, email, phone)

        # 2. Create Member if not found
        if not member:
            member = models.Member(
                first_name=record.first_name or "Visitante",
                last_name=record.last_name or "",
                email=email,
                phone=phone,
                spiritual_status=record.spiritual_status,
                church_role=record.church_role,
            )
            db.add(member)
            db.flush()
            result.member_created = True
            logger.info(
                f"New Member created via public contact: "
                f"{member.first_name} {member.last_name} ({email or phone})"
            )

        result.member = member

        # 3. Create ConsolidationCase
        notes_lines = list(record.extra_notes)
        if record.notes:
            notes_lines.append(record.notes)
        if record.landing_page:
            notes_lines.append(f"Landing: {record.landing_page}")
        if record.campaign:
            notes_lines.append(f"Campaign: {record.campaign}")

        case = models.ConsolidationCase(
            member_id=member.id,
            stage="new",
            status="active",
            source=record.source,
            notes="\n".join(notes_lines) if notes_lines else None,
        )
        db.add(case)
        db.flush()
        result.case = case
        result.case_created = True

        return result

    @staticmethod
    def _find_member(
        db: Session, email: Optional[str], phone: Optional[str]
    ) -> Optional[models.Member]:
        """Find an existing Member by email or phone."""
        conditions = []
        if phone:
            conditions.append(models.Member.phone == phone)
        if email:
            conditions.append(models.Member.email == email)

        if not conditions:
            return None

        return db.query(models.Member).filter(or_(*conditions)).first()


# Module-level convenience instance
tracker = PublicContactTracker()
