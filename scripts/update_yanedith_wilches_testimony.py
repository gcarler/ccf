#!/usr/bin/env python3
"""Publish the reviewed pastoral testimony for Yanedith Wilches."""

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
    "Líder comunitaria y pastora comprometida con la defensa de las mujeres, "
    "el cuidado de las comunidades y el servicio a las poblaciones más vulnerables."
)

BIO_FULL = (
    "<p><strong>Una vida de servicio:</strong> La Pastora Yanedith Wilches ha sido, durante toda su vida, una líder "
    "natural y una miembro activa de la iglesia. Su historia se ha formado en medio del servicio, la fe y la cercanía "
    "con las personas. Es una mujer viuda que, a través de sus propias experiencias, ha desarrollado una sensibilidad "
    "especial para acompañar a quienes atraviesan momentos difíciles y necesitan encontrar fuerza y esperanza.</p>\n"
    "<p><strong>Defensa de las comunidades:</strong> Yanedith trabaja con determinación por las comunidades y por los "
    "derechos de las poblaciones más vulnerables, con un énfasis especial en las mujeres cabeza de familia. Su servicio "
    "nace de la convicción de que cada mujer merece ser escuchada, respetada y acompañada en la reivindicación de sus "
    "derechos y en la construcción de mejores oportunidades para ella y su familia.</p>\n"
    "<p>Por segundo período consecutivo, ejerce el rol de presidenta de la Junta de Acción Comunal de su comunidad. "
    "También hace parte de la Federación de Juntas de Acción Comunal, espacios desde los cuales participa en la búsqueda "
    "de soluciones, representa las necesidades de sus vecinos y promueve una participación comunitaria responsable y "
    "solidaria.</p>\n"
    "<p><strong>Acompañar y abrir caminos:</strong> Además de su liderazgo comunal, trabaja con la administración distrital "
    "en la Oficina de la Mujer, atendiendo casos específicos y acompañando a mujeres que luchan por la reivindicación de "
    "sus derechos. En cada encuentro procura ofrecer escucha, orientación y esperanza, ayudando a que quienes llegan en "
    "medio de la dificultad puedan reconocerse como personas valiosas, con dignidad y capacidad para avanzar.</p>\n"
    "<p><strong>Servicio en El Faro:</strong> En la Comunidad Cristiana El Faro Principal, Yanedith es responsable de "
    "diferentes equipos de trabajo. Allí pone al servicio de la iglesia su capacidad de liderazgo, su perseverancia y su "
    "corazón de pastora. No se limita a ocupar responsabilidades: acompaña personas, articula esfuerzos y anima a otros "
    "a servir con compromiso, sensibilidad y amor por la obra de Dios.</p>\n"
    "<p>Su vida conecta la acción comunitaria con el ministerio pastoral. En los barrios, en las juntas comunales, en la "
    "Oficina de la Mujer y en la iglesia, Yanedith ha sostenido una misma convicción: servir es ponerse del lado de quien "
    "necesita apoyo y trabajar para que la esperanza vuelva a abrirse camino. Por eso se ha convertido en un soporte y un "
    "baluarte para la obra de la iglesia en las comunidades y en los sectores más vulnerables.</p>\n"
    "<p>El testimonio de la Pastora Yanedith Wilches habla de una mujer que transforma el dolor en sensibilidad, el liderazgo "
    "en servicio y la fe en acciones concretas. Su legado se construye acompañando, defendiendo y levantando a otros, con "
    "la certeza de que Dios también usa una vida entregada para llevar dignidad, cuidado y esperanza a quienes más lo "
    "necesitan.</p>"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persistir el testimonio revisado")
    args = parser.parse_args()

    with SessionLocal() as db:
        profile = (
            db.query(models.Persona)
            .filter(
                models.Persona.first_name.ilike("%Yanedith%"),
                models.Persona.last_name.ilike("%Wilches%"),
                models.Persona.is_pastoral_leader.is_(True),
            )
            .first()
        )
        if profile is None:
            raise RuntimeError("No se encontró el perfil pastoral de Yanedith Wilches")

        print(f"{profile.nombre_completo}: {len(profile.bio_full or '')} -> {len(BIO_FULL)} caracteres")
        if args.apply:
            profile.bio_short = BIO_SHORT
            profile.bio_full = BIO_FULL
            db.commit()
            invalidate_cached_public_pattern("public_pastoral_team")
            print("✓ Testimonio de Yanedith Wilches publicado e invalidación de cache solicitada.")
        else:
            print("Dry run: usa --apply para persistir el testimonio revisado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
