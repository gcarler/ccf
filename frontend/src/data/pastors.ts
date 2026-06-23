export interface Pastor {
    id: string;
    name: string;
    title: string;
    image: string;
    quote: string;
    verse: string;
    shortStory: string;
    fullStory: string;
    isMain?: boolean;
    instagram?: string;
    facebook?: string;
    twitter?: string;
}

export const PASTORS: Pastor[] = [
    {
        id: "luis-ricardo-meza",
        name: "Luis Ricardo Meza Gutiérrez",
        title: "Pastor Principal",
        image: "/images/pastores/luis_ricardo_meza.webp",
        isMain: true,
        quote: "La Palabra de Dios, correctamente dividida, es el alimento que da vida a la Iglesia.",
        verse: "Esdras 7:10 - 'Porque Esdras había preparado su corazón para inquirir la ley de Jehová y para cumplirla, y para enseñar en Israel sus estatutos y decretos.'",
        shortStory: "Un testimonio de transformación profunda y pasión inagotable por la enseñanza de la Palabra.",
        fullStory: `
            <p>El Pastor Luis Ricardo Meza Gutiérrez llegó a los pies de Cristo buscando respuestas a las inquietudes más profundas de su intelecto y su alma. Lo que encontró fue una verdad tan innegable y un amor tan avasallador que cambió el rumbo de sus estudios y de su vida por completo.</p>
            <blockquote>"Cuando la mente es iluminada por la revelación de la Escritura, el corazón inevitablemente se enciende en adoración."</blockquote>
            <p>Dotado de una aguda capacidad para la exégesis bíblica y la enseñanza apologética, Luis Ricardo es un defensor apasionado de la sana doctrina. Ha liderado el Instituto Bíblico y la Academia de la congregación, formando teológicamente a los nuevos obreros y asegurando que las raíces doctrinales de la congregación sean profundas y firmes.</p>
            <p>Su testimonio nos recuerda que Dios redime nuestro intelecto y lo usa como un instrumento poderoso para derribar argumentos y llevar todo pensamiento cautivo a la obediencia a Cristo.</p>
        `
    },
    {
        id: "histar-ariza",
        name: "Histar Ariza Herrera",
        title: "Pastor Principal",
        image: "/images/pastores/histar_ariza.webp",
        isMain: true,
        quote: "Nuestra mayor recompensa es ver corazones transformados por el amor del Padre.",
        verse: "Jeremías 3:15 - 'Y os daré pastores según mi corazón, que os apacienten con ciencia y con inteligencia.'",
        shortStory: "El llamado pastoral, la visión de expansión y el corazón de paternidad espiritual que guía a nuestra congregación.",
        fullStory: `
            <p>El Pastor Histar Ariza Herrera ha sido un pilar fundamental en la fundación y consolidación de la congregación. Su ministerio nació de un profundo encuentro personal con la paternidad de Dios, lo que marcó para siempre su forma de liderar, amar y guiar a la iglesia.</p>
            <blockquote>"El ministerio no se trata de construir edificios grandes, sino de edificar familias fuertes que reflejen el carácter de Cristo."</blockquote>
            <p>Con más de dos décadas de servicio ininterrumpido, su enseñanza se caracteriza por la profundidad teológica combinada con una aplicación práctica y compasiva. Su visión principal es ver a cada persona de la comunidad no solo como un asistente, sino como un hijo espiritual llamado a cumplir un propósito eterno.</p>
            <p>A lo largo de los años, el Pastor Histar ha liderado proyectos de expansión, siembra de nuevas misiones y ha formado a decenas de líderes que hoy sirven a lo largo de toda la congregación. Su testimonio es un recordatorio vivo de que cuando Dios llama, también respalda, provee y sostiene.</p>
        `
    },
    {
        id: "alex-y-elvia",
        name: "Alex y Elvia",
        title: "Pastores de Familias",
        image: "/images/pastores/alex_elvia.webp",
        quote: "Las familias fuertes son el cimiento de una iglesia inquebrantable.",
        verse: "Josué 24:15 - 'Pero yo y mi casa serviremos a Jehová.'",
        shortStory: "Un testimonio vivo de gracia enfocado en la restauración matrimonial y el ministerio familiar.",
        fullStory: `
            <p>Los pastores Alex y Elvia son un testimonio vivo del poder restaurador de Dios. Tras experimentar de primera mano cómo la gracia divina puede sanar heridas profundas y reconciliar lo que parecía perdido, decidieron dedicar sus vidas a ayudar a otras parejas a encontrar el mismo milagro.</p>
            <blockquote>"No hay matrimonio tan roto que Dios no pueda reparar, ni familia tan herida que Su amor no pueda sanar."</blockquote>
            <p>Actualmente lideran el Ministerio de Familias, donde coordinan consejería prematrimonial, retiros de parejas y escuelas para padres. Su enfoque siempre ha sido práctico y vulnerable; enseñan desde sus propias cicatrices para mostrar que un matrimonio cimentado en la roca que es Cristo puede soportar cualquier tormenta.</p>
            <p>Bajo su liderazgo, cientos de matrimonios en la congregación han encontrado sanidad, perdón y herramientas bíblicas para criar a la próxima generación en el temor del Señor.</p>
        `
    },
    {
        id: "alba-arias",
        name: "Alba Arias",
        title: "Pastora",
        image: "/images/pastores/camilo_alba.webp",
        quote: "Mi mayor gozo no está en una posición o en un título, sino en pertenecer a la obra de Dios y ser útil en sus manos.",
        verse: "Juan 3:16 - 'Porque de tal manera amó Dios al mundo, que ha dado a su Hijo unigénito, para que todo aquel que en él cree, no se pierda, mas tenga vida eterna.'",
        shortStory: "Le apasiona enseñar, convencida de que la educación transforma vidas y le da el privilegio de sembrar conocimiento y valores.",
        fullStory: `
            <p>Antes de llegar a la congregación, la Pastora Alba Arias no había tenido acercamientos a ninguna iglesia ni una relación personal con Dios. Fue en este lugar donde experimentó la presencia del Espíritu Santo por primera vez, un encuentro que transformó su carácter, sanó su corazón y le dio una profunda identidad como hija amada. Esta revelación de la bondad del Padre la impulsó a compartir su amor con otros.</p>
            <blockquote>"Elijo Juan 3:16 porque nos muestra la esencia misma de lo que Él es y lo que quiere con cada uno de nosotros."</blockquote>
            <p>Lo que más le apasiona es enseñar, una vocación que también constituye su profesión. Alba cree firmemente que la educación transforma vidas y que, a través de ella, Dios le concede el privilegio de sembrar conocimiento y valores eternos en el corazón de cada estudiante.</p>
            <p><strong>Perfil Ministerial:</strong> A lo largo de su servicio en la casa de Dios, Alba ha apoyado en múltiples áreas. Comenzó colaborando en la limpieza del templo y en diversas tareas logísticas; posteriormente se integró al equipo de bienvenida para recibir con amor a todos los que llegaban. Más adelante sirvió en el ministerio infantil (sala cuna y escuela dominical), sembrando principios bíblicos en la niñez. Actualmente se desempeña en el ministerio pastoral, apoyando a los pastores principales en las áreas administrativa y financiera.</p>
            <p><strong>Perfil Familiar:</strong> Está casada con el Pastor Camilo Pájaro, a quien conoció en su etapa escolar. Juntos comenzaron asistiendo a los servicios de madrugón. Aunque en los inicios de su relación vivieron altibajos que los llevaron a separarse durante un año —período en el que Alba se alejó temporalmente de la iglesia—, el Señor restauró su lazo amoroso y ella regresó a la congregación. En 2014 se bautizaron y se casaron. En doce años de matrimonio, el Padre los ha sustentado y hecho crecer ministerialmente. Hoy en día, tienen dos hermosas hijas, Sara Valentina y Shaddai Antonella, y su historia es un testimonio de la fidelidad y provisión divina.</p>
        `
    },
    {
        id: "camilo-pajaro",
        name: "Camilo Pájaro",
        title: "Pastor",
        image: "/images/pastores/camilo_alba.webp",
        quote: "He entendido que si es Él quien me guía y me dirige, en mi vida todo terminará ayudando para bien.",
        verse: "Salmo 23:1 - 'Jehová es mi pastor; nada me faltará.'",
        shortStory: "Le apasiona habitar en la presencia del Padre y siente un profundo celo por apoyar y guiar a las almas perdidas.",
        fullStory: `
            <p>Antes de conocer al Señor, Camilo Pájaro vivía una vida volcada al baile, la música secular y su mayor prioridad: el béisbol, deporte en el cual se formaba activamente. Sin embargo, Dios intervino de forma providencial, llamándolo a abandonar lo que creía que era su propósito terrenal para alinear su vida con su propósito eterno. Llegó a los pies del Señor con inseguridades y maldiciones generacionales, de las cuales fue totalmente libertado por el amor y la misericordia divina.</p>
            <blockquote>"He entendido que si es Él quien me guía y me dirige, en mi vida todo terminará ayudando para bien."</blockquote>
            <p>A Camilo le apasiona habitar en la presencia de Dios, cultivar una relación cercana con el Padre y agradarle en todo. Asimismo, tiene un profundo celo por las almas perdidas, sintiendo el llamado de apoyar a quienes andan sin rumbo y guiarlos de vuelta a la senda de Cristo.</p>
            <p><strong>Perfil Ministerial:</strong> Su caminar en el servicio comenzó desde las tareas más sencillas, limpiando y colaborando con el aseo del templo. A medida que crecía espiritualmente, Dios abrió puertas en su liderazgo: se desempeñó como maestro de la Academia de Formación Ministerial, ministro de alabanza y miembro destacado de la agrupación musical Sonido de Gloria, y hoy en día sirve en el ministerio pastoral.</p>
            <p><strong>Perfil Familiar:</strong> Está casado con la Pastora Alba Arias, con quien comparte su vida y ministerio. Se conocieron en el colegio y dieron sus primeros pasos espirituales asistiendo a los madrugones de la iglesia. Tras superar una separación de un año, se bautizaron y casaron en el 2014. Hoy, junto a sus hijas Sara Valentina y Shaddai Antonella, testifican que el Señor ha sido su sustento inquebrantable durante doce años de matrimonio.</p>
        `
    },
    {
        id: "fernando-y-monica",
        name: "Fernando y Mónica",
        title: "Pastores de Discipulado",
        image: "/images/pastores/fernando_monica.webp",
        quote: "El verdadero crecimiento ocurre cuando caminamos lado a lado.",
        verse: "Hebreos 10:24 - 'Y considerémonos unos a otros para estimularnos al amor y a las buenas obras.'",
        shortStory: "La historia de la fidelidad, el servicio incondicional y el acompañamiento constante.",
        fullStory: `
            <p>Los pastores Fernando y Mónica representan la esencia del servicio incondicional y la fidelidad. Su caminar en la iglesia comenzó sirviendo en las áreas más silenciosas, donde nadie los veía, pero donde Dios formó el carácter de siervos que hoy los define.</p>
            <blockquote>"El discipulado no es un curso que se toma, es una vida que se comparte."</blockquote>
            <p>Su ministerio está enfocado en el crecimiento integral del creyente. Son los encargados de asegurar que cada persona que cruza las puertas de la congregación no solo se quede a escuchar un mensaje, sino que sea abrazada, integrada y formada a la imagen de Cristo a través del discipulado uno a uno y los grupos pequeños.</p>
            <p>Su hogar siempre ha sido una casa de puertas abiertas. A través de su ejemplo, enseñan que el liderazgo más efectivo es aquel que se ejerce con una toalla en las manos y la disposición de lavar los pies de los demás.</p>
        `
    },
    {
        id: "nehemias-morales",
        name: "Nehemías Morales",
        title: "Pastor de Consolidación",
        image: "/images/pastores/nehemias_morales.webp",
        quote: "Cada alma cuenta, cada vida es preciosa y cada nuevo creyente necesita un refugio.",
        verse: "Nehemías 2:18 - 'Entonces les declaré cómo la mano de mi Dios había sido buena sobre mí... Y dijeron: Levantémonos y edifiquemos. Así esforzaron sus manos para bien.'",
        shortStory: "Enfocado en la resiliencia, la construcción de comunidad y la fe inquebrantable.",
        fullStory: `
            <p>Haciendo honor a su nombre, el Pastor Nehemías Morales es un constructor y un restaurador de murallas espirituales. Su ministerio se especializa en cuidar a los que acaban de llegar, garantizando que ninguna vida que se entregue a Cristo quede a la deriva.</p>
            <blockquote>"El momento más frágil de un creyente son sus primeros pasos; ahí es donde la iglesia debe ser más fuerte."</blockquote>
            <p>La propia historia de Nehemías es una de profunda resiliencia y superación de adversidades imposibles mediante la fe. Con esa misma tenacidad lidera a los equipos de consolidación, llamando a cada nuevo creyente, visitando hospitales y organizando las redes de apoyo comunitario.</p>
            <p>Su vida es un faro de esperanza para aquellos que llegan a la iglesia con las murallas de su vida destruidas, mostrándoles que con Dios, siempre hay oportunidad para reedificar.</p>
        `
    },
    {
        id: "yair-macea",
        name: "Yair Macea",
        title: "Pastor Evangelístico",
        image: "/images/pastores/yair_macea.webp",
        quote: "No podemos quedarnos sentados mientras hay un mundo afuera que necesita a Jesús.",
        verse: "Marcos 16:15 - 'Y les dijo: Id por todo el mundo y predicad el evangelio a toda criatura.'",
        shortStory: "Un relato de gracia abrumadora, superación personal y un fuego evangelístico inextinguible.",
        fullStory: `
            <p>El Pastor Yair Macea es el impulso misional de la congregación. Su encuentro con Cristo lo sacó de un pasado de oscuridad profunda, y desde el momento en que sus ojos fueron abiertos a la gracia salvadora, no ha podido dejar de hablar de lo que Dios hizo por él.</p>
            <blockquote>"La iglesia no es un club de personas santas, es un hospital de rescate y la calle es nuestra principal sala de emergencias."</blockquote>
            <p>Con un estilo de predicación ferviente y directo, Yair lidera las jornadas de evangelismo, misiones urbanas y el alcance a sectores vulnerables de la ciudad. Su mayor pasión es ver a las personas reconciliadas con Dios y bautizadas.</p>
            <p>Él es la prueba de que Dios no desperdicia ninguna parte de nuestro pasado, sino que lo convierte en un testimonio poderoso para rescatar a quienes hoy se encuentran en los mismos lugares de donde fuimos sacados.</p>
        `
    },
    {
        id: "yanedith-wilches",
        name: "Yanedith Wilches",
        title: "Pastora de Intercesión",
        image: "/images/pastores/yanedith_wilches.webp",
        quote: "Las batallas más grandes de nuestra vida se ganan primero de rodillas.",
        verse: "Proverbios 31:25 - 'Fuerza y honor son su vestidura; Y se ríe de lo por venir.'",
        shortStory: "La fuerza inquebrantable de una mujer virtuosa, la intercesión y la compasión por los vulnerables.",
        fullStory: `
            <p>La Pastora Yanedith Wilches es el motor espiritual de la congregación a través de la oración y la intercesión. Su testimonio está tejido por múltiples experiencias de respuestas milagrosas a la oración, sanidades divinas y provisión en tiempos de escasez.</p>
            <blockquote>"Cuando la iglesia ora, el cielo responde. No hay fortaleza espiritual que resista el clamor de un pueblo unido."</blockquote>
            <p>Ella lidera los ejércitos de intercesores, las vigilias y el ministerio de mujeres. Su liderazgo compasivo, pero firme como el acero en el ámbito espiritual, ha inspirado a cientos de mujeres a levantarse como columnas en sus hogares y guerreras en el Reino.</p>
            <p>Yanedith combina una profunda dulzura pastoral con una autoridad espiritual que se hace evidente cada vez que dirige a la congregación a buscar el rostro de Dios en adoración y ruego.</p>
        `
    },
    {
        id: "martina-herrera",
        name: "Martina Herrera",
        title: "Pastora Fundadora",
        image: "/images/pastores/martina_herrera.webp",
        isMain: true,
        quote: "La obra de Dios se edifica con fe, obediencia y amor por las almas.",
        verse: "1 Corintios 3:9 - 'Porque nosotros somos colaboradores de Dios, y vosotros sois labranza de Dios, edificio de Dios.'",
        shortStory: "Pastora fundadora del ministerio Comunidad Cristiana El Faro junto a su esposo, Alejandro Ariza Torres, quien ya partió y está con el Señor.",
        fullStory: `
            <p>La Pastora Martina Herrera es la pastora fundadora del ministerio Comunidad Cristiana El Faro. Junto a su esposo, Alejandro Ariza Torres, quien ya partió y está con el Señor, sembró con fe, oración y perseverancia las bases espirituales de esta casa.</p>
            <blockquote>"La obra de Dios se edifica con fe, obediencia y amor por las almas."</blockquote>
            <p>Desde los primeros días del ministerio, la Pastora Martina ha sido un pilar de oración, fidelidad y cuidado pastoral. Su corazón maternal ha acompañado a generaciones de creyentes que encontraron en ella una pastora, una consejera y una madre espiritual.</p>
            <p>Su legado permanece vivo en la familia espiritual de Comunidad Cristiana El Faro: una iglesia levantada para amar a Dios, servir a las personas y continuar la obra que el Señor puso en sus manos.</p>
        `
    }
];
