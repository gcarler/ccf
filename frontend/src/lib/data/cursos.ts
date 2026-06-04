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

export const PREMIUM_COURSES: CourseItem[] = [
    {
        id: "fundamentos-teologia",
        title: "Fundamentos de Teología",
        excerpt: "Un recorrido intensivo por las doctrinas principales que sostienen nuestra fe, diseñado para forjar convicciones inquebrantables.",
        desc: "Este curso está diseñado para equipar a líderes y personas activos con una comprensión profunda de la gracia, la salvación y la escatología básica. A través de este programa, aprenderás a defender tu fe con amor y a enseñar a otros con claridad bíblica absoluta.",
        tag: "Certificación Master",
        modality: "Presencial & Online",
        lessons: 12,
        cta: "Inscribirse",
        imageUrl: "https://picsum.photos/seed/teologia-faro/800/600",
        instructor: "Pastor Luis Ricardo Meza Gutiérrez",
        syllabus: [
            "Introducción a la Apologética",
            "La Doctrina de la Gracia Irresistible",
            "El carácter de Dios revelado",
            "Escatología Básica para tiempos modernos"
        ]
    },
    {
        id: "liderazgo-servicial",
        title: "Liderazgo Servicial Avanzado",
        excerpt: "Aprende a liderar como Jesús: desde abajo hacia arriba. Técnicas prácticas para la gestión de equipos ministeriales.",
        desc: "El mundo nos enseña a liderar desde una posición de poder, pero el Reino exige liderar desde la toalla y el lebrillo. Este curso romperá tus paradigmas sobre autoridad e influencia.",
        tag: "Ministerio",
        modality: "100% Online",
        lessons: 8,
        cta: "Inscribirse",
        imageUrl: "https://picsum.photos/seed/liderazgo-servicial/800/600",
        instructor: "Equipo Pastoral",
        syllabus: [
            "El paradigma del siervo",
            "Resolución de conflictos en el ministerio",
            "Multiplicación de líderes",
            "Inteligencia Emocional Espiritual"
        ]
    },
    {
        id: "matrimonios-solidos",
        title: "Diseño Original: Matrimonios Sólidos",
        excerpt: "Descubre el plano de Dios para el matrimonio y la familia en un mundo que ha perdido el rumbo.",
        desc: "Un curso transformador para parejas, tanto para aquellos que están a punto de casarse como para quienes buscan restaurar y fortalecer su pacto matrimonial.",
        tag: "Familia",
        modality: "Presencial",
        lessons: 6,
        cta: "Inscribirse",
        imageUrl: "https://picsum.photos/seed/matrimonios-solidos/800/600",
        instructor: "Ministerio de Familias FARO",
        syllabus: [
            "El Pacto vs. El Contrato",
            "Comunicación y Perdón Radical",
            "Finanzas en Pareja",
            "Intimidad y Propósito Compartido"
        ]
    },
    {
        id: "apologetica-jovenes",
        title: "Apologética para Universitarios",
        excerpt: "Respuestas intelectualmente sólidas para las preguntas más difíciles que enfrentarás en la academia.",
        desc: "La universidad no tiene que ser el lugar donde mueren las convicciones. Aprende a defender tu fe en debates éticos, científicos y filosóficos modernos.",
        tag: "Jóvenes",
        modality: "Híbrido",
        lessons: 10,
        cta: "Inscribirse",
        imageUrl: "https://picsum.photos/seed/apologetica/800/600",
        instructor: "Academia FARO Jóvenes",
        syllabus: [
            "Ciencia y Fe: ¿Son compatibles?",
            "El Problema del Mal y el Sufrimiento",
            "La historicidad de la resurrección",
            "Relativismo moral en el campus"
        ]
    }
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
        title: "Liderazgo Espiritual",
        author: "J. Oswald Sanders",
        price: "$12.00",
        img: "https://picsum.photos/seed/sanders-book/400/600",
        desc: "Principios infalibles para aquellos que están llamados a guiar al pueblo de Dios."
    },
    {
        id: "b4",
        title: "Héroes de la Fe",
        author: "Orlando Boyer",
        price: "$14.00",
        img: "https://picsum.photos/seed/boyer-book/400/600",
        desc: "Biografías electrizantes de hombres y mujeres que transformaron el mundo en el poder del Espíritu."
    }
];
