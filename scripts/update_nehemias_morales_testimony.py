#!/usr/bin/env python3
"""Publish the reviewed pastoral testimony for Nehemías Morales."""

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

BIO_SHORT = (
    "Apasionado por la adoración a Dios, impulsa a las nuevas generaciones "
    "a buscarle de manera genuina y a crecer en su presencia."
)

BIO_FULL = (
    "<p><strong>Historia y familia:</strong> El Pastor Nehemías Morales es el primer hijo de su primer matrimonio. "
    "Está casado con María José Cueto, ministra de alabanza de la Comunidad Cristiana El Faro. "
    "Juntos sirven al Señor y construyen un hogar que procura honrar a Dios, caminar en unidad y reflejar "
    "el valor de una fe vivida con sinceridad.</p>\n"
    "<p><strong>Pasión y llamado:</strong> Nehemías es un hombre apasionado por la adoración a Dios. "
    "Para él, adorar no se limita a una canción o a un momento de reunión: es una respuesta diaria de amor, "
    "obediencia y entrega a la presencia del Señor. Desde esa convicción, anima a cada persona a acercarse a Dios "
    "con un corazón genuino, dispuesto a escucharle y a rendirle toda la vida.</p>\n"
    "<p><strong>Ministerio:</strong> Su pasión impulsa especialmente a las nuevas generaciones a buscar a Dios de "
    "manera real y profunda. Con sensibilidad pastoral, procura acompañarlas para que descubran su identidad en "
    "Cristo, desarrollen una fe firme y entiendan que la presencia de Dios transforma el carácter, las decisiones "
    "y la manera de servir a los demás.</p>\n"
    "<p><strong>Servicio actual:</strong> En su labor pastoral de consolidación, Nehemías recibe, afirma y acompaña "
    "a quienes están comenzando o retomando su camino de fe. Su servicio combina escucha, cercanía y formación, "
    "ayudando a que cada persona encuentre un lugar sano en la comunidad, crezca en su relación con Dios y descubra "
    "cómo poner sus dones al servicio del Reino.</p>\n"
    "<p>Su testimonio recuerda que una búsqueda genuina de Dios no es una experiencia pasajera, sino un camino de "
    "transformación constante. Desde la adoración, la familia y el acompañamiento pastoral, Nehemías procura encender "
    "en otros el deseo de conocer al Señor y vivir delante de Su presencia con verdad, pasión y perseverancia.</p>"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persistir el testimonio revisado")
    args = parser.parse_args()

    with SessionLocal() as db:
        profile = (
            db.query(models.Persona)
            .filter(
                models.Persona.first_name.ilike("%Nehemías%"),
                models.Persona.last_name.ilike("%Morales%"),
                models.Persona.is_pastoral_leader.is_(True),
            )
            .first()
        )
        if profile is None:
            raise RuntimeError("No se encontró el perfil pastoral de Nehemías Morales")

        print(f"{profile.nombre_completo}: {len(profile.bio_full or '')} -> {len(BIO_FULL)} caracteres")
        if args.apply:
            profile.bio_short = BIO_SHORT
            profile.bio_full = BIO_FULL
            db.commit()
            invalidate_cached_public_pattern("public_pastoral_team")
            print("✓ Testimonio de Nehemías Morales publicado e invalidación de cache solicitada.")
        else:
            print("Dry run: usa --apply para persistir el testimonio revisado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
