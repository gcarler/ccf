#!/usr/bin/env python3
"""Populate the public pastoral profiles with reviewed editorial biographies."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import models  # noqa: E402
from backend.core.cache_v2 import invalidate_cached_public_pattern  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402


BIOS = {
    "Luis Ricardo Meza Gutiérrez": """
<p><strong>Historia y llamado:</strong> El Pastor Luis Ricardo Meza Gutiérrez sirve como pastor principal de la Comunidad Cristiana El Faro. Su ministerio se distingue por una pasión constante por la enseñanza de la Palabra y por el deseo de que cada persona encuentre una fe firme, práctica y transformadora.</p>
<p><strong>Testimonio:</strong> Su historia pastoral refleja un proceso de transformación profunda: la gracia de Dios lo llevó a entender que enseñar no consiste solamente en comunicar información, sino en acompañar vidas hacia una relación más madura con Cristo. Desde esa convicción sirve a la iglesia con perseverancia, claridad bíblica y sensibilidad pastoral.</p>
<p><strong>Servicio actual:</strong> Como pastor principal, participa en la formación espiritual de la comunidad, acompaña a líderes y familias, y contribuye a extender una visión de iglesia fundamentada en la sana doctrina, la vida en comunidad y el servicio. Su anhelo es que la Palabra produzca discípulos que vivan su fe con integridad y esperanza.</p>
""",
    "Histar Ariza Herrera": """
<p><strong>Historia y llamado:</strong> La Pastora Histar Ariza Herrera sirve como pastora principal y es reconocida por su corazón de paternidad espiritual, su visión de expansión y su compromiso con el cuidado cercano de la congregación.</p>
<p><strong>Testimonio:</strong> Su ministerio nace de la convicción de que una comunidad sana se construye cuando las personas son vistas, amadas y formadas. Por eso acompaña procesos con paciencia, anima a quienes atraviesan temporadas difíciles y ayuda a que nuevos creyentes encuentren un lugar seguro para crecer.</p>
<p><strong>Servicio actual:</strong> Su liderazgo integra visión, compasión y formación. Sirve impulsando el crecimiento de la iglesia, fortaleciendo familias y levantando nuevos servidores que puedan llevar el amor del Padre a sus hogares, ministerios y ciudades.</p>
""",
    "Martina Herrera": """
<p><strong>Historia y llamado:</strong> La Pastora Martina Herrera es reconocida como pastora fundadora de la Comunidad Cristiana El Faro, ministerio que levantó junto a su esposo, Alejandro Ariza Torres. Su historia está vinculada a los primeros pasos de una casa de fe que buscó servir a las familias y anunciar el evangelio con perseverancia.</p>
<p><strong>Testimonio:</strong> A lo largo de su caminar ha visto cómo Dios sostiene una obra cuando el servicio nace de la obediencia, la oración y el amor por las personas. Su testimonio habla de fidelidad en las temporadas de inicio, de fortaleza en los momentos de transición y de gratitud por cada generación alcanzada.</p>
<p><strong>Legado:</strong> Su servicio pastoral continúa inspirando a la comunidad a cuidar la familia, permanecer firmes en la fe y abrir camino para que otros también respondan al llamado de servir. Su vida representa una memoria viva de los fundamentos sobre los que se edificó esta casa.</p>
""",
    "Alba Arias": """
<p><strong>Historia y encuentro con Dios:</strong> Antes de llegar a la Comunidad Cristiana El Faro, la Pastora Alba Arias no había tenido acercamientos a una iglesia ni una relación personal con Dios. En esta casa experimentó por primera vez la presencia del Espíritu Santo; ese encuentro transformó su carácter y le dio una nueva identidad como hija amada.</p>
<blockquote>“Elijo Juan 3:16 porque nos muestra la esencia misma de lo que Él es y lo que quiere con cada uno de nosotros.”</blockquote>
<p><strong>Servicio ministerial:</strong> Su camino comenzó en tareas sencillas de limpieza y logística. Después sirvió en bienvenida y en el ministerio infantil, acompañando a niños en sala cuna y escuela dominical. Su pasión por enseñar también se conecta con su profesión y con la convicción de que la educación puede sembrar conocimiento y valores eternos.</p>
<p><strong>Familia y llamado:</strong> Comparte la vida y el ministerio con el Pastor Camilo Pájaro. Juntos han atravesado procesos de restauración, regresaron a la comunidad, se bautizaron y se casaron en 2014. Hoy sirven acompañados por sus hijas, como testimonio de la fidelidad y provisión de Dios.</p>
""",
    "Camilo Pájaro": """
<p><strong>Historia y encuentro con Dios:</strong> Antes de conocer al Señor, el Pastor Camilo Pájaro estaba enfocado en el baile, la música secular y el béisbol. Dios reorientó sus prioridades y lo llevó a reconocer un propósito eterno. En ese proceso experimentó libertad frente a inseguridades y maldiciones generacionales.</p>
<blockquote>“He entendido que si es Él quien me guía y me dirige, en mi vida todo terminará ayudando para bien.”</blockquote>
<p><strong>Servicio ministerial:</strong> Su servicio comenzó en labores sencillas de limpieza y apoyo al templo. Con el tiempo creció como maestro de la Academia de Formación Ministerial, ministro de alabanza y integrante de Sonido de Gloria. Su pasión es habitar en la presencia de Dios y acompañar a quienes necesitan recuperar dirección y esperanza.</p>
<p><strong>Familia y llamado:</strong> Está casado con la Pastora Alba Arias, con quien comparte vida, familia y ministerio. Juntos sirven desde una historia de restauración y perseverancia, acompañados por sus hijas y por el deseo de ayudar a otras familias a caminar hacia la sanidad y la fe.</p>
""",
    "Alex y Elvia": """
<p><strong>Historia y llamado:</strong> Los Pastores Alex y Elvia sirven como pastores de familias. Su ministerio nace de una experiencia de gracia que los llevó a comprender que Dios también restaura vínculos, sana conversaciones y vuelve a unir lo que parecía perdido.</p>
<p><strong>Testimonio:</strong> Su historia ministerial está marcada por la perseverancia y por la convicción de que el matrimonio y la familia pueden convertirse en espacios de discipulado. Desde su experiencia acompañan a parejas y hogares que atraviesan crisis, buscando mostrar que la restauración requiere verdad, perdón, responsabilidad y dependencia de Dios.</p>
<p><strong>Servicio actual:</strong> Su labor pastoral se enfoca en escuchar, orientar y caminar junto a las familias. Sirven recordando que una casa fortalecida por el amor y la Palabra puede convertirse en una fuente de esperanza para otras generaciones.</p>
""",
    "Fernando y Mónica": """
<p><strong>Historia y llamado:</strong> Los Pastores Fernando y Mónica sirven en el ministerio de discipulado, acompañando a personas que desean avanzar de una fe inicial hacia una vida de compromiso, madurez y servicio.</p>
<p><strong>Testimonio:</strong> Su recorrido refleja una fidelidad construida en lo cotidiano: permanecer disponibles, servir sin buscar reconocimiento y caminar con otros aun cuando el proceso sea lento. Para ellos, discipular significa compartir la vida, enseñar con paciencia y ayudar a cada persona a reconocer su próximo paso con Dios.</p>
<p><strong>Servicio actual:</strong> Acompañan procesos de formación, consolidan nuevos creyentes y ayudan a conectar la enseñanza bíblica con decisiones reales. Su ministerio sostiene la convicción de que nadie debería caminar solo en su crecimiento espiritual.</p>
""",
    "Nehemías Morales": """
<p><strong>Historia y llamado:</strong> El Pastor Nehemías Morales sirve en el área de consolidación, una labor dedicada a recibir, afirmar y acompañar a quienes están comenzando o retomando su camino de fe.</p>
<p><strong>Testimonio:</strong> Su ministerio está marcado por la resiliencia y la fe inquebrantable. Desde esa perspectiva entiende que consolidar no es apresurar procesos, sino permanecer cerca, escuchar con respeto y ayudar a que cada persona encuentre estabilidad en Dios y en la comunidad.</p>
<p><strong>Servicio actual:</strong> Trabaja para que los nuevos miembros encuentren vínculos sanos, formación y oportunidades de servicio. Su pasión es construir comunidad con paciencia, generando espacios donde las personas puedan sanar, pertenecer y crecer.</p>
""",
    "Yair Macea": """
<p><strong>Historia y llamado:</strong> El Pastor Yair Macea sirve como pastor evangelístico, impulsado por el deseo de comunicar el evangelio con cercanía, claridad y compasión.</p>
<p><strong>Testimonio:</strong> Su historia pastoral habla de una gracia que vence la vergüenza y transforma la superación personal en una plataforma para servir. Por eso se acerca a quienes se sienten lejos, sin rumbo o sin una segunda oportunidad, recordándoles que Dios todavía puede escribir una historia nueva.</p>
<p><strong>Servicio actual:</strong> Su ministerio busca encender una pasión evangelística constante en la iglesia y movilizar a los creyentes hacia sus barrios, familias y círculos de influencia. Sirve con un fuego que no se limita a los escenarios, sino que se expresa en conversaciones y acciones concretas de amor.</p>
""",
    "Yanedith Wilches": """
<p><strong>Historia y llamado:</strong> La Pastora Yanedith Wilches sirve en el ministerio de intercesión, desde una sensibilidad especial por las necesidades de las personas y por quienes atraviesan situaciones de vulnerabilidad.</p>
<p><strong>Testimonio:</strong> Su vida ministerial refleja la fuerza de una mujer virtuosa que aprende a sostener a otros en oración, compasión y esperanza. Entiende la intercesión como una expresión de amor: escuchar el dolor, presentarlo delante de Dios y permanecer disponible para servir.</p>
<p><strong>Servicio actual:</strong> Acompaña jornadas de oración, fortalece la vida espiritual de la comunidad y anima a otros a desarrollar una fe perseverante. Su llamado une firmeza y ternura, recordando que la iglesia está llamada a cuidar especialmente a quienes necesitan protección y apoyo.</p>
""",
}


def main() -> None:
    with SessionLocal() as db:
        updated = []
        for name, bio in BIOS.items():
            pastor = db.query(models.Persona).filter(models.Persona.nombre_completo == name).first()
            if pastor is None:
                raise RuntimeError(f"Pastor no encontrado: {name}")
            pastor.bio_full = bio.strip()
            updated.append(name)
        db.commit()
        invalidate_cached_public_pattern("public_pastoral_team")
        print(f"Actualizados {len(updated)} perfiles: {', '.join(updated)}")


if __name__ == "__main__":
    main()
