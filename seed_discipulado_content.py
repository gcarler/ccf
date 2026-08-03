import sys
sys.path.insert(0, '/root/ccf')
from backend.core.database import SessionLocal
from backend.models_academy_core import Course, Lesson
import backend.models

CONTENT_MAP = {
    "La Salvación por Gracia": """# La Salvación por Gracia

## Introducción
La salvación es el regalo más grande que Dios ha ofrecido a la humanidad. No es algo que podamos ganar con nuestras propias fuerzas, sino que se recibe únicamente por la gracia de Dios mediante la fe.

## El Problema: El Pecado
> "Por cuanto todos pecaron, y están destituidos de la gloria de Dios." — **Romanos 3:23 (RVR1960)**

Desde la caída del hombre, todos nacemos con una naturaleza pecaminosa que nos separa de Dios. Ninguna buena obra puede cruzar el abismo que el pecado creó.

## La Solución: Jesucristo
> "Porque por gracia sois salvos por medio de la fe; y esto no de vosotros, pues es don de Dios; no por obras, para que nadie se gloríe." — **Efesios 2:8-9 (RVR1960)**

Jesucristo pagó el precio de nuestros pecados en la cruz. La gracia es recibir un favor inmerecido. Para ser salvos, debemos:
1. **Arrepentirnos:** Reconocer nuestro pecado y apartarnos de él.
2. **Creer:** Confiar en que Jesús murió y resucitó por nosotros.
3. **Confesar:** Declarar a Jesús como nuestro Señor y Salvador (Romanos 10:9-10).

## Preguntas de Reflexión
- ¿Has experimentado un arrepentimiento genuino en tu vida?
- ¿Por qué es un error pensar que podemos ir al cielo por "ser buenas personas"?
""",
    "La Autoridad de la Biblia": """# La Autoridad de la Biblia

## Introducción
La Biblia no es un libro común; es la revelación escrita de Dios para la humanidad. Es nuestra única regla infalible de fe y conducta.

## Inspiración Divina
> "Toda la Escritura es inspirada por Dios, y útil para enseñar, para redargüir, para corregir, para instruir en justicia, a fin de que el hombre de Dios sea perfecto, enteramente preparado para toda buena obra." — **2 Timoteo 3:16-17 (RVR1960)**

Creemos que los escritores bíblicos fueron guiados por el Espíritu Santo. Por lo tanto, la Biblia es inerrante y tiene autoridad final sobre nuestras vidas, opiniones y tradiciones.

## Poder Transformador
> "La palabra de Dios tiene vida y poder. Es más cortante que cualquier espada de dos filos..." — **Hebreos 4:12 (TLA)**

## Cómo acercarnos a la Palabra
- **Leerla diariamente:** Es nuestro alimento espiritual (Mateo 4:4).
- **Meditar en ella:** Salmos 1 nos llama a reflexionar de día y de noche en Su ley.
- **Obedecerla:** No seamos solo oidores, sino hacedores (Santiago 1:22).

## Preguntas de Reflexión
- ¿Qué lugar ocupa la lectura de la Biblia en tu rutina diaria?
- ¿Estás dispuesto a cambiar una opinión personal si la Biblia dice lo contrario?
""",
    "La Naturaleza de Dios": """# La Naturaleza de Dios

## Introducción
Para tener una relación profunda con Dios, debemos conocer quién es Él. Creemos en un solo Dios verdadero que se ha revelado en tres personas distintas: el Padre, el Hijo y el Espíritu Santo.

## Un Solo Dios
> "Oye, Israel: Jehová nuestro Dios, Jehová uno es." — **Deuteronomio 6:4 (RVR1960)**

## La Trinidad
Aunque la palabra "Trinidad" no aparece en la Biblia, el concepto es evidente desde el Génesis. Vemos a la Trinidad obrando en la salvación y en el bautismo de Jesús.
> "Por tanto, id, y haced discípulos a todas las naciones, bautizándolos en el nombre del Padre, y del Hijo, y del Espíritu Santo." — **Mateo 28:19 (RVR1960)**

## Sus Atributos
- **Amor:** Dios es amor (1 Juan 4:8). Su amor es incondicional y sacrificial.
- **Santidad:** Él es apartado del pecado y perfectamente puro.
- **Justicia y Misericordia:** Él juzga el pecado, pero ofrece perdón a través de la cruz.

## Preguntas de Reflexión
- ¿Cómo te ayuda entender que Dios es Padre, Hijo y Espíritu Santo?
- De los atributos de Dios (amor, santidad, justicia), ¿cuál te impacta más en este momento de tu vida?
""",
    "La Persona de Jesucristo": """# La Persona de Jesucristo

## Introducción
Jesucristo es la figura central de la historia y de nuestra fe. Él es Dios encarnado, el puente perfecto entre un Dios santo y una humanidad pecadora.

## Totalmente Dios y Totalmente Hombre
> "En el principio era el Verbo, y el Verbo era con Dios, y el Verbo era Dios... Y aquel Verbo fue hecho carne, y habitó entre nosotros." — **Juan 1:1, 14 (RVR1960)**

Jesús tuvo que ser humano para poder morir en nuestro lugar, y tuvo que ser Dios para que Su sacrificio tuviera un valor infinito y pudiera vencer a la muerte.

## Su Obra Redentora
- **Nacimiento Virginal:** Concebido por el Espíritu Santo, nació sin la naturaleza pecaminosa de Adán.
- **Vida sin Pecado:** Vivió en perfecta obediencia a la ley de Dios.
- **Muerte Vicaria:** Murió en la cruz recibiendo el castigo que nosotros merecíamos.
- **Resurrección y Exaltación:** Resucitó al tercer día, venció la muerte, ascendió al cielo y hoy intercede por nosotros (Filipenses 2:5-11).

## Preguntas de Reflexión
- ¿Quién es Jesús para ti personalmente?
- ¿Por qué era absolutamente necesario que Jesús resucitara de entre los muertos?
""",
    "El Bautismo en Agua": """# El Bautismo en Agua

## Introducción
El bautismo en agua es una ordenanza directa de Jesucristo. No es un medio para alcanzar la salvación, sino una demostración pública de una salvación que ya ha ocurrido en el corazón.

## El Significado
La palabra *bautizar* (del griego *baptizo*) significa sumergir. Al ser sumergidos en el agua, declaramos que nos identificamos con Cristo.
> "¿O no sabéis que todos los que hemos sido bautizados en Cristo Jesús, hemos sido bautizados en su muerte? Porque somos sepultados juntamente con él para muerte por el bautismo, a fin de que como Cristo resucitó de los muertos por la gloria del Padre, así también nosotros andemos en vida nueva." — **Romanos 6:3-4 (RVR1960)**

- **Bajar al agua:** Representa morir a nuestra vieja vida y al pecado.
- **Salir del agua:** Representa resucitar a una vida nueva en Cristo.

## ¿Quién debe bautizarse?
Todo aquel que se ha arrepentido y ha creído en Jesús como su Señor y Salvador (Hechos 2:38). Es un acto de obediencia que debe seguir a la conversión.

## Preguntas de Reflexión
- Si ya has aceptado a Cristo, ¿estás dispuesto a dar este paso de obediencia pública?
- ¿Qué significado personal tiene para ti dejar la "vieja vida" atrás?
""",
    "El Bautismo en el Espíritu Santo": """# El Bautismo en el Espíritu Santo

## Introducción
Como iglesia pentecostal, creemos que el Bautismo en el Espíritu Santo es una experiencia subsecuente a la salvación. Es la promesa del Padre para empoderar a los creyentes para el testimonio y el servicio.

## La Promesa y el Propósito
> "Pero recibiréis poder, cuando haya venido sobre vosotros el Espíritu Santo, y me seréis testigos en Jerusalén, en toda Judea, en Samaria, y hasta lo último de la tierra." — **Hechos 1:8 (RVR1960)**

El propósito principal de esta llenura no es hacernos sentir superiores, sino darnos **poder (dunamis)** para vivir una vida santa y predicar el Evangelio con audacia.

## La Evidencia Inicial
En el libro de los Hechos, vemos un patrón claro cuando los creyentes eran bautizados en el Espíritu:
> "Y fueron todos llenos del Espíritu Santo, y comenzaron a hablar en otras lenguas, según el Espíritu les daba que hablasen." — **Hechos 2:4 (RVR1960)**

Creemos que el hablar en lenguas es la evidencia física inicial de esta llenura, tal como se experimentó en el Día de Pentecostés.

## ¿Cómo recibirlo?
1. Tener un corazón limpio y arrepentido.
2. Pedirlo con fe (Lucas 11:13).
3. Entregarse en adoración y recibirlo, dejando que el Espíritu tome control.

## Preguntas de Reflexión
- ¿Sientes que necesitas más poder espiritual para vencer la tentación y hablar de Cristo?
- ¿Estás buscando diariamente ser lleno del Espíritu Santo?
""",
    "Los Dones del Espíritu": """# Los Dones del Espíritu

## Introducción
El Espíritu Santo no solo nos empodera, sino que reparte herramientas sobrenaturales (dones) a la Iglesia para su edificación.

## Diversidad de Dones
> "Pero a cada uno le es dada la manifestación del Espíritu para provecho... Porque a éste es dada por el Espíritu palabra de sabiduría; a otro, palabra de ciencia... a otro, fe... a otro, dones de sanidades... a otro, el hacer milagros; a otro, profecía; a otro, discernimiento de espíritus; a otro, diversos géneros de lenguas; y a otro, interpretación de lenguas." — **1 Corintios 12:7-10 (RVR1960)**

Estos dones no son talentos naturales, son operaciones sobrenaturales.
- **Dones de Revelación:** Sabiduría, Ciencia, Discernimiento de espíritus.
- **Dones de Poder:** Fe, Sanidades, Milagros.
- **Dones de Inspiración:** Profecía, Géneros de lenguas, Interpretación de lenguas.

## El Propósito
Los dones no son para exaltar al individuo, sino para edificar a la iglesia y glorificar a Dios. Deben operar siempre bajo el fruto más excelente: el amor (1 Corintios 13).

## Preguntas de Reflexión
- ¿Crees que Dios puede usarte con dones sobrenaturales hoy en día?
- ¿Cómo puedes prepararte para que el Espíritu Santo te use en la edificación de tu iglesia local?
""",
    "La Oración y el Ayuno": """# La Oración y el Ayuno

## Introducción
La relación con Dios requiere comunicación y disciplina. La oración y el ayuno son las alas que elevan nuestra vida espiritual por encima de los afanes del mundo.

## La Oración
No es un rito religioso, es hablar con nuestro Padre celestial.
> "Mas tú, cuando ores, entra en tu aposento, y cerrada la puerta, ora a tu Padre que está en secreto; y tu Padre que ve en lo secreto te recompensará en público." — **Mateo 6:6 (RVR1960)**

Debemos orar sin cesar (1 Tesalonicenses 5:17), presentando nuestras peticiones con acción de gracias.

## El Ayuno
El ayuno bíblico es abstenerse voluntariamente de alimentos por un propósito espiritual.
> "Cuando ustedes ayunen, no se muestren tristes como los hipócritas... Dios, tu Padre, que ve en lo secreto, te dará tu recompensa." — **Mateo 6:16-18 (TLA)**

El ayuno no cambia a Dios, nos cambia a nosotros. Rompe fortalezas, humilla el alma y afina nuestro oído para escuchar la voz del Espíritu Santo.

## Preguntas de Reflexión
- ¿Cómo describirías tu vida de oración actualmente?
- ¿Qué área de tu vida crees que necesita ser entregada a Dios a través del ayuno y la oración?
""",
    "La Sanidad Divina": """# La Sanidad Divina

## Introducción
La enfermedad entró al mundo como consecuencia de la caída del hombre, pero la obra de Cristo en la cruz trajo redención no solo para nuestra alma, sino también para nuestro cuerpo físico.

## Provisión en la Expiación
Creemos que la sanidad divina es un privilegio de todos los creyentes, provisto en el sacrificio de Jesús.
> "Ciertamente llevó él nuestras enfermedades, y sufrió nuestros dolores... y por su llaga fuimos nosotros curados." — **Isaías 53:4-5 (RVR1960)**

## El Ministerio de Sanidad
Durante Su ministerio terrenal, Jesús sanó a todos los que acudían a Él, y delegó esta misma autoridad a Su Iglesia.
> "¿Está alguno enfermo entre vosotros? Llame a los ancianos de la iglesia, y oren por él, ungiéndole con aceite en el nombre del Señor. Y la oración de fe salvará al enfermo, y el Señor lo levantará..." — **Santiago 5:14-15 (RVR1960)**

Seguimos imponiendo las manos sobre los enfermos y orando con fe, confiando en la soberanía y la bondad de Dios.

## Preguntas de Reflexión
- ¿Crees verdaderamente que Dios sigue haciendo milagros de sanidad hoy?
- Si estás enfrentando una enfermedad, ¿has llevado tu petición a Dios y a los líderes de tu iglesia en fe?
""",
    "Mayordomía y Generosidad": """# Mayordomía y Generosidad

## Introducción
Todo lo que tenemos (vida, tiempo, talentos y dinero) le pertenece a Dios. Nosotros somos simplemente administradores (mayordomos) de Sus recursos.

## El Principio del Diezmo
El diezmo significa el 10% de nuestros ingresos. Es apartar la primicia para Dios como acto de adoración y reconocimiento de que Él es nuestro proveedor.
> "Traed todos los diezmos al alfolí y haya alimento en mi casa; y probadme ahora en esto, dice Jehová de los ejércitos, si no os abriré las ventanas de los cielos, y derramaré sobre vosotros bendición hasta que sobreabunde." — **Malaquías 3:10 (RVR1960)**

## Ofrendas y Generosidad
Mientras el diezmo es una obediencia establecida, la ofrenda es un acto de gratitud voluntaria.
> "Cada uno debe dar lo que haya decidido en su corazón, y no de mala gana ni a la fuerza, porque Dios ama al que da con alegría." — **2 Corintios 9:7 (TLA)**

En la iglesia local, los recursos se utilizan para expandir el Reino de Dios, sostener el ministerio y ayudar a los necesitados.

## Preguntas de Reflexión
- ¿Ves tu dinero como algo tuyo o como algo que Dios te ha confiado?
- ¿Qué te detiene a veces para ser completamente generoso con Dios?
""",
    "La Familia y la Iglesia Local": """# La Familia y la Iglesia Local

## Introducción
Nadie fue diseñado para vivir la vida cristiana en aislamiento. Al aceptar a Cristo, somos adoptados en una familia espiritual: la Iglesia.

## El Cuerpo de Cristo
La iglesia no es un edificio, son las personas. Cada creyente es un miembro del Cuerpo de Cristo con una función vital.
> "Y considerémonos unos a otros para estimularnos al amor y a las buenas obras; no dejando de congregarnos, como algunos tienen por costumbre, sino exhortándonos..." — **Hebreos 10:24-25 (RVR1960)**

## Nuestro Compromiso
Estar comprometido con CCF (tu iglesia local) implica:
1. **Asistencia y Fidelidad:** Congregarme regularmente.
2. **Comunión (Koinonía):** Desarrollar relaciones auténticas.
3. **Servicio:** Usar mis dones para bendecir a otros (Efesios 4:11-12).
4. **Sujeción:** Estar bajo cobertura pastoral y liderazgo espiritual.

## Preguntas de Reflexión
- ¿Te consideras un asistente pasivo o un miembro activo de la familia de la iglesia?
- ¿En qué área o ministerio sientes que Dios te está llamando a servir dentro de la congregación?
""",
    "La Segunda Venida de Cristo": """# La Segunda Venida de Cristo

## Introducción
La promesa más grande que aguarda la Iglesia es el retorno de nuestro Señor Jesucristo. Esta verdad es la "esperanza bienaventurada" que nos consuela y nos motiva a vivir en santidad.

## El Arrebatamiento (Rapto) de la Iglesia
Creemos que Jesús volverá en las nubes para llevarse a Su Iglesia antes de los juicios de la Gran Tribulación.
> "Porque el Señor mismo con voz de mando, con voz de arcángel, y con trompeta de Dios, descenderá del cielo; y los muertos en Cristo resucitarán primero. Luego nosotros los que vivimos, los que hayamos quedado, seremos arrebatados juntamente con ellos en las nubes para recibir al Señor en el aire, y así estaremos siempre con el Señor." — **1 Tesalonicenses 4:16-17 (RVR1960)**

## Un Llamado a Vivir Preparados
Nadie sabe el día ni la hora. Por lo tanto, nuestra misión es vivir en santidad y predicar el Evangelio urgentemente a toda criatura.
> "El que da testimonio de estas cosas dice: Ciertamente vengo en breve. Amén; sí, ven, Señor Jesús." — **Apocalipsis 22:20 (RVR1960)**

## Preguntas de Reflexión
- Si Jesús regresara hoy, ¿estarías listo para irte con Él?
- ¿De qué manera la inminencia de Su venida cambia tus prioridades diarias?
"""
}

def update_lessons():
    with SessionLocal() as db:
        course = db.query(Course).filter(Course.slug == "discipulado-basico-ccf").first()
        if not course:
            print("Course not found!")
            return
            
        lessons = db.query(Lesson).filter(Lesson.course_id == course.id).order_by(Lesson.order_index).all()
        for lesson in lessons:
            title = lesson.title
            if title in CONTENT_MAP:
                lesson.content = CONTENT_MAP[title]
                # Modificamos el tipo de contenido a text ya que lo vamos a publicar como lectura en la página pública
                lesson.content_type = "texto"
                db.add(lesson)
                print(f"Updated content for lesson: {title}")
            else:
                print(f"Warning: No content mapping found for {title}")
                
        db.commit()
        print("All lessons updated successfully.")

if __name__ == "__main__":
    update_lessons()
