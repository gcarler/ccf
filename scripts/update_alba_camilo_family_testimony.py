#!/usr/bin/env python3
"""Publish the verified family testimony for Pastors Alba and Camilo.

The copy comes from the pastoral team and replaces the generic family
paragraph in both public profiles. The default mode is a dry run; pass
``--apply`` to persist the update and invalidate the public pastoral cache.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import models
from backend.core.cache_v2 import invalidate_cached_public_pattern
from backend.core.database import SessionLocal

FAMILY_TESTIMONY = (
    "<p><strong>Perfil Familiar — Alba y Camilo:</strong> Alba está casada con el Pastor Camilo Pájaro. "
    "Se conocieron en su etapa escolar y comenzaron a asistir juntos a los servicios de madrugón, "
    "que marcaron los inicios de su relación en la iglesia. En medio de su relación atravesaron "
    "altibajos y estuvieron separados durante un año; en ese período Alba se alejó de la Iglesia El Faro. "
    "Después retomaron su relación y Alba regresó a la iglesia. En 2014 contrajeron matrimonio. "
    "Durante sus doce años de matrimonio, el Señor los ha sustentado, han crecido ministerialmente "
    "y han procurado caminar bajo la dirección del Padre. Juntos, guiados y fortalecidos por Dios, "
    "han formado una familia con dos hijas, Sara Valentina y Shaddai Antonella. Su historia familiar "
    "es un testimonio de la fidelidad, el amor y la provisión de Dios.</p>"
)

FAMILY_SECTION_RE = re.compile(
    r"<p><strong>(?:Perfil Familiar|Familia y llamado):</strong>.*?</p>",
    flags=re.DOTALL,
)


def _find_persona(db, first_name: str, last_name: str):
    return (
        db.query(models.Persona)
        .filter(
            models.Persona.first_name.ilike(f"%{first_name}%"),
            models.Persona.last_name.ilike(f"%{last_name}%"),
            models.Persona.is_pastoral_leader.is_(True),
        )
        .first()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persist the verified testimony")
    args = parser.parse_args()

    with SessionLocal() as db:
        profiles = [
            _find_persona(db, "Alba", "Arias"),
            _find_persona(db, "Camilo", "Pájaro"),
        ]
        missing = [label for label, profile in zip(("Alba Arias", "Camilo Pájaro"), profiles) if profile is None]
        if missing:
            raise RuntimeError(f"No se encontraron perfiles pastorales: {', '.join(missing)}")

        for profile in profiles:
            current = profile.bio_full or ""
            if FAMILY_SECTION_RE.search(current):
                next_bio = FAMILY_SECTION_RE.sub(FAMILY_TESTIMONY, current, count=1)
            else:
                next_bio = f"{current}{FAMILY_TESTIMONY}"
            print(f"{profile.nombre_completo}: {len(current)} -> {len(next_bio)} caracteres")
            if args.apply:
                profile.bio_full = next_bio

        if args.apply:
            db.commit()
            invalidate_cached_public_pattern("public_pastoral_team")
            print("✓ Testimonio familiar publicado e invalidación de cache solicitada.")
        else:
            print("Dry run: usa --apply para persistir el testimonio verificado.")


if __name__ == "__main__":
    main()
