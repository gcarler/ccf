#!/usr/bin/env python3
"""Add the verified family origin to Luis Ricardo Meza's testimony."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import models
from backend.core.cache_v2 import invalidate_cached_public_pattern
from backend.core.database import SessionLocal

FAMILY_PARAGRAPH = (
    "<p><strong>Sus raíces familiares:</strong> El Pastor Luis Ricardo Meza Gutiérrez es hijo de Luis Ricardo Meza "
    "Vázquez y de Neris Josefa Gutiérrez. Esta familia forma parte de sus raíces y de la historia que acompaña su "
    "identidad, su recorrido y su servicio al Señor.</p>\n"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persistir el dato familiar verificado")
    args = parser.parse_args()

    with SessionLocal() as db:
        profile = (
            db.query(models.Persona)
            .filter(
                models.Persona.first_name.ilike("%Luis Ricardo%"),
                models.Persona.last_name.ilike("%Meza%"),
                models.Persona.is_pastoral_leader.is_(True),
            )
            .first()
        )
        if profile is None:
            raise RuntimeError("No se encontró el perfil pastoral de Luis Ricardo Meza")

        current = profile.bio_full or ""
        if "Luis Ricardo Meza Vázquez" in current and "Neris Josefa Gutiérrez" in current:
            next_bio = current
        else:
            marker = "</p>"
            position = current.find(marker)
            if position < 0:
                next_bio = f"{FAMILY_PARAGRAPH}{current}"
            else:
                position += len(marker)
                next_bio = f"{current[:position]}\n{FAMILY_PARAGRAPH}{current[position:]}"

        print(f"{profile.nombre_completo}: {len(current)} -> {len(next_bio)} caracteres")
        if args.apply and next_bio != current:
            profile.bio_full = next_bio
            db.commit()
            invalidate_cached_public_pattern("public_pastoral_team")
            print("✓ Raíces familiares de Luis Ricardo publicadas e invalidación de cache solicitada.")
        elif args.apply:
            print("✓ Las raíces familiares ya estaban publicadas.")
        else:
            print("Dry run: usa --apply para persistir el dato familiar verificado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
