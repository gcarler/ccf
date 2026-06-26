"""
Script para crear el perfil de la Pastora Martina Herrera
y actualizar la foto de Yanedith Wilches.

Uso: cd /root/ccf && /root/ccf/venv/bin/python scripts/setup_pastoral_profiles.py
"""

import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, '.')

from backend.core.database import SessionLocal
from backend import models


def utcnow():
    return datetime.now(timezone.utc)


YANEDITH_PHOTO = "/images/pastores/yanedith_wilches.webp"
MARTINA_PHOTO = "/images/pastores/martina_herrera.webp"


def main():
    db = SessionLocal()

    try:
        sede = db.query(models.Sede).first()
        if not sede:
            print("ERROR: No hay sedes en la base de datos")
            return

        # ── 1. Actualizar Yanedith Wilches ──
        yane = db.query(models.Persona).filter(
            models.Persona.first_name.ilike('%yanedith%'),
            models.Persona.last_name.ilike('%wilches%'),
        ).first()

        if yane:
            yane.is_pastoral_leader = True
            yane.church_role = 'Pastora de Intercesión'
            yane.photo_url = YANEDITH_PHOTO
            yane.bio_short = 'La fuerza inquebrantable de una mujer virtuosa, la intercesión y la compasión por los vulnerables.'
            yane.bio_full = (
                '<p>La Pastora Yanedith Wilches es el motor espiritual de la congregación a través de la oración y la intercesión. '
                'Su testimonio está tejido por múltiples experiencias de respuestas milagrosas a la oración, sanidades divinas '
                'y provisión en tiempos de escasez.</p>'
                '<blockquote>"Cuando la iglesia ora, el cielo responde. No hay fortaleza espiritual que resista el clamor de un pueblo unido."</blockquote>'
                '<p>Ella lidera los ejércitos de intercesores, las vigilias y el ministerio de mujeres. Su liderazgo compasivo, '
                'pero firme como el acero en el ámbito espiritual, ha inspirado a cientos de mujeres a levantarse como columnas '
                'en sus hogares y guerreras en el Reino.</p>'
                '<p>Yanedith combina una profunda dulzura pastoral con una autoridad espiritual que se hace evidente cada vez '
                'que dirige a la congregación a buscar el rostro de Dios en adoración y ruego.</p>'
            )
            print(f"✓ Yanedith Wilches actualizada (ID: {yane.id})")
        else:
            print("⚠ Yanedith Wilches no encontrada en la DB. ¿Ya existe con otro nombre?")
            # Buscar alternativas
            alt = db.query(models.Persona).filter(
                models.Persona.first_name.ilike('%yanedith%')
            ).all()
            if alt:
                print(f"  Alternativas encontradas: {[(a.id, a.first_name, a.last_name) for a in alt]}")

        # ── 2. Crear Martina Herrera ──
        martina = db.query(models.Persona).filter(
            models.Persona.first_name.ilike('%martina%'),
            models.Persona.last_name.ilike('%herrera%'),
        ).first()
        if not martina:
            martina = db.query(models.Persona).filter(
                models.Persona.first_name.ilike('%martina%'),
            ).first()

        if martina:
            martina.is_pastoral_leader = True
            martina.is_main_pastor = True
            martina.church_role = 'Pastora Fundadora'
            martina.photo_url = MARTINA_PHOTO
            martina.bio_short = (
                'Pastora fundadora del ministerio Comunidad Cristiana El Faro junto a su esposo, '
                'Alejandro Ariza Torres, quien ya partió y está con el Señor.'
            )
            martina.bio_full = (
                '<p>La Pastora Martina Herrera es la pastora fundadora del ministerio Comunidad Cristiana El Faro. '
                'Junto a su esposo, Alejandro Ariza Torres, quien ya partió y está con el Señor, sembró con fe, '
                'oración y perseverancia las bases espirituales de esta casa.</p>'
                '<blockquote>"La obra de Dios se edifica con fe, obediencia y amor por las almas."</blockquote>'
                '<p>Desde los primeros días del ministerio, la Pastora Martina ha sido un pilar de oración, '
                'fidelidad y cuidado pastoral. Su corazón maternal ha acompañado a generaciones de creyentes '
                'que encontraron en ella una pastora, una consejera y una madre espiritual.</p>'
                '<p>Su legado permanece vivo en la familia espiritual de Comunidad Cristiana El Faro: una iglesia '
                'levantada para amar a Dios, servir a las personas y continuar la obra que el Señor puso en sus manos.</p>'
            )
            print(f"✓ Martina Herrera actualizada (existente, ID: {martina.id})")
        else:
            nueva = models.Persona(
                id=uuid.uuid4(),
                sede_id=sede.id,
                first_name='Martina',
                last_name='Herrera',
                church_role='Pastora Fundadora',
                photo_url=MARTINA_PHOTO,
                estado_vital='ACTIVO',
                participation_type='Activo',
                is_pastoral_leader=True,
                is_main_pastor=True,
                bio_short=(
                    'Pastora fundadora del ministerio Comunidad Cristiana El Faro junto a su esposo, '
                    'Alejandro Ariza Torres, quien ya partió y está con el Señor.'
                ),
                bio_full=(
                    '<p>La Pastora Martina Herrera es la pastora fundadora del ministerio Comunidad Cristiana El Faro. '
                    'Junto a su esposo, Alejandro Ariza Torres, quien ya partió y está con el Señor, sembró con fe, '
                    'oración y perseverancia las bases espirituales de esta casa.</p>'
                    '<blockquote>"La obra de Dios se edifica con fe, obediencia y amor por las almas."</blockquote>'
                    '<p>Desde los primeros días del ministerio, la Pastora Martina ha sido un pilar de oración, '
                    'fidelidad y cuidado pastoral. Su corazón maternal ha acompañado a generaciones de creyentes '
                    'que encontraron en ella una pastora, una consejera y una madre espiritual.</p>'
                    '<p>Su legado permanece vivo en la familia espiritual de Comunidad Cristiana El Faro: una iglesia '
                    'levantada para amar a Dios, servir a las personas y continuar la obra que el Señor puso en sus manos.</p>'
                ),
            )
            db.add(nueva)
            db.flush()
            print(f"✓ Martina Herrera creada (ID: {nueva.id})")

        db.commit()
        print("\n✅ Perfiles pastorales actualizados exitosamente.")
        print("\nFotos configuradas:")
        print(f"  Yanedith: {YANEDITH_PHOTO}")
        print(f"  Martina:  {MARTINA_PHOTO}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
