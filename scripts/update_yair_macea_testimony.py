#!/usr/bin/env python3
"""Publish the reviewed pastoral testimony for Yair Macea."""

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
    "Líder de jóvenes y maestro por naturaleza, comprometido con guiar a las nuevas generaciones "
    "a buscar a Jesús y servirle con pasión."
)

BIO_FULL = (
    "<p><strong>Un liderazgo que nació en casa:</strong> El Pastor Yair Macea es un líder que nació y creció en la "
    "Comunidad Cristiana El Faro. Desde niño ha estado vinculado a la vida de la iglesia y, con el paso de los años, "
    "se ha convertido en un referente para las generaciones que buscan conocer a Jesús y caminar con Él. Su historia no "
    "comenzó en una plataforma, sino en el aprendizaje cotidiano de la fe, el servicio y la vida en comunidad.</p>\n"
    "<p><strong>Maestro por naturaleza:</strong> Yair tiene una capacidad especial para acercarse a las personas, "
    "escucharlas y ayudarles a comprender la verdad de Dios de una manera clara y cercana. Su liderazgo nace de la "
    "relación y del ejemplo: enseña porque primero ha aprendido a caminar, a servir y a buscar al Señor con un corazón "
    "dispuesto. Por eso muchos jóvenes encuentran en él una voz de orientación y un acompañante confiable en sus procesos.</p>\n"
    "<p><strong>Una pasión que inspira:</strong> Como líder de jóvenes, anima a las nuevas generaciones a no vivir una fe "
    "superficial, sino a buscar a Jesús con sinceridad y a reconocerle como su Salvador. Su deseo es que cada joven "
    "descubra que puede tener una relación real con Dios, desarrollar sus dones y convertirse también en una influencia "
    "positiva para quienes le rodean.</p>\n"
    "<p><strong>Servicio en la adoración:</strong> El Pastor Yair sirve activamente en el grupo de Alabanza y en la "
    "agrupación Sonido de Gloria. Allí entiende la música y la adoración como espacios para exaltar a Dios, ministrar a "
    "la iglesia y ayudar a que otros vuelvan su corazón a Su presencia. Su servicio combina sensibilidad, disciplina y "
    "pasión por honrar al Señor con los dones que ha recibido.</p>\n"
    "<p><strong>Ministerio actual:</strong> Mientras lidera a los jóvenes del ministerio, Yair continúa formando, "
    "acompañando y movilizando a una generación que necesita referentes cercanos y una fe auténtica. Su liderazgo une la "
    "enseñanza, la adoración y el cuidado pastoral, creando espacios donde los jóvenes pueden crecer, servir y entender "
    "que sus vidas tienen propósito en Dios.</p>\n"
    "<p>El testimonio del Pastor Yair Macea es el de un hombre formado en la casa, afirmado en la fe y entregado a las "
    "generaciones que vienen. Desde la Comunidad Cristiana El Faro, continúa sirviendo con la convicción de que una vida "
    "apasionada por Jesús puede encender a muchas otras y abrirles el camino hacia una búsqueda genuina de Dios.</p>"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persistir el testimonio revisado")
    args = parser.parse_args()

    with SessionLocal() as db:
        profile = (
            db.query(models.Persona)
            .filter(
                models.Persona.first_name.ilike("%Yair%"),
                models.Persona.last_name.ilike("%Macea%"),
                models.Persona.is_pastoral_leader.is_(True),
            )
            .first()
        )
        if profile is None:
            raise RuntimeError("No se encontró el perfil pastoral de Yair Macea")

        print(f"{profile.nombre_completo}: {len(profile.bio_full or '')} -> {len(BIO_FULL)} caracteres")
        if args.apply:
            profile.bio_short = BIO_SHORT
            profile.bio_full = BIO_FULL
            db.commit()
            invalidate_cached_public_pattern("public_pastoral_team")
            print("✓ Testimonio de Yair Macea publicado e invalidación de cache solicitada.")
        else:
            print("Dry run: usa --apply para persistir el testimonio revisado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
