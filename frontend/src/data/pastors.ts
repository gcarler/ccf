export interface Pastor {
    id: string;
    name: string;
    title: string;
    image: string;
    quote: string;
    verse: string;
    shortStory: string;
    fullStory: string;
}

export const PASTORS: Pastor[] = [
    {
        id: "histar-ariza",
        name: "Histar Ariza",
        title: "Pastor Principal",
        image: "/pastores/histar_ariza_1777656780660.png",
        quote: "Nuestra mayor recompensa es ver corazones transformados por el amor del Padre.",
        verse: "Jeremías 3:15 - 'Y os daré pastores según mi corazón, que os apacienten con ciencia y con inteligencia.'",
        shortStory: "El llamado pastoral, la visión de expansión y el corazón de paternidad espiritual que guía a nuestra congregación.",
        fullStory: `
            <p>El Pastor Histar Ariza ha sido un pilar fundamental en la fundación y consolidación de la Comunidad Cristiana Alfaro. Su ministerio nació de un profundo encuentro personal con la paternidad de Dios, lo que marcó para siempre su forma de liderar, amar y guiar a la iglesia.</p>
            <blockquote>"El ministerio no se trata de construir edificios grandes, sino de edificar familias fuertes que reflejen el carácter de Cristo."</blockquote>
            <p>Con más de dos décadas de servicio ininterrumpido, su enseñanza se caracteriza por la profundidad teológica combinada con una aplicación práctica y compasiva. Su visión principal es ver a cada persona de la comunidad no solo como un asistente, sino como un hijo espiritual llamado a cumplir un propósito eterno.</p>
            <p>A lo largo de los años, el Pastor Histar ha liderado proyectos de expansión, siembra de nuevas misiones y ha formado a decenas de líderes que hoy sirven a lo largo de toda la congregación. Su testimonio es un recordatorio vivo de que cuando Dios llama, también respalda, provee y sostiene.</p>
        `
    },
    {
        id: "alex-y-elvia",
        name: "Alex y Elvia",
        title: "Pastores de Familias",
        image: "/pastores/alex_elvia_1777656808218.png",
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
        id: "camilo-alba",
        name: "Camilo Alba",
        title: "Pastor de Jóvenes",
        image: "/pastores/camilo_alba_1777656794964.png",
        quote: "Un joven rendido a Cristo es una flecha encendida en las manos de Dios.",
        verse: "1 Timoteo 4:12 - 'Ninguno tenga en poco tu juventud, sino sé ejemplo de los creyentes en palabra, conducta, amor, espíritu, fe y pureza.'",
        shortStory: "Un relato vibrante sobre el liderazgo juvenil, la pasión por la adoración y el avivamiento.",
        fullStory: `
            <p>Con un corazón que late por la próxima generación, el Pastor Camilo Alba lidera con energía, creatividad y una pasión desbordante por ver a los jóvenes experimentar un avivamiento genuino. Su historia está marcada por una transformación radical durante sus años de adolescencia, cuando Dios lo rescató y le dio un propósito claro: levantar una generación que no se avergüenza del Evangelio.</p>
            <blockquote>"No queremos una fe heredada por costumbre, sino una fe encendida por convicción."</blockquote>
            <p>Camilo es conocido por su enfoque dinámico en la enseñanza y su talento para la adoración profética. Ha sido fundamental en la creación de los grandes congresos juveniles y los campamentos que han marcado un antes y un después en cientos de vidas.</p>
            <p>Su mayor anhelo es ver a jóvenes profesionales, estudiantes y artistas usando sus talentos para la expansión del Reino, demostrando que seguir a Jesús es la aventura más grande que existe.</p>
        `
    },
    {
        id: "fernando-y-monica",
        name: "Fernando y Mónica",
        title: "Pastores de Discipulado",
        image: "/pastores/fernando_monica_1777656831456.png",
        quote: "El verdadero crecimiento ocurre cuando caminamos lado a lado.",
        verse: "Hebreos 10:24 - 'Y considerémonos unos a otros para estimularnos al amor y a las buenas obras.'",
        shortStory: "La historia de la fidelidad, el servicio incondicional y el acompañamiento constante.",
        fullStory: `
            <p>Los pastores Fernando y Mónica representan la esencia del servicio incondicional y la fidelidad. Su caminar en la iglesia comenzó sirviendo en las áreas más silenciosas, donde nadie los veía, pero donde Dios formó el carácter de siervos que hoy los define.</p>
            <blockquote>"El discipulado no es un curso que se toma, es una vida que se comparte."</blockquote>
            <p>Su ministerio está enfocado en el crecimiento integral del creyente. Son los encargados de asegurar que cada persona que cruza las puertas de CCF no solo se quede a escuchar un mensaje, sino que sea abrazada, integrada y formada a la imagen de Cristo a través del discipulado uno a uno y los grupos pequeños.</p>
            <p>Su hogar siempre ha sido una casa de puertas abiertas. A través de su ejemplo, enseñan que el liderazgo más efectivo es aquel que se ejerce con una toalla en las manos y la disposición de lavar los pies de los demás.</p>
        `
    },
    {
        id: "luis-ricardo-meza",
        name: "Luis Ricardo Meza Gutiérrez",
        title: "Pastor de Enseñanza",
        image: "/pastores/luis_ricardo_meza_1777656765476.png",
        quote: "La Palabra de Dios, correctamente dividida, es el alimento que da vida a la Iglesia.",
        verse: "Esdras 7:10 - 'Porque Esdras había preparado su corazón para inquirir la ley de Jehová y para cumplirla, y para enseñar en Israel sus estatutos y decretos.'",
        shortStory: "Un testimonio de transformación profunda y pasión inagotable por la enseñanza de la Palabra.",
        fullStory: `
            <p>El Pastor Luis Ricardo Meza Gutiérrez llegó a los pies de Cristo buscando respuestas a las inquietudes más profundas de su intelecto y su alma. Lo que encontró fue una verdad tan innegable y un amor tan avasallador que cambió el rumbo de sus estudios y de su vida por completo.</p>
            <blockquote>"Cuando la mente es iluminada por la revelación de la Escritura, el corazón inevitablemente se enciende en adoración."</blockquote>
            <p>Dotado de una aguda capacidad para la exégesis bíblica y la enseñanza apologética, Luis Ricardo es un defensor apasionado de la sana doctrina. Ha liderado el Instituto Bíblico y la Academia de la iglesia, formando teológicamente a los nuevos obreros y asegurando que las raíces doctrinales de la congregación sean profundas y firmes.</p>
            <p>Su testimonio nos recuerda que Dios redime nuestro intelecto y lo usa como un instrumento poderoso para derribar argumentos y llevar todo pensamiento cautivo a la obediencia a Cristo.</p>
        `
    },
    {
        id: "nehemias-morales",
        name: "Nehemías Morales",
        title: "Pastor de Consolidación",
        image: "/pastores/nehemias_morales_1777656877353.png",
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
        image: "/pastores/yair_macea_1777656845407.png",
        quote: "No podemos quedarnos sentados mientras hay un mundo afuera que necesita a Jesús.",
        verse: "Marcos 16:15 - 'Y les dijo: Id por todo el mundo y predicad el evangelio a toda criatura.'",
        shortStory: "Un relato de gracia abrumadora, superación personal y un fuego evangelístico inextinguible.",
        fullStory: `
            <p>El Pastor Yair Macea es el impulso misional de CCF. Su encuentro con Cristo lo sacó de un pasado de oscuridad profunda, y desde el momento en que sus ojos fueron abiertos a la gracia salvadora, no ha podido dejar de hablar de lo que Dios hizo por él.</p>
            <blockquote>"La iglesia no es un club de personas santas, es un hospital de rescate y la calle es nuestra principal sala de emergencias."</blockquote>
            <p>Con un estilo de predicación ferviente y directo, Yair lidera las jornadas de evangelismo, misiones urbanas y el alcance a sectores vulnerables de la ciudad. Su mayor pasión es ver a las personas reconciliadas con Dios y bautizadas.</p>
            <p>Él es la prueba de que Dios no desperdicia ninguna parte de nuestro pasado, sino que lo convierte en un testimonio poderoso para rescatar a quienes hoy se encuentran en los mismos lugares de donde fuimos sacados.</p>
        `
    },
    {
        id: "yanedith-wilches",
        name: "Yanedith Wilches",
        title: "Pastora de Intercesión",
        image: "/pastores/yanedith_wilches_1777656863437.png",
        quote: "Las batallas más grandes de nuestra vida se ganan primero de rodillas.",
        verse: "Proverbios 31:25 - 'Fuerza y honor son su vestidura; Y se ríe de lo por venir.'",
        shortStory: "La fuerza inquebrantable de una mujer virtuosa, la intercesión y la compasión por los vulnerables.",
        fullStory: `
            <p>La Pastora Yanedith Wilches es el motor espiritual de la congregación a través de la oración y la intercesión. Su testimonio está tejido por múltiples experiencias de respuestas milagrosas a la oración, sanidades divinas y provisión en tiempos de escasez.</p>
            <blockquote>"Cuando la iglesia ora, el cielo responde. No hay fortaleza espiritual que resista el clamor de un pueblo unido."</blockquote>
            <p>Ella lidera los ejércitos de intercesores, las vigilias y el ministerio de mujeres. Su liderazgo compasivo, pero firme como el acero en el ámbito espiritual, ha inspirado a cientos de mujeres a levantarse como columnas en sus hogares y guerreras en el Reino.</p>
            <p>Yanedith combina una profunda dulzura pastoral con una autoridad espiritual que se hace evidente cada vez que dirige a la congregación a buscar el rostro de Dios en adoración y ruego.</p>
        `
    }
];
