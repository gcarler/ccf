#!/usr/bin/env python3
"""Publish the reviewed pastoral testimony for Alex y Elvia."""

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
    "Pastores comprometidos con enseñar la Palabra, servir a la iglesia "
    "y acompañar a las generaciones con amor y compasión."
)

BIO_FULL = (
    "<p><strong>Un llamado que nació en la juventud:</strong> Los Pastores Alex Cabarcas y Elvia de Angulo se "
    "vincularon desde jóvenes a la Comunidad Cristiana El Faro y formaron parte del ministerio de jóvenes. Allí "
    "comenzaron a crecer en la fe, a descubrir sus dones y a expresar un amor sincero por el Señor y por su iglesia. "
    "Con el tiempo, ese vínculo se convirtió en una historia de servicio compartido y en un llamado pastoral que han "
    "construido juntos.</p>\n"
    "<p><strong>Servir desde diferentes dones:</strong> Alex es un maestro de la Palabra. Le apasiona enseñar, abrir "
    "las Escrituras con claridad y ayudar a que las personas comprendan cómo la fe puede transformar sus decisiones y su "
    "manera de vivir. Es un hombre que ama el servicio y que procura poner sus capacidades al beneficio de la comunidad.</p>\n"
    "<p>Elvia también ha servido con fidelidad desde los diferentes roles que ha asumido en el ministerio. Su entrega, "
    "sensibilidad y disposición para acompañar a otros complementan el llamado que comparten. Juntos han aprendido que "
    "el pastorado no se sostiene únicamente con palabras, sino con presencia, cuidado, paciencia y una vida coherente "
    "con el evangelio que anuncian.</p>\n"
    "<p><strong>Un pastorado que conduce al amor y al servicio:</strong> En su labor pastoral han buscado conducir a los "
    "miembros de la Comunidad Cristiana El Faro hacia el amor y el servicio al Señor. Su ejemplo anima a otros a no ser "
    "solo espectadores de la vida de iglesia, sino personas dispuestas a involucrarse, servir con responsabilidad y poner "
    "sus dones al alcance de los demás.</p>\n"
    "<p><strong>Una familia que testifica:</strong> Alex y Elvia son padres de Ezequiel Cabarcas. Para ellos, su hijo es "
    "un testimonio vivo del amor y la fidelidad de Dios, una promesa encarnada que les recuerda que el Señor sigue obrando "
    "en su familia y en cada etapa de su historia. Su hogar también forma parte del mensaje que comparten: Dios puede "
    "sostener, guiar y cumplir sus propósitos con amor.</p>\n"
    "<p><strong>Un ministerio para cada generación:</strong> Los Pastores Alex y Elvia aman el ministerio y aman a la "
    "iglesia. Enseñan con denuedo, pero también con amor y compasión. Su servicio alcanza tanto a quienes están comenzando "
    "a conocer al Señor como a quienes llevan años caminando en la fe y necesitan ser afirmados para permanecer firmes.</p>\n"
    "<p>Su historia es un testimonio del poder de Dios: dos jóvenes que encontraron en la iglesia un lugar para crecer y "
    "que hoy sirven para que otros también encuentren dirección, comunidad y propósito. Desde su familia y su pastorado, "
    "continúan enseñando que amar a Dios también significa amar a las personas y estar dispuesto a servirlas.</p>"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persistir el testimonio revisado")
    args = parser.parse_args()

    with SessionLocal() as db:
        profile = (
            db.query(models.Persona)
            .filter(
                models.Persona.first_name.ilike("%Alex%"),
                models.Persona.last_name.ilike("%Elvia%"),
                models.Persona.is_pastoral_leader.is_(True),
            )
            .first()
        )
        if profile is None:
            raise RuntimeError("No se encontró el perfil pastoral de Alex y Elvia")

        print(f"{profile.nombre_completo}: {len(profile.bio_full or '')} -> {len(BIO_FULL)} caracteres")
        if args.apply:
            profile.bio_short = BIO_SHORT
            profile.bio_full = BIO_FULL
            db.commit()
            invalidate_cached_public_pattern("public_pastoral_team")
            print("✓ Testimonio de Alex y Elvia publicado e invalidación de cache solicitada.")
        else:
            print("Dry run: usa --apply para persistir el testimonio revisado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
