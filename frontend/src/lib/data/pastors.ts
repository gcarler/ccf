export interface PastorProfile {
    id: string;
    slug: string;
    name: string;
    role: "Apóstol" | "Pastor";
    category: "apostles" | "pastors";
    description: string;
    img: string;
    social?: {
        instagram?: string;
        facebook?: string;
    };
}

export const PASTORS: PastorProfile[] = [
    {
        id: "1",
        slug: "luis-ricardo-meza",
        name: "Luis Ricardo Meza Gutiérrez",
        role: "Apóstol",
        category: "apostles",
        description: "Fundador y visionario principal de Comunidad CCF. El Apóstol Luis Ricardo ha dedicado más de tres décadas a la expansión del evangelio, plantando iglesias y levantando generaciones de líderes íntegros. Su ministerio se caracteriza por una enseñanza profunda, una fe inquebrantable y un corazón pastoral genuino. Ha sido instrumento de Dios para transformar miles de vidas, estableciendo un legado de amor, excelencia y servicio incondicional a la comunidad. Es autor, conferencista internacional y un padre espiritual para muchos.",
        img: "/images/pastores/luis_ricardo_meza.png",
        social: { instagram: "https://instagram.com/comunidadccf", facebook: "https://facebook.com/comunidadccf" }
    },
    {
        id: "2",
        slug: "histar-ariza",
        name: "Histar Ariza Herrera",
        role: "Apóstol",
        category: "apostles",
        description: "Pilar fundamental en la consolidación de la iglesia y un maestro excepcional de las Escrituras. El Apóstol Histar posee una gracia especial para impartir sabiduría, restaurar familias y guiar a la congregación hacia una madurez espiritual profunda. Su liderazgo compasivo y su enfoque en el discipulado personal han sido vitales para el crecimiento sostenido de CCF. Dedica gran parte de su tiempo a la mentoría pastoral y al desarrollo de estrategias para el fortalecimiento del núcleo familiar.",
        img: "/images/pastores/histar_ariza.png",
        social: { instagram: "https://instagram.com/comunidadccf", facebook: "https://facebook.com/comunidadccf" }
    },
    {
        id: "3",
        slug: "camilo-alba",
        name: "Camilo Pájaro y Alba Estrada",
        role: "Pastor",
        category: "pastors",
        description: "Una pareja pastoral con un corazón gigante para la restauración de matrimonios y el cuidado de los personas. Camilo y Alba lideran ministerios enfocados en la sanidad interior, la consejería familiar y la integración. Su calidez, empatía y testimonio de vida han inspirado a innumerables familias a encontrar esperanza y reconstruir sus hogares sobre el fundamento de Cristo. Son conocidos por su hospitalidad y por hacer sentir a todos como en casa.",
        img: "/images/pastores/camilo_alba.png",
        social: { instagram: "https://instagram.com/comunidadccf", facebook: "https://facebook.com/comunidadccf" }
    },
    {
        id: "4",
        slug: "alex-elvia",
        name: "Alex Cabarcas y Elvia Ángulo",
        role: "Pastor",
        category: "pastors",
        description: "Apasionados por el servicio social y la movilización comunitaria. Alex y Elvia son la fuerza detrás de muchas iniciativas de alcance que conectan a la iglesia con las necesidades de la ciudad. Su liderazgo dinámico fomenta una cultura de generosidad y acción. Trabajan incansablemente en la asimilación de nuevos creyentes, asegurando que cada persona que llega a CCF encuentre su lugar, descubra sus dones y comience a servir con alegría.",
        img: "/images/pastores/alex_elvia.png",
        social: { instagram: "https://instagram.com/comunidadccf", facebook: "https://facebook.com/comunidadccf" }
    },
    {
        id: "5",
        slug: "fernando-monica",
        name: "Fernando Ascencio y Mónica de Arco",
        role: "Pastor",
        category: "pastors",
        description: "Líderes estratégicos y mentores de vida. Fernando y Mónica tienen una unción especial para la enseñanza práctica y la consolidación de procesos educativos dentro de la iglesia. Dirigen programas de discipulado avanzado y capacitación ministerial. Su enfoque alegre pero estructurado ayuda a los creyentes a transicionar de asistentes a discípulos comprometidos. Siempre están listos para escuchar, orientar y celebrar las victorias de cada persona de la congregación.",
        img: "/images/pastores/fernando_monica.png",
        social: { instagram: "https://instagram.com/comunidadccf", facebook: "https://facebook.com/comunidadccf" }
    },
    {
        id: "6",
        slug: "yair-macea",
        name: "Yair Macea",
        role: "Pastor",
        category: "pastors",
        description: "Voz profética y líder de la nueva generación. El Pastor Yair combina su talento en la adoración con un fervor contagioso por ver a los jóvenes vivir una fe radical. Bajo su guía, los ministerios juveniles han experimentado un avivamiento caracterizado por la autenticidad, la creatividad y la pasión por la presencia de Dios. Su energía inagotable y su habilidad para comunicar verdades eternas en un lenguaje contemporáneo lo hacen un referente vital en CCF.",
        img: "/images/pastores/yair_macea.png",
        social: { instagram: "https://instagram.com/comunidadccf", facebook: "https://facebook.com/comunidadccf" }
    },
    {
        id: "7",
        slug: "yanedith-wilches",
        name: "Yanedith Wilches",
        role: "Pastor",
        category: "pastors",
        description: "Mujer de oración y guerrera espiritual. La Pastora Yanedith lidera el ministerio de intercesión con una convicción férrea en el poder de la oración para transformar atmósferas y romper cadenas. Su vida es un testimonio de fidelidad y compasión. Además de su labor intercesora, es una consejera sabia y una madre espiritual para muchas mujeres, guiándolas hacia su identidad y propósito en Dios con gracia y firmeza.",
        img: "/images/pastores/yanedith_wilches.png",
        social: { instagram: "https://instagram.com/comunidadccf", facebook: "https://facebook.com/comunidadccf" }
    },
    {
        id: "8",
        slug: "nehemias-morales",
        name: "Nehemías Morales",
        role: "Pastor",
        category: "pastors",
        description: "Estratega, administrador y constructor de equipos. El Pastor Nehemías asegura que la visión espiritual de CCF esté respaldada por una estructura operativa de excelencia. Su mente analítica, combinada con un profundo llamado pastoral, le permite liderar equipos de voluntarios y coordinar la logística de la iglesia con precisión. Es un maestro en el arte de optimizar recursos para maximizar el impacto del evangelio, operando siempre detrás de escena con gran humildad.",
        img: "/images/pastores/nehemias_morales.png",
        social: { instagram: "https://instagram.com/comunidadccf", facebook: "https://facebook.com/comunidadccf" }
    }
];

export function getPastorBySlug(slug: string): PastorProfile | undefined {
    return PASTORS.find(p => p.slug === slug);
}
