export interface CourseItem {
    id: string;
    tag?: string;
    modality?: string;
    title: string;
    desc: string;
    excerpt?: string;
    cta?: string;
    lessons?: number;
    imageUrl?: string;
    syllabus?: string[];
    instructor?: string;
}

export interface BookItem {
    id: string;
    title: string;
    author: string;
    price: string;
    img: string;
    desc: string;
}

// Fallback local — solo se usa si la API no responde.
// Los slugs coinciden con los de la BD para que los links sean coherentes.
export const PREMIUM_COURSES: CourseItem[] = [
    {
        id: "el-evangelio-que-no-conocias",
        title: "El Evangelio que no Conocías",
        excerpt: "¿Qué pasa cuando el mensaje que llamamos 'buenas noticias' ha sido secuestrado por el moralismo religioso y la sentimentalidad barata? Este curso es un ejercicio de recuperación.",
        desc: "Después de dos mil años, el Evangelio corre el riesgo de volverse una marca, un sistema de reglas o una terapia emocional. Este curso es una excavación arqueológica hasta el núcleo del mensaje original de Jesús y Pablo.",
        tag: "Fundamentos Radicales",
        modality: "Presencial & Online",
        lessons: 10,
        cta: "Quiero Inscribirme",
        imageUrl: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=600&fit=crop",
        instructor: "Pastor Luis Ricardo Meza Gutiérrez",
        syllabus: [
            "El evangelio que Pablo predicó vs. el que predicamos hoy",
            "Gracia irresistible: ¿liberación o licencia para pecar?",
            "El reino que Jesús anunció no era una religión",
            "La cruz sin el resucitado es solo una tragedia griega",
        ]
    },
    {
        id: "jesus-el-subversivo",
        title: "Jesús el Subversivo: Historia, Contexto y Escándalo",
        excerpt: "El Jesús manso y gentil de las estampitas religiosas no sobreviviría un minuto en el Palestina del siglo I. Este curso estudia al Jesús real: el que perturbó al Imperio y fue ejecutado por razones políticas.",
        desc: "La mayoría de los retratos de Jesús son proyecciones de las culturas que los producen. Este curso aplica herramientas de historia crítica para recuperar al Jesús del contexto judío del Segundo Templo.",
        tag: "Teología Crítica",
        modality: "100% Online",
        lessons: 8,
        cta: "Quiero Conocerlo de Verdad",
        imageUrl: "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=800&h=600&fit=crop",
        instructor: "Academia FARO — Teología Histórica",
        syllabus: [
            "Palestina en el siglo I: Roma, Herodes y el Templo",
            "Las fuentes no-bíblicas sobre Jesús",
            "Las Bienaventuranzas como manifiesto político-espiritual",
            "La resurrección y su impacto histórico-político",
        ]
    },
    {
        id: "escatologia-sin-miedo",
        title: "Escatología sin Apocalipsis-Fobia",
        excerpt: "Décadas de películas del Arrebatamiento y calculadoras de fechas del fin del mundo. Ya es hora de leer el Apocalipsis como lo que es: una carta de resistencia y esperanza.",
        desc: "El libro más leído del Nuevo Testamento es también el más malinterpretado. Este curso desmonta el dispensacionalismo moderno y regresa al texto original.",
        tag: "Profecía & Esperanza",
        modality: "100% Online",
        lessons: 8,
        cta: "Quiero Leer el Apocalipsis de Nuevo",
        imageUrl: "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&h=600&fit=crop",
        instructor: "Academia FARO — Teología Bíblica",
        syllabus: [
            "Historia del dispensacionalismo: Darby, Scofield y el 'Left Behind'",
            "El Apocalipsis como género literario",
            "Los símbolos del Apocalipsis y su clave de lectura",
            "Escatología como ética: cómo cambia nuestra vida",
        ]
    },
    {
        id: "teodicea-dios-frente-al-sufrimiento",
        title: "Teodicea: Dios Frente al Sufrimiento",
        excerpt: "Las respuestas fáciles al sufrimiento son una ofensa a quienes sufren. Este curso afronta sin filtros el problema más difícil de la fe cristiana.",
        desc: "Desde la filosofía griega hasta la Shoah, desde Job hasta C.S. Lewis escribiendo tras la muerte de su esposa. No terminarás con todas las respuestas, sino con un Dios más real.",
        tag: "Apologética Profunda",
        modality: "Híbrido",
        lessons: 10,
        cta: "Quiero Afrontar Esta Pregunta",
        imageUrl: "https://images.unsplash.com/photo-1476611338391-6f395a0ebc7b?w=800&h=600&fit=crop",
        instructor: "Academia FARO — Filosofía y Teología",
        syllabus: [
            "El problema del mal: formulación lógica y evidencial",
            "Las respuestas que no funcionan",
            "Job: cuando Dios mismo tiene que responder",
            "La teología de la Cruz como respuesta: Moltmann",
        ]
    },
];

export const PREMIUM_BOOKS: BookItem[] = [
    {
        id: "b1",
        title: "La Búsqueda de Dios",
        author: "A.W. Tozer",
        price: "$15.00",
        img: "https://picsum.photos/seed/tozer-book/400/600",
        desc: "Un clásico indispensable sobre la sed espiritual y la verdadera intimidad con el Creador."
    },
    {
        id: "b2",
        title: "Mero Cristianismo",
        author: "C.S. Lewis",
        price: "$18.50",
        img: "https://picsum.photos/seed/cslewis-book/400/600",
        desc: "La apología moderna más brillante sobre las bases objetivas de la fe cristiana."
    },
    {
        id: "b3",
        title: "El Costo del Discipulado",
        author: "Dietrich Bonhoeffer",
        price: "$14.00",
        img: "https://picsum.photos/seed/bonhoeffer-book/400/600",
        desc: "Escrito desde la resistencia al nazismo: la diferencia entre la gracia barata y la gracia costosa."
    },
    {
        id: "b4",
        title: "La Política de Jesús",
        author: "John Howard Yoder",
        price: "$16.00",
        img: "https://picsum.photos/seed/yoder-book/400/600",
        desc: "El texto fundacional de la teología política anabaptista. Jesús como modelo de ética social."
    }
];
