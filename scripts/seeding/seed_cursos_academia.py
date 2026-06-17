"""
Seed de cursos académicos disruptivos — Academia FARO.

Cursos cristocéntricos con perspectiva crítica, diseñados para ser referencia.
Ejecutar desde la raíz del proyecto:
    python3 scripts/seeding/seed_cursos_academia.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.models  # noqa: F401 — carga todos los modelos para resolver relaciones
from backend.models_academy_core import Curso, Leccion

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ccf_admin:ccf_password_secret_123@localhost:5432/ccf_db")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

SEDE_ID = "91eedd12-a1b2-474b-8270-5ccdcd111f86"

CURSOS = [
    {
        "code": "FARO-EVG-01",
        "slug": "el-evangelio-que-no-conocias",
        "title": "El Evangelio que no Conocías",
        "tag": "Fundamentos Radicales",
        "modality": "Presencial & Online",
        "duration_hours": 10,
        "instructor_name": "Pastor Luis Ricardo Meza Gutiérrez",
        "image_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=600&fit=crop",
        "excerpt": "¿Qué pasa cuando el mensaje que llamamos 'buenas noticias' ha sido secuestrado por el moralismo religioso y la sentimentalidad barata? Este curso es un ejercicio de recuperación.",
        "description": (
            "Después de dos mil años, el Evangelio corre el riesgo de volverse una marca, "
            "un sistema de reglas o una terapia emocional. Este curso es una excavación arqueológica "
            "hasta el núcleo del mensaje original de Jesús y Pablo: el anuncio de que el mundo ha "
            "cambiado de régimen. Estudiaremos la gracia que no da permiso para el pecado pero "
            "tampoco construye jaulas morales. Revisaremos por qué el evangelio de 'haz lo correcto "
            "y te irá bien' no es el evangelio de la cruz. Al final, quedarás con menos certezas "
            "cómodas y una fe más anclada en la persona de Jesucristo que en cualquier sistema teológico."
        ),
        "cta_text": "Quiero Inscribirme",
        "syllabus": [
            "El evangelio que Pablo predicó vs. el que predicamos hoy",
            "Gracia irresistible: ¿liberación o licencia para pecar?",
            "El reino que Jesús anunció no era una religión",
            "La cruz sin el resucitado es solo una tragedia griega",
            "Justificación y santificación: ¿tensión o armonía?",
            "El evangelio como subversión del poder imperial",
            "¿Es posible tener el Espíritu sin tener al Evangelio?",
            "Revisión: ¿qué diferencia hace el evangelio real en la vida cotidiana?",
        ],
        "lecciones": [
            ("¿Qué es exactamente el 'euangelion'?", "video", 45,
             "Exploramos la palabra griega desde su contexto político-imperial antes de ser 'secuestrada' por la religión. ¿Qué proclamaban los heraldos del César cuando anunciaban 'buenas noticias'?"),
            ("El Evangelio de Marcos en 16 capítulos que te cambiarán", "video", 60,
             "Lectura acelerada y comentada del Evangelio más antiguo. Sin ornamentos. El Jesús que actúa, confronta y salva."),
            ("Romanos 1-8: El argumento más denso de la historia", "video", 90,
             "Pablo construye el caso más elaborado del Nuevo Testamento. No es un libro de reglas: es un tratado de liberación ontológica."),
            ("Gracia barata vs. gracia costosa (Bonhoeffer)", "texto", 50,
             "Dietrich Bonhoeffer desde una celda nazi nos enseña la diferencia entre la gracia que salva y la que adormece. Lectura comentada de 'El costo del discipulado'."),
            ("El problema del moralismo evangélico contemporáneo", "video", 55,
             "Análisis crítico de cómo la cultura evangélica latinoamericana ha transformado el evangelio en un código de conducta con bonus espirituales."),
            ("La teología de la gloria vs. la teología de la cruz (Lutero)", "video", 50,
             "El joven Lutero en Heidelberg, 1518. Dos teologías que siguen en guerra. ¿Buscamos un Dios de poder o al Dios que muere?"),
            ("Escándalo y locura: 1 Corintios 1-2 en su contexto", "texto", 45,
             "El evangelio como escándalo para judíos religiosos y locura para griegos racionales. ¿Por qué el mensaje de la cruz sigue siendo inaceptable para el pensamiento moderno?"),
            ("Síntesis: El evangelio como ecosistema, no como fórmula", "video", 60,
             "Integración final. El evangelio no es un conjunto de proposiciones sino un campo de fuerza que transforma toda área de la existencia humana."),
        ],
    },
    {
        "code": "FARO-JES-02",
        "slug": "jesus-el-subversivo",
        "title": "Jesús el Subversivo: Historia, Contexto y Escándalo",
        "tag": "Teología Crítica",
        "modality": "100% Online",
        "duration_hours": 8,
        "instructor_name": "Academia FARO — Teología Histórica",
        "image_url": "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=800&h=600&fit=crop",
        "excerpt": "El Jesús manso y gentil de las estampitas religiosas no sobreviviría un minuto en el Palestina del siglo I. Este curso estudia al Jesús real: el que perturbó al Imperio y fue ejecutado por razones políticas.",
        "description": (
            "La mayoría de los retratos de Jesús son proyecciones de las culturas que los producen: "
            "un Jesús blanco, pacifista light, terapeuta espiritual o guardián de valores conservadores. "
            "Ninguno de estos es el Jesús del primer siglo. Este curso aplica las herramientas de la "
            "historia crítica y la arqueología bíblica para recuperar al Jesús del contexto judío "
            "del Segundo Templo: un maestro apocalíptico, un reformador radical, un hombre que dijo "
            "y hizo cosas que amenazaban a todos los poderes —romanos, sacerdotales y zelotes— y que "
            "por eso fue ejecutado por traición al Imperio. Estudiar este Jesús no debilitará tu fe: "
            "la hará indestructible."
        ),
        "cta_text": "Quiero Conocerlo de Verdad",
        "syllabus": [
            "Palestina en el siglo I: Roma, Herodes y el Templo",
            "Las fuentes no-bíblicas sobre Jesús (Josefo, Tácito, Plinio)",
            "El movimiento de Juan el Bautista y el bautismo de Jesús",
            "Las Bienaventuranzas como manifiesto político-espiritual",
            "Jesús y los Zelotas: ¿por qué no se unió a la resistencia armada?",
            "La purificación del Templo: ¿gesto simbólico o provocación calculada?",
            "El juicio: ¿por qué querían matarlo tanto judíos como romanos?",
            "La resurrección y su impacto histórico-político en el movimiento primitivo",
        ],
        "lecciones": [
            ("El Mediterráneo del siglo I: el mundo donde nació Jesús", "video", 55,
             "Mapas, cronologías y contexto. ¿Cómo era vivir bajo ocupación romana? ¿Qué significaba el Templo? ¿Quiénes eran los fariseos, saduceos y zelotas?"),
            ("Las fuentes históricas: ¿qué sabemos con certeza?", "video", 60,
             "Josefo, Tácito, el Talmud y los evangelios. Criterios de autenticidad histórica. Separar historia de teología sin destruir ninguna."),
            ("El programa de Galilea: milagros, parábolas y escándalo", "video", 65,
             "¿Por qué Jesús sanaba en sábado? ¿Por qué comía con pecadores? Cada acto era una declaración teológica y política."),
            ("'El reino de Dios está cerca': ¿qué significa exactamente?", "texto", 50,
             "La frase más repetida por Jesús y más malentendida por la historia. Análisis de las expectativas apocalípticas judías del período."),
            ("Jesús y las mujeres: la revolución silenciosa", "video", 50,
             "En una cultura donde las mujeres no podían testificar en juicio, Jesús las hace testigos primarias de la resurrección. El feminismo más antiguo de la historia."),
            ("La entrada a Jerusalén: provocación calculada", "video", 45,
             "Un burro, no un caballo de guerra. Un rey de los pobres en la ciudad del poder. La entrada mesiánica como performance político-teológico."),
            ("El proceso y la crucifixión: ¿por qué lo mataron?", "video", 70,
             "Análisis del proceso legal desde el derecho romano y judío. La crucifixión como ejecución política, no ritual religioso. El 'INRI' que Roma puso en la cruz."),
            ("La resurrección: historia, teología y consecuencias", "video", 75,
             "¿Qué ocurrió el tercer día? Evidencia histórica, las teorías alternativas y por qué la resurrección sigue siendo el evento más disruptivo de la historia humana."),
        ],
    },
    {
        "code": "FARO-ESC-03",
        "slug": "escatologia-sin-miedo",
        "title": "Escatología sin Apocalipsis-Fobia",
        "tag": "Profecía & Esperanza",
        "modality": "100% Online",
        "duration_hours": 8,
        "instructor_name": "Academia FARO — Teología Bíblica",
        "image_url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&h=600&fit=crop",
        "excerpt": "Décadas de películas del Arrebatamiento, bestias numéricas y calculadoras de fechas del fin del mundo. Ya es hora de leer el Apocalipsis como lo que es: una carta de resistencia y esperanza, no un almanaque de catástrofes.",
        "description": (
            "El libro más leído del Nuevo Testamento (Apocalipsis) es también el más malinterpretado. "
            "Durante décadas, el dispensacionalismo moderno ha convertido la profecía bíblica en un "
            "sistema de terror: el arrebatamiento, la tribulación, el Anticristo con código de barras. "
            "Este curso desmonta esas construcciones históricamente recientes y regresa al texto "
            "original: una carta escrita en código a comunidades perseguidas del siglo I, llena de "
            "símbolos que sus destinatarios entendían perfectamente. La escatología bíblica no es "
            "una predicción del futuro: es una teología de la esperanza en medio de la oscuridad. "
            "Y eso lo cambia todo."
        ),
        "cta_text": "Quiero Leer el Apocalipsis de Nuevo",
        "syllabus": [
            "Historia del dispensacionalismo: Darby, Scofield y el 'Left Behind'",
            "El Apocalipsis como género literario: literatura apocalíptica judía",
            "Los siete mensajes a las siete iglesias: cartas reales a comunidades reales",
            "Los símbolos del Apocalipsis y su clave de lectura del Antiguo Testamento",
            "Preterismo, historicismo, idealismo y futurismo: cuatro lecturas comparadas",
            "El Milenio: ¿literal, simbólico o ya inaugurado?",
            "La Nueva Jerusalén: ¿ciudad literal o metáfora de la restauración cósmica?",
            "Escatología como ética: cómo cambia nuestra vida el creer en la esperanza",
        ],
        "lecciones": [
            ("¿De dónde viene el 'rapto'? Historia de una idea de 200 años", "video", 50,
             "John Nelson Darby, el reverendo Scofield y cómo una interpretación del siglo XIX se convirtió en 'lo que siempre enseñó la Biblia'. Historia crítica del dispensacionalismo."),
            ("Apocalipsis 101: contexto, autor, destinatarios y propósito", "video", 60,
             "Quién escribió el Apocalipsis, cuándo y para quién. Las siete iglesias del Asia Menor. La persecución romana como contexto de emergencia."),
            ("Leer símbolos, no noticias: la clave hermenéutica", "texto", 55,
             "La Bestia con número 666 no es un chip subcutáneo. Es el emperador Nerón en código hebreo (gematría). Aprende a leer los símbolos como los lectores del siglo I."),
            ("La cosmología del Apocalipsis: cielo, tierra y el trono", "video", 50,
             "La liturgia celestial del Apocalipsis y su función en la narrativa. Dios en el trono no como decorado sino como afirmación política: César no es señor."),
            ("El Milenio a través de la historia de la iglesia", "video", 65,
             "Amilenarismo, postmilenio y premilenio. ¿Qué creían Agustín, Calvino, los Reformadores? ¿Por qué no hay una sola respuesta correcta?"),
            ("'Casi se acaba el mundo': cómo las fechas erróneas revelan el problema", "video", 45,
             "Un recorrido cómico y doloroso por las fechas del fin del mundo que no ocurrieron: 1844, 1914, 1975, 1988, 2000, 2012. ¿Qué nos dice esto sobre el método?"),
            ("Escatología del Nuevo Testamento: más allá del Apocalipsis", "texto", 55,
             "Marcos 13, 1 Tesalonicenses 4-5, 2 Pedro 3. La escatología no es solo un libro: es un hilo que corre por todo el Nuevo Testamento con coherencia."),
            ("Esperanza que transforma el presente: escatología como ética", "video", 60,
             "Si el final ya fue decidido y es la redención de toda la creación, ¿cómo cambia eso mi relación con el medioambiente, la justicia social y la historia?"),
        ],
    },
    {
        "code": "FARO-TEO-04",
        "slug": "teodicea-dios-frente-al-sufrimiento",
        "title": "Teodicea: Dios Frente al Sufrimiento",
        "tag": "Apologética Profunda",
        "modality": "Híbrido",
        "duration_hours": 10,
        "instructor_name": "Academia FARO — Filosofía y Teología",
        "image_url": "https://images.unsplash.com/photo-1476611338391-6f395a0ebc7b?w=800&h=600&fit=crop",
        "excerpt": "Las respuestas fáciles al sufrimiento son una ofensa a quienes sufren. 'Dios tiene un propósito', 'Todo pasa por algo' — frases que suelen venir de los que no están sufriendo. Este curso afronta sin filtros el problema más difícil de la fe.",
        "description": (
            "Si Dios es bueno y todopoderoso, ¿por qué existe el sufrimiento? Esta pregunta ha "
            "destruido más fe que cualquier argumento del ateísmo. Y las respuestas rápidas de la "
            "cultura religiosa —'Dios tiene un propósito', 'todo obra para bien'— a menudo silencian "
            "el dolor en lugar de acompañarlo. Este curso es una travesía honesta por el problema "
            "del mal: desde la filosofía griega hasta la Shoah, desde el libro de Job hasta C.S. Lewis "
            "escribiendo tras la muerte de su esposa. No terminarás con todas las respuestas. "
            "Terminarás con un Dios más real, más cercano al dolor, y con mayor capacidad de "
            "acompañar a quienes sufren sin ofenderlos con platitudes."
        ),
        "cta_text": "Quiero Afrontar Esta Pregunta",
        "syllabus": [
            "El problema del mal: formulación lógica y evidencial",
            "Las respuestas que no funcionan: refutación de los clichés pastorales",
            "Job: cuando Dios mismo tiene que responder al sufrimiento",
            "El mal natural vs. el mal moral: ¿son el mismo problema?",
            "Las teodiceas clásicas: Leibniz, Ireneo, Plantinga",
            "El Holocausto y la muerte de Dios: Wiesel, Frankl, Rubenstein",
            "La teología de la Cruz como respuesta: Moltmann y el Dios sufriente",
            "Sufrimiento y resurrección: la esperanza que no elude el dolor",
        ],
        "lecciones": [
            ("El problema del mal: formulación filosófica clásica", "video", 60,
             "Epicuro, Hume y el problema lógico del mal. ¿Es contradictorio creer en un Dios bueno y omnipotente en un mundo con sufrimiento? Análisis riguroso de las premisas."),
            ("Las respuestas que no funcionan", "video", 55,
             "'Todo pasa por algo', 'Dios necesitaba otro ángel', 'Es una prueba'. Por qué estas respuestas son teológicamente erróneas y pastoralmente dañinas."),
            ("Job: el libro más honesto de la Biblia", "texto", 70,
             "Lectura exegética de Job. El personaje que acusa a Dios en su cara y es justificado por él. ¿Qué dice esto sobre la lamentación, la honestidad y la oración?"),
            ("El libre albedrío como respuesta: Plantinga y sus límites", "video", 60,
             "Alvin Plantinga y la defensa del libre albedrío. ¿Explica el mal moral? ¿Explica el mal natural? ¿Un terremoto eligió libremente matar a miles?"),
            ("Auschwitz: el punto donde la teodicea tradicional muere", "video", 65,
             "Elie Wiesel, Viktor Frankl y Richard Rubenstein después del Holocausto. Las tres respuestas teológicas judías al mal extremo y qué dice cada una."),
            ("Jürgen Moltmann: el Dios crucificado", "texto", 55,
             "El teólogo más importante del siglo XX sobre el sufrimiento. Si Dios murió en la cruz, ¿dónde está Dios en Auschwitz? Moltmann responde desde la Trinidad."),
            ("Dolor, lamentación y espiritualidad: los Salmos de queja", "video", 50,
             "El 40% del Salterio son Salmos de lamentación y queja. La tradición bíblica no pide resignación ante el dolor: pide honestidad radical con Dios."),
            ("La resurrección como respuesta final al sufrimiento", "video", 65,
             "No la resurrección como consuelo barato, sino como afirmación de que el sufrimiento no tiene la última palabra. Escatología y teodicea como respuesta integral."),
        ],
    },
    {
        "code": "FARO-POL-05",
        "slug": "politica-poder-y-el-reino",
        "title": "Política, Poder y el Reino de Dios",
        "tag": "Ética Pública",
        "modality": "Presencial",
        "duration_hours": 8,
        "instructor_name": "Academia FARO — Ética y Teología Pública",
        "image_url": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=800&h=600&fit=crop",
        "excerpt": "Decir 'no me meto en política' es la postura política más cómoda para quienes tienen privilegios. La Biblia nunca fue apolítica. Este curso explora la tensión entre el reino de Dios y los reinos del mundo sin esquivar ninguna pregunta incómoda.",
        "description": (
            "Desde Constantino en el siglo IV hasta los evangelistas aliados con regímenes "
            "autoritarios en el siglo XXI, la iglesia cristiana ha tenido una relación complicada "
            "y frecuentemente vergonzosa con el poder político. Este curso no ofrece un partido "
            "político cristiano ni una agenda electoral. Ofrece herramientas bíblicas y teológicas "
            "para pensar críticamente sobre el poder, la justicia, el estado y la participación "
            "ciudadana desde los valores del reino de Dios. Los profetas del Antiguo Testamento "
            "eran profundamente políticos. Jesús fue ejecutado por el estado. Pablo desafió al "
            "César. La fe cristiana nunca fue privada: siempre tuvo implicaciones públicas."
        ),
        "cta_text": "Quiero Pensar con Profundidad",
        "syllabus": [
            "¿Puede un cristiano ser apolítico? Crítica de la privatización de la fe",
            "El error de Constantino: cuando la iglesia se casó con el poder",
            "El Sermón del Monte como constitución política del Reino",
            "Los profetas del AT como voces de oposición política",
            "Teología política: Barth, Yoder y Ellul",
            "Democracia, derechos humanos y pensamiento cristiano",
            "Idolatría política: cuando el partido o la nación se vuelven dioses",
            "¿Puede haber una ética política cristiana en el siglo XXI?",
        ],
        "lecciones": [
            ("La ilusión de la apoliticidad cristiana", "video", 55,
             "Por qué 'la iglesia no debe meterse en política' es en sí misma una postura política. Historia de la despolitización evangelica en América Latina y sus consecuencias."),
            ("Constantino, 313 d.C.: el momento en que todo cambió", "video", 60,
             "Cuando el cristianismo pasó de ser perseguido a ser oficial del Imperio Romano. Las consecuencias teológicas y políticas que aún pagamos."),
            ("Los profetas como disidentes políticos", "texto", 55,
             "Amós, Miqueas, Isaías: hombres que denunciaban injusticia económica, corrupción judicial y falsa religiosidad. Lectura política del profetismo bíblico."),
            ("El Sermón del Monte: las Bienaventuranzas como política alternativa", "video", 65,
             "'Bienaventurados los pobres' en su contexto socio-político. No como resignación sino como declaración de una realidad alternativa que el reino inaugura."),
            ("Karl Barth y el No a Hitler: cuando la teología fue resistencia", "video", 50,
             "La Declaración de Barmen (1934). Por qué un teólogo suizo se convirtió en el defensor teológico de la resistencia alemana al nazismo."),
            ("John Howard Yoder: la política de Jesús", "texto", 60,
             "La obra más influyente de teología política anabaptista del siglo XX. ¿Es la no-violencia una estrategia política viable o solo un ideal utópico?"),
            ("Idolatría política: cuando adoramos banderas y partidos", "video", 50,
             "Análisis teológico del nacionalismo, el tribalismo político y la idolatría del Estado. ¿Cómo discernir cuando la lealtad política se convierte en apostasía?"),
            ("Hacia una ética política cristiana para el siglo XXI", "video", 65,
             "Síntesis integradora. Participación ciudadana, voto informado, desobediencia civil y profetismo público: herramientas para el cristiano del siglo XXI."),
        ],
    },
    {
        "code": "FARO-ECO-06",
        "slug": "ecologia-creacion-crisis-climatica",
        "title": "Ecología, Creación y la Crisis Climática",
        "tag": "Cosmovisión",
        "modality": "Híbrido",
        "duration_hours": 6,
        "instructor_name": "Academia FARO — Cosmovisión y Creación",
        "image_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&h=600&fit=crop",
        "excerpt": "La tierra gime (Romanos 8:22) y la mayoría de las iglesias evitan el tema. Este curso desafía el antropocentrismo cristiano que ha justificado el saqueo de la creación y propone una teología del cuidado para el siglo XXI.",
        "description": (
            "En 1967, el historiador Lynn White publicó un artículo que acusó al cristianismo de "
            "ser el principal responsable intelectual de la crisis ecológica, por su visión de que "
            "la naturaleza existe para servir al ser humano. Tenía razón en parte. También tenía "
            "razón en identificar que la solución debía venir de dentro del mismo pensamiento "
            "cristiano. Génesis 1-2 no dice que el humano es dueño de la tierra: dice que es "
            "'shamar' — guardián. Este curso explora la teología de la creación, el mandato de "
            "mayordomía, la relación entre escatología y ecología ('si el mundo se va a quemar, "
            "¿para qué cuidarlo?') y propone una espiritualidad integrada con el cuidado de la "
            "tierra que no requiere abandonar la fe sino profundizarla."
        ),
        "cta_text": "Quiero Cuidar la Creación",
        "syllabus": [
            "Génesis 1-2: el mandato de 'dominio' que no es explotación",
            "Lynn White y la tesis de la responsabilidad cristiana en la crisis ecológica",
            "Escatología y ecología: ¿para qué cuidar si el mundo se acaba?",
            "El grito de la tierra: Romanos 8 y la creación que gime",
            "Consumo, capitalismo y la teología del 'tener más'",
            "San Francisco de Asís, Albert Schweitzer y el respeto a la vida",
        ],
        "lecciones": [
            ("Génesis 1-2: ¿dominio o mayordomía?", "video", 55,
             "El análisis semántico del hebreo 'radah' (dominio) y 'shamar' (guardar). La diferencia entre un dueño y un guardián y cómo eso cambia todo."),
            ("Lynn White y el cargo de culpabilidad cristiana", "texto", 50,
             "El artículo de 1967 que sacudió la teología. Análisis crítico: ¿tuvo razón? ¿Qué partes son válidas y qué partes son simplificación?"),
            ("'La creación entera gime': exégesis de Romanos 8:18-23", "video", 55,
             "Pablo habla de una creación que fue sometida a la vanidad involuntariamente y espera liberación. ¿Qué dice esto sobre la relación de Dios con la naturaleza?"),
            ("Escatología verde: si el mundo no 'se va a quemar', ¿qué pasa?", "video", 60,
             "La doctrina de la renovación de la creación (no su destrucción) en Apocalipsis 21-22. Cómo la escatología correcta produce compromiso ecológico."),
            ("Consumo, capitalismo y el pecado de la codicia sistémica", "video", 55,
             "El sistema económico que requiere consumo infinito en un planeta finito. Análisis teológico desde la doctrina del pecado estructural y la justicia redistributiva."),
            ("Espiritualidad encarnada: vivir el cuidado de la creación", "texto", 50,
             "Prácticas concretas, decisiones comunitarias y posicionamiento profético. Cómo una iglesia puede ser agente de restauración ecológica en su territorio."),
        ],
    },
]


def seed():
    db = Session()
    try:
        for data in CURSOS:
            existing = db.query(Curso).filter(Curso.slug == data["slug"]).first()
            if existing:
                print(f"  ↻  Actualizando: {data['title']}")
                curso = existing
            else:
                print(f"  +  Creando: {data['title']}")
                curso = Curso()

            curso.code = data["code"]
            curso.slug = data["slug"]
            curso.title = data["title"]
            curso.tag = data["tag"]
            curso.modality = data["modality"]
            curso.duration_hours = data["duration_hours"]
            curso.instructor_name = data["instructor_name"]
            curso.image_url = data["image_url"]
            curso.excerpt = data["excerpt"]
            curso.description = data["description"]
            curso.cta_text = data["cta_text"]
            curso.syllabus = data["syllabus"]
            curso.is_published = True
            curso.is_self_paced = True
            curso.access_level = "open"
            curso.xp_per_lesson = 25
            curso.sede_id = SEDE_ID

            if not existing:
                db.add(curso)
            db.flush()

            # Lecciones — borrar las existentes y recrear
            db.query(Leccion).filter(Leccion.course_id == curso.id).delete()

            for idx, (titulo, tipo, duracion, contenido) in enumerate(data["lecciones"], start=1):
                leccion = Leccion(
                    course_id=curso.id,
                    title=titulo,
                    content=contenido,
                    content_type=tipo,
                    order_index=idx,
                    duration_minutes=duracion,
                    is_published=True,
                )
                db.add(leccion)

            print(f"     → {len(data['lecciones'])} lecciones creadas")

        db.commit()
        print("\n✅ Seed completado exitosamente.")
        total = db.query(Curso).filter(Curso.is_published == True).count()  # noqa: E712
        print(f"   Total cursos publicados: {total}")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Sembrando cursos de la Academia FARO...\n")
    seed()
