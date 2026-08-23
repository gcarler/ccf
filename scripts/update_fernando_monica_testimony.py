#!/usr/bin/env python3
"""Publish the reviewed pastoral testimony for Fernando y Mónica."""

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
    "Pastores apasionados por la enseñanza, la formación de nuevas generaciones "
    "y el servicio fiel a Dios en la vida profesional y ministerial."
)

BIO_FULL = (
    "<p><strong>Una vocación que enseña:</strong> La historia de los Pastores Fernando y Mónica está marcada por "
    "una pasión compartida: enseñar. Su profesión es la docencia y, tanto en entidades públicas como en su ejercicio "
    "ministerial, han entendido la enseñanza como una oportunidad para acompañar vidas, formar carácter y abrir caminos "
    "de esperanza para las nuevas generaciones.</p>\n"
    "<p>Para ellos, educar no consiste únicamente en transmitir conocimientos. También significa ayudar a cada persona a "
    "reconocer su valor, tomar buenas decisiones y crecer con principios firmes. Por eso, en su labor siempre ha estado "
    "presente el deseo de inculcar valores cristianos y mostrar, con palabras y con el ejemplo, que la fe puede orientar "
    "la manera de vivir, relacionarse y servir a los demás.</p>\n"
    "<p><strong>Sus primeros pasos en la iglesia:</strong> En sus comienzos formaron parte de la congregación de la "
    "Comunidad Cristiana El Faro en María La Baja. Allí fueron construyendo una historia de servicio, aprendizaje y "
    "fidelidad, creciendo junto a la comunidad y disponiendo sus dones para acompañar a otras personas en su camino con "
    "Dios. Cada etapa fue preparando sus corazones y fortaleciendo una convicción que con el tiempo se hizo más clara: "
    "la enseñanza y el pastoreo pueden convertirse en una misma expresión de amor y servicio.</p>\n"
    "<p><strong>Un nuevo llamado:</strong> Con el paso del tiempo asumieron el rol de pastores en la Comunidad Cristiana "
    "El Faro Central. Allí han puesto su experiencia, su esfuerzo y su dedicación al servicio de la iglesia, inspirando "
    "a otros a trabajar y a servir al Señor con responsabilidad, excelencia y perseverancia.</p>\n"
    "<p><strong>Ministerio actual:</strong> Fernando y Mónica sirven desde una visión que une el aula y el altar: forman "
    "personas, acompañan procesos y ayudan a que la enseñanza cristiana se convierta en decisiones concretas. Su "
    "testimonio anima a vivir la fe con coherencia, tanto en el ejercicio profesional como en el ministerial, recordando "
    "que cada espacio puede ser una oportunidad para reflejar a Cristo.</p>\n"
    "<p>Su historia es la de dos maestros que han convertido la enseñanza en una forma de pastorear y el pastoreo en una "
    "forma de servir. Con paciencia, entrega y amor por las generaciones que vienen, continúan sembrando valores, formando "
    "vidas y ayudando a construir una comunidad más comprometida con Dios y con el bienestar de los demás.</p>"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persistir el testimonio revisado")
    args = parser.parse_args()

    with SessionLocal() as db:
        profile = (
            db.query(models.Persona)
            .filter(
                models.Persona.first_name.ilike("%Fernando%"),
                models.Persona.last_name.ilike("%Mónica%"),
                models.Persona.is_pastoral_leader.is_(True),
            )
            .first()
        )
        if profile is None:
            profile = (
                db.query(models.Persona)
                .filter(
                    models.Persona.first_name.ilike("%Fernando%"),
                    models.Persona.last_name.ilike("%Monica%"),
                    models.Persona.is_pastoral_leader.is_(True),
                )
                .first()
            )
        if profile is None:
            raise RuntimeError("No se encontró el perfil pastoral de Fernando y Mónica")

        print(f"{profile.nombre_completo}: {len(profile.bio_full or '')} -> {len(BIO_FULL)} caracteres")
        if args.apply:
            profile.bio_short = BIO_SHORT
            profile.bio_full = BIO_FULL
            db.commit()
            invalidate_cached_public_pattern("public_pastoral_team")
            print("✓ Testimonio de Fernando y Mónica publicado e invalidación de cache solicitada.")
        else:
            print("Dry run: usa --apply para persistir el testimonio revisado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
