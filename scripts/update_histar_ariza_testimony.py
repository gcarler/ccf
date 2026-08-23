#!/usr/bin/env python3
"""Publish the reviewed pastoral testimony for Histar Ariza."""

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
    "Hija de pastores fundadores, servidora de su comunidad y pastora principal, "
    "comprometida con formar generaciones apasionadas por Cristo."
)

BIO_FULL = (
    "<p><strong>Una fe recibida en casa:</strong> La historia de la Pastora Histar Ariza está profundamente ligada a "
    "la historia de la Comunidad Cristiana El Faro. Es hija de los pastores fundadores, Alejandro Ariza Torres y "
    "Martina Herrera, y nació en el seno de una familia cristiana. Desde sus primeros años recibió de sus padres "
    "mucho más que una enseñanza: recibió una forma de caminar con Dios, de servir a las personas y de permanecer "
    "firme en la fe. En su hogar aprendió que el ministerio también se construye con ejemplo, responsabilidad y amor "
    "por las nuevas generaciones.</p>\n"
    "<p><strong>Servir también es transformar:</strong> En su vida adulta, Histar fue elegida para ejercer cargos de "
    "elección popular. Desde esos espacios puso su liderazgo al servicio de las comunidades cercanas a la Comunidad "
    "Cristiana El Faro, trabajando por oportunidades, desarrollo y bienestar social. Su labor se expresó en proyectos "
    "de acueducto, alcantarillado y pavimentación, obras que respondían a necesidades concretas y que buscaban mejorar "
    "la vida cotidiana de las familias.</p>\n"
    "<p>También impulsó escuelas de música para inspirar a las nuevas generaciones, fortalecer sus talentos y abrirles "
    "caminos de formación. En esa tarea se hizo visible una convicción que ha acompañado toda su vida: cuando una "
    "generación encuentra oportunidades, dirección y esperanza, también puede descubrir un propósito mayor. Para Histar, "
    "formar a los jóvenes significa animarlos a desarrollar sus capacidades y modelar en ellos una vida apasionada por "
    "Cristo.</p>\n"
    "<p><strong>Un nuevo tiempo pastoral:</strong> Su servicio público siempre caminó de la mano con su ejercicio de "
    "pastoreo en la Comunidad Cristiana El Faro. En 2021, tras el fallecimiento del Pastor Alejandro Ariza Torres, "
    "Histar y su esposo, el Pastor Luis Ricardo Meza, asumieron como pastores principales del Ministerio Comunidad "
    "Cristiana El Faro. Este paso representó la continuidad de una historia familiar y espiritual, pero también el "
    "inicio de una nueva etapa de responsabilidad, cuidado y liderazgo para la iglesia.</p>\n"
    "<p><strong>Su llamado hoy:</strong> Desde entonces, Histar se dedica plenamente a la tarea pastoral. Junto con "
    "su esposo ha trabajado para sacar adelante proyectos que fortalecen la fe y sirven a la comunidad, entre ellos "
    "<em>Jesús Transforma</em>. Su ministerio une la sensibilidad de quien conoce las necesidades de su gente con la "
    "convicción de quien ha visto a Dios obrar a través de las generaciones.</p>\n"
    "<p>La vida de la Pastora Histar es un puente entre la herencia recibida y el futuro que ayuda a formar. En ella se "
    "encuentran la hija que aprendió a servir, la mujer que trabajó por el bienestar de su comunidad y la pastora que "
    "hoy acompaña a la iglesia con fe, cercanía y visión. Su testimonio habla de una familia que sembró, de una comunidad "
    "que sigue creciendo y de un Dios que permanece fiel mientras nuevas generaciones son llamadas a conocerle, amarle y "
    "servirle.</p>"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persistir el testimonio revisado")
    args = parser.parse_args()

    with SessionLocal() as db:
        profile = (
            db.query(models.Persona)
            .filter(
                models.Persona.first_name.ilike("%Histar%"),
                models.Persona.last_name.ilike("%Ariza%"),
                models.Persona.is_pastoral_leader.is_(True),
            )
            .first()
        )
        if profile is None:
            raise RuntimeError("No se encontró el perfil pastoral de Histar Ariza")

        print(f"{profile.nombre_completo}: {len(profile.bio_full or '')} -> {len(BIO_FULL)} caracteres")
        if args.apply:
            profile.bio_short = BIO_SHORT
            profile.bio_full = BIO_FULL
            db.commit()
            invalidate_cached_public_pattern("public_pastoral_team")
            print("✓ Testimonio de Histar Ariza publicado e invalidación de cache solicitada.")
        else:
            print("Dry run: usa --apply para persistir el testimonio revisado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
