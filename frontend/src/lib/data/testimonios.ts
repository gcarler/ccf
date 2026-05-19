export interface Testimonial {
    id: number;
    content: string;
    emotion?: string;
    media_type?: "text" | "image" | "video" | "podcast" | string;
    media_url?: string | null;
    image_url?: string | null;
    video_url?: string | null;
    podcast_url?: string | null;
    author?: { id: number; username: string; role?: string; avatarUrl?: string } | null;
    is_approved?: boolean;
    show_on_home?: boolean;
}

export const PREMIUM_TESTIMONIALS: Testimonial[] = [
    {
        id: 101,
        content: "Mi matrimonio estaba al borde del divorcio. Habíamos intentado absolutamente todo: terapias, libros, consejos de amigos. Nada funcionaba y la distancia entre nosotros era abismal. Llegar a FARO no solo salvó nuestra relación, sino que nos enseñó a perdonar desde la raíz, arrancando años de resentimiento. Hoy, somos líderes y ayudamos a otras parejas a encontrar esa misma luz y restauración en sus hogares.",
        emotion: "Restauración",
        author: { id: 1, username: "Carlos Mendoza", role: "Padre de familia", avatarUrl: "https://i.pravatar.cc/150?img=11" },
        is_approved: true,
        show_on_home: true
    },
    {
        id: 102,
        content: "Luché contra la ansiedad y la depresión profunda durante toda mi juventud. Aquí encontré un refugio seguro, una familia espiritual que no me juzgó, sino que me amó hasta que sané por completo. He recuperado mi propósito y la alegría de vivir.",
        emotion: "Sanidad",
        author: { id: 2, username: "Daniela Vega", role: "Diseñadora Gráfica", avatarUrl: "https://i.pravatar.cc/150?img=5" },
        is_approved: true
    },
    {
        id: 103,
        content: "Pensaba que tener éxito financiero era el propósito supremo de la vida, pero por dentro estaba completamente vacío y agotado. Cuando conocí el mensaje de Jesús en esta comunidad, mis prioridades cambiaron radicalmente. Ahora uso mis talentos empresariales para servir al Reino.",
        emotion: "Propósito",
        author: { id: 3, username: "Alejandro Torres", role: "Emprendedor", avatarUrl: "https://i.pravatar.cc/150?img=68" },
        is_approved: true
    },
    {
        id: 104,
        content: "Me diagnosticaron una enfermedad autoinmune degenerativa y los médicos no me daban esperanza de recuperación a largo plazo. La iglesia entera se unió en oración y ayuno por mí. No solo he visto un milagro médico en mi cuerpo que sorprendió a los especialistas, sino una fe inquebrantable que nació en mi corazón.",
        emotion: "Milagro",
        author: { id: 4, username: "Valeria Castro", role: "Docente", avatarUrl: "https://i.pravatar.cc/150?img=9" },
        is_approved: true
    },
    {
        id: 105,
        content: "Llegué a FARO arrastrando adicciones que me habían costado mi trabajo y mi familia. Sentía que había tocado fondo. Aquí no encontré religión condenatoria, encontré verdadera libertad. El programa de discipulado me dio las herramientas y el acompañamiento constante para reconstruir mi vida desde cero, y hoy llevo 3 años sobrio.",
        emotion: "Libertad",
        author: { id: 5, username: "Diego Ramírez", role: "Músico", avatarUrl: "https://i.pravatar.cc/150?img=12" },
        is_approved: true
    },
    {
        id: 106,
        content: "Llegar a una ciudad nueva sin conocer absolutamente a nadie me hizo sentir profundamente sola y aislada. Encontrar un Faro en Casa me dio más que amigos de domingo; me dio hermanos de vida con quienes comparto mis victorias y derrotas cada día.",
        emotion: "Comunidad",
        author: { id: 6, username: "Mariana Ortiz", role: "Estudiante de Medicina", avatarUrl: "https://i.pravatar.cc/150?img=20" },
        is_approved: true
    },
    {
        id: 107,
        content: "El mensaje es claro, profundo, bíblicamente sólido y sumamente práctico. Como joven, buscaba respuestas intelectuales a mi fe en medio de un mundo escéptico y aquí las encontré. La enseñanza me ha retado a ser un mejor profesional ético y un creyente con convicciones firmes que sabe defender su esperanza.",
        emotion: "Crecimiento",
        author: { id: 7, username: "Mateo Silva", role: "Ingeniero de Software", avatarUrl: "https://i.pravatar.cc/150?img=33" },
        is_approved: true
    },
    {
        id: 108,
        content: "Después de perder a mi esposo tras una larga batalla contra el cáncer, sentí que mi mundo se apagaba para siempre. El equipo pastoral me acompañó en cada etapa aguda de mi duelo. Su amor incondicional y paciencia fue el faro que me guio de vuelta a la luz cuando todo estaba oscuro. Hoy vuelvo a sonreír.",
        emotion: "Esperanza",
        author: { id: 8, username: "Isabella Rojas", role: "Madre y Viuda", avatarUrl: "https://i.pravatar.cc/150?img=43" },
        is_approved: true
    },
    {
        id: 109,
        content: "Fui criado en la iglesia, pero me alejé por más de diez años persiguiendo placeres vacíos. Regresar me daba muchísima vergüenza, pensando en el qué dirán, pero el recibimiento que tuve fue idéntico al del Padre al hijo pródigo. Hubo una fiesta en los cielos y abrazos genuinos en la tierra que derritieron mi orgullo.",
        emotion: "Gracia",
        author: { id: 9, username: "Andrés Vargas", role: "Arquitecto", avatarUrl: "https://i.pravatar.cc/150?img=53" },
        is_approved: true
    },
    {
        id: 110,
        content: "Servir en el equipo de jóvenes me ha transformado completamente. Entré buscando que alguien me ministrara a mí porque venía rota, y terminé descubriendo que mi mayor bendición estaba en consolar a otros. FARO me formó como líder, como mujer de fe y como mentora de una nueva generación encendida por Dios.",
        emotion: "Liderazgo",
        author: { id: 10, username: "Camila Herrera", role: "Coordinadora Juvenil", avatarUrl: "https://i.pravatar.cc/150?img=44" },
        is_approved: true
    }
];
