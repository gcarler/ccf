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
    "Pastora principal de la Comunidad Cristiana El Faro, comprometida con formar generaciones "
    "apasionadas por Cristo y servir a las comunidades con fe y esperanza."
)

BIO_FULL = (
    "<p><strong>Historia y familia:</strong> La Pastora Histar Ariza es hija de los pastores fundadores "
    "Alejandro Ariza Torres y Martina Herrera. Nació y creció en el seno de una familia cristiana, donde recibió "
    "de sus padres la enseñanza, la guía y la orientación necesarias para seguir al Señor y servirle con fidelidad.</p>\n"
    "<p><strong>Servicio a la comunidad:</strong> En su vida adulta fue elegida para ejercer cargos de elección "
    "popular, desde los cuales trabajó por las oportunidades, el desarrollo y el bienestar social de comunidades "
    "cercanas a la Comunidad Cristiana El Faro. Entre sus iniciativas se destacan proyectos de acueducto, "
    "alcantarillado y pavimentación, así como escuelas de música orientadas a inspirar a las nuevas generaciones, "
    "fortalecer sus talentos y acercarlas a la pasión por Cristo.</p>\n"
    "<p><strong>Llamado pastoral:</strong> Esta labor de servicio público la desarrolló de la mano con su llamado "
    "pastoral en la Comunidad Cristiana El Faro. Tras el fallecimiento del Pastor Alejandro Ariza Torres, en 2021, "
    "la Pastora Histar Ariza y su esposo, el Pastor Luis Ricardo Meza, asumieron como pastores principales del "
    "Ministerio Comunidad Cristiana El Faro.</p>\n"
    "<p><strong>Ministerio actual:</strong> Desde 2021, Histar se dedica plenamente a su tarea pastoral. Junto con "
    "su esposo ha trabajado para sacar adelante proyectos que fortalecen la fe y sirven a la comunidad, entre ellos "
    "<em>Jesús Transforma</em>. Su historia refleja la fidelidad de Dios a través de las generaciones, el valor de una "
    "familia que sirve al Señor y el compromiso de llevar esperanza, formación y transformación a la sociedad.</p>"
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
