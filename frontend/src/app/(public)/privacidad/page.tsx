"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { Shield, ChevronRight, Mail, Calendar, ArrowUp } from "lucide-react";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import { SITE_NAME, SITE_URL, SITE_EMAIL } from "@/lib/site-config";
import CmsPageOverride from "@/components/public/cms/CmsPageOverride";

const LAST_UPDATE = "12 de junio de 2026";

const FALLBACK_SECTIONS = [
    { id: "responsables", title: "1. Responsables del tratamiento" },
    { id: "datos-recopilados", title: "2. Datos que recopilamos" },
    { id: "finalidades", title: "3. Finalidades del tratamiento" },
    { id: "bases-legales", title: "4. Bases legales" },
    { id: "derechos", title: "5. Derechos del titular" },
    { id: "procedimiento", title: "6. Procedimiento para ejercer derechos" },
    { id: "terceros", title: "7. Transferencia y transmisión a terceros" },
    { id: "cookies", title: "8. Cookies y tecnologías similares" },
    { id: "menores", title: "9. Menores de edad" },
    { id: "seguridad", title: "10. Seguridad de la información" },
    { id: "conservacion", title: "11. Conservación de datos" },
    { id: "cambios", title: "12. Cambios a esta política" },
    { id: "contacto", title: "13. Canal de atención" },
];

export default function PrivacidadPage() {
    const [activeSection, setActiveSection] = useState("");
    const [showScrollTop, setShowScrollTop] = useState(false);
    const privacyPage = useCmsV2Page('privacy');
    const privacyContent = privacyPage?.blocks?.privacy;
    const privacy = (privacyContent?.parsed && typeof privacyContent.parsed === "object" && !Array.isArray(privacyContent.parsed))
        ? privacyContent.parsed as Record<string, unknown>
        : {};
    const lastUpdate = typeof privacy.last_update === "string" ? privacy.last_update : LAST_UPDATE;
    const summary = typeof privacy.summary === "string"
        ? privacy.summary
        : "";
    const sections = useMemo(() => (
        Array.isArray(privacy.sections) && privacy.sections.length > 0
            ? privacy.sections
                .map((item) => item && typeof item === "object" ? item as Record<string, unknown> : {})
                .map((item) => ({
                    id: typeof item.id === "string" ? item.id : "",
                    title: typeof item.title === "string" ? item.title : "",
                }))
                .filter((item) => item.id && item.title)
            : FALLBACK_SECTIONS
    ), [privacy.sections]);

    useEffect(() => {
        const onScroll = () => {
            setShowScrollTop(window.scrollY > 400);
            for (const s of [...sections].reverse()) {
                const el = document.getElementById(s.id);
                if (el && el.getBoundingClientRect().top <= 120) {
                    setActiveSection(s.id);
                    return;
                }
            }
            setActiveSection("");
        };
        window.addEventListener("scroll", onScroll, { passive: true });
        return () => window.removeEventListener("scroll", onScroll);
    }, [sections]);

    const scrollTo = (id: string) => {
        const el = document.getElementById(id);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    return (
        <CmsPageOverride slug="privacidad">
        <main className="min-h-screen bg-[hsl(var(--bg-primary))] dark:bg-[#07080c] pt-[88px]">

            {/* ── Hero ── */}
            <section className="relative overflow-hidden border-b border-[hsl(var(--border))]/60 dark:border-white/[0.05]">
                <div className="absolute inset-0 pointer-events-none">
                    <div className="absolute -top-40 -right-40 w-[500px] h-[500px] rounded-full bg-gradient-to-br from-[hsl(var(--primary))/0.06] to-transparent blur-3xl" />
                </div>
                <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12 py-14 md:py-20 relative z-10">
                    <div className="flex items-center gap-2 text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-6">
                        <Link href="/" className="hover:text-[hsl(var(--primary))] transition-colors">Inicio</Link>
                        <ChevronRight size={12} />
                        <span className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Política de Privacidad</span>
                    </div>
                    <div className="flex items-start gap-5">
                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[hsl(var(--primary))/0.15] to-[hsl(var(--primary))/0.05] flex items-center justify-center shrink-0 border border-[hsl(var(--primary))/0.15] shadow-sm">
                            <Shield size={24} className="text-[hsl(var(--primary))]" />
                        </div>
                        <div>
                            <h1 className="text-3xl md:text-4xl lg:text-5xl font-black text-[hsl(var(--text-primary))] dark:text-white tracking-tight mb-3">
                                Política de Privacidad
                            </h1>
                            <div className="flex flex-wrap items-center gap-4 text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                <span className="inline-flex items-center gap-1.5">
                                    <Calendar size={12} />
                                    Última actualización: {lastUpdate}
                                </span>
                                <span className="inline-flex items-center gap-1.5">
                                    <Shield size={12} />
                                    Conforme a la Ley 1581 de 2012 — Colombia
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Resumen ejecutivo */}
                    <div className="mt-8 p-5 rounded-2xl bg-gradient-to-r from-[hsl(var(--primary))/0.06] to-transparent border border-[hsl(var(--primary))/0.12]">
                        <p className="text-sm md:text-base text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed">
                            {summary || (
                                <>
                                    Esta política describe cómo <strong className="text-[hsl(var(--text-primary))] dark:text-white">PLES SAS</strong> y la{" "}
                                    <strong className="text-[hsl(var(--text-primary))] dark:text-white">{SITE_NAME}</strong> recopilan,
                                    usan, almacenan y protegen tus datos personales cuando utilizas la plataforma{" "}
                                    <strong className="text-[hsl(var(--text-primary))] dark:text-white">{SITE_URL}</strong>. Tu privacidad es un
                                    derecho fundamental y nos comprometemos a respetarlo en cada interacción.
                                </>
                            )}
                        </p>
                    </div>
                </div>
            </section>

            {/* ── Contenido + Índice ── */}
            <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12 py-12 md:py-16">
                <div className="flex flex-col lg:flex-row gap-10 lg:gap-16 items-start">

                    {/* Índice lateral */}
                    <aside className="w-full lg:w-72 shrink-0 lg:sticky lg:top-[108px]">
                        <div className="rounded-2xl border border-[hsl(var(--border))]/60 dark:border-white/[0.06] bg-[hsl(var(--bg-primary))] dark:bg-[#0f1117] p-5 shadow-sm">
                            <p className="text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-4">
                                Contenido
                            </p>
                            <nav className="space-y-1">
                                {sections.map((s) => (
                                    <button
                                        key={s.id}
                                        onClick={() => scrollTo(s.id)}
                                        className={`w-full text-left text-xs px-3 py-2 rounded-lg transition-all duration-200 ${
                                            activeSection === s.id
                                                ? "bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] font-semibold"
                                                : "text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.04]"
                                        }`}
                                    >
                                        {s.title}
                                    </button>
                                ))}
                            </nav>
                        </div>
                    </aside>

                    {/* Artículo principal */}
                    <article className="flex-1 min-w-0 prose-policy">

                        <Section id="responsables" title="1. Responsables del tratamiento">
                            <p>Los responsables del tratamiento de datos personales recopilados a través de la plataforma <strong>{SITE_URL}</strong> son:</p>
                            <InfoCard>
                                <InfoRow label="Razón social" value="PLES SAS" />
                                <InfoRow label="NIT" value="Por confirmar" />
                                <InfoRow label="Domicilio" value="Colombia" />
                                <InfoRow label="Sitio web" value="ples.com.co" link="https://ples.com.co" />
                                <InfoRow label="Correo" value="privacidad@ples.com.co" link="mailto:privacidad@ples.com.co" />
                            </InfoCard>
                            <InfoCard>
                                <InfoRow label="Nombre" value={SITE_NAME} />
                                <InfoRow label="Domicilio" value="Colombia" />
                                <InfoRow label="Correo" value={SITE_EMAIL} link={`mailto:${SITE_EMAIL}`} />
                            </InfoCard>
                            <p>
                                PLES SAS actúa como <strong>encargado del tratamiento</strong> en su calidad de proveedor tecnológico de la plataforma.
                                {SITE_NAME} actúa como <strong>responsable del tratamiento</strong> respecto a los datos de sus miembros, asistentes y usuarios.
                            </p>
                        </Section>

                        <Section id="datos-recopilados" title="2. Datos que recopilamos">
                            <p>Recopilamos únicamente los datos necesarios para prestar los servicios de la plataforma:</p>
                            <Subsection title="Datos de identificación">
                                <ul>
                                    <li>Nombre completo</li>
                                    <li>Correo electrónico</li>
                                    <li>Número de teléfono o celular (opcional)</li>
                                    <li>Ciudad y país de residencia</li>
                                </ul>
                            </Subsection>
                            <Subsection title="Datos de participación comunitaria">
                                <ul>
                                    <li>Inscripción a eventos, grupos o cursos</li>
                                    <li>Solicitudes de consejería o peticiones de oración</li>
                                    <li>Respuestas a formularios pastorales</li>
                                    <li>Historial de asistencia (solo para miembros registrados)</li>
                                </ul>
                            </Subsection>
                            <Subsection title="Datos de uso de la plataforma">
                                <ul>
                                    <li>Dirección IP y datos de dispositivo (navegador, sistema operativo)</li>
                                    <li>Páginas visitadas y tiempo de sesión</li>
                                    <li>Interacciones con contenido (prédicas, cursos, eventos)</li>
                                    <li>Datos de cookies (ver sección 8)</li>
                                </ul>
                            </Subsection>
                            <p>
                                <strong>No recopilamos</strong> datos sensibles como origen racial o étnico, orientación sexual,
                                datos biométricos, información de salud ni datos financieros, salvo que el titular los comparta voluntariamente
                                en contextos pastorales con el consentimiento explícito correspondiente.
                            </p>
                        </Section>

                        <Section id="finalidades" title="3. Finalidades del tratamiento">
                            <p>Tus datos son tratados exclusivamente para las siguientes finalidades:</p>
                            <ol>
                                <li><strong>Gestión de membresía:</strong> registro, autenticación y administración de tu cuenta en la plataforma.</li>
                                <li><strong>Comunicaciones pastorales:</strong> envío del boletín, avisos sobre eventos, actividades y noticias de la comunidad.</li>
                                <li><strong>Participación en actividades:</strong> inscripción y seguimiento a eventos, grupos de célula, cursos bíblicos y retiros.</li>
                                <li><strong>Atención y cuidado pastoral:</strong> gestión de solicitudes de consejería, visitas o acompañamiento espiritual.</li>
                                <li><strong>Mejora de la plataforma:</strong> análisis estadístico de uso para optimizar la experiencia del usuario.</li>
                                <li><strong>Cumplimiento legal:</strong> atención a requerimientos de autoridades competentes conforme a la ley colombiana.</li>
                            </ol>
                            <p>
                                Tus datos <strong>no serán</strong> utilizados para fines comerciales ajenos a la misión de{" "}
                                {SITE_NAME} ni vendidos a terceros bajo ninguna circunstancia.
                            </p>
                        </Section>

                        <Section id="bases-legales" title="4. Bases legales">
                            <p>El tratamiento de tus datos personales se fundamenta en las siguientes bases legales:</p>
                            <ul>
                                <li><strong>Consentimiento (Ley 1581/2012, art. 9):</strong> cuando aceptas esta política al registrarte o utilizar la plataforma.</li>
                                <li><strong>Relación contractual:</strong> cuando tu participación como miembro o asistente implica la prestación de un servicio.</li>
                                <li><strong>Interés legítimo:</strong> para el envío de comunicaciones sobre actividades directamente relacionadas con tu vinculación a la comunidad.</li>
                                <li><strong>Cumplimiento de obligaciones legales:</strong> cuando la ley colombiana exige la conservación o reporte de ciertos datos.</li>
                            </ul>
                        </Section>

                        <Section id="derechos" title="5. Derechos del titular">
                            <p>
                                Conforme a la <strong>Ley Estatutaria 1581 de 2012</strong> y el <strong>Decreto 1074 de 2015</strong>,
                                como titular de tus datos personales tienes los siguientes derechos:
                            </p>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 not-prose my-5">
                                {[
                                    { right: "Acceso", desc: "Conocer qué datos tuyos tenemos almacenados y cómo los estamos usando." },
                                    { right: "Actualización", desc: "Solicitar la corrección de datos inexactos, incompletos o desactualizados." },
                                    { right: "Rectificación", desc: "Modificar datos que no correspondan a la realidad." },
                                    { right: "Supresión", desc: "Solicitar la eliminación de tus datos cuando no exista obligación legal de conservarlos." },
                                    { right: "Revocatoria", desc: "Revocar el consentimiento otorgado para el tratamiento de tus datos." },
                                    { right: "Queja ante la SIC", desc: "Presentar queja ante la Superintendencia de Industria y Comercio si consideras que se han vulnerado tus derechos." },
                                ].map((item) => (
                                    <div key={item.right} className="p-4 rounded-xl border border-[hsl(var(--border))]/60 dark:border-white/[0.06] bg-[hsl(var(--surface-1))] dark:bg-white/[0.02]">
                                        <p className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--primary))] mb-1">{item.right}</p>
                                        <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed">{item.desc}</p>
                                    </div>
                                ))}
                            </div>
                        </Section>

                        <Section id="procedimiento" title="6. Procedimiento para ejercer derechos">
                            <p>Para ejercer cualquiera de los derechos descritos en la sección anterior, puedes:</p>
                            <ol>
                                <li>
                                    Enviar un correo a{" "}
                                    <a href={`mailto:${SITE_EMAIL}`} className="text-[hsl(var(--primary))] hover:underline">
                                        {SITE_EMAIL}
                                    </a>{" "}
                                    indicando: tu nombre completo, tipo y número de documento de identidad, la solicitud específica y los datos de contacto donde deseas recibir respuesta.
                                </li>
                                <li>
                                    Recibirás una confirmación de recepción en un plazo no mayor a <strong>2 días hábiles</strong>.
                                </li>
                                <li>
                                    La solicitud será atendida en un plazo máximo de <strong>10 días hábiles</strong> a partir de la fecha de recepción.
                                    Si no es posible atenderla en dicho plazo, se te informarán los motivos de la demora y la fecha estimada de respuesta,
                                    la cual no podrá superar los <strong>5 días hábiles adicionales</strong>.
                                </li>
                            </ol>
                            <p>
                                Si la solicitud es presentada por un tercero distinto al titular, deberá acreditar la representación legal
                                o el poder otorgado por el titular para actuar en su nombre.
                            </p>
                        </Section>

                        <Section id="terceros" title="7. Transferencia y transmisión a terceros">
                            <p>
                                Tus datos <strong>no son vendidos</strong> ni cedidos a terceros con fines comerciales.
                                Sin embargo, podemos compartir datos en las siguientes circunstancias limitadas:
                            </p>
                            <ul>
                                <li>
                                    <strong>Proveedores tecnológicos:</strong> PLES SAS, como encargado del tratamiento, accede a los datos
                                    para operar y mantener la plataforma. Estos accesos están regulados por acuerdos de confidencialidad y procesamiento de datos.
                                </li>
                                <li>
                                    <strong>Proveedores de servicios de correo y mensajería:</strong> para el envío de comunicaciones y notificaciones
                                    (boletín, recordatorios de eventos). Estos proveedores solo acceden a los datos estrictamente necesarios para prestar el servicio.
                                </li>
                                <li>
                                    <strong>Autoridades competentes:</strong> cuando exista una obligación legal, una orden judicial o un requerimiento
                                    de la Superintendencia de Industria y Comercio (SIC).
                                </li>
                            </ul>
                            <p>
                                Cualquier transmisión de datos a proveedores fuera de Colombia se realiza únicamente hacia países
                                que ofrecen un nivel adecuado de protección de datos o bajo garantías contractuales equivalentes.
                            </p>
                        </Section>

                        <Section id="cookies" title="8. Cookies y tecnologías similares">
                            <p>
                                La plataforma utiliza cookies y tecnologías similares para mejorar tu experiencia de navegación.
                            </p>
                            <Subsection title="Tipos de cookies que usamos">
                                <ul>
                                    <li><strong>Cookies esenciales:</strong> necesarias para el funcionamiento básico de la plataforma (autenticación, sesión). No pueden desactivarse.</li>
                                    <li><strong>Cookies de análisis:</strong> nos permiten entender cómo se usa la plataforma para mejorarla. Recopilan datos de forma anónima y agregada.</li>
                                    <li><strong>Cookies de preferencias:</strong> recuerdan tus configuraciones (tema claro/oscuro, idioma).</li>
                                </ul>
                            </Subsection>
                            <p>
                                Puedes configurar tu navegador para rechazar cookies o ser notificado cuando se envíen.
                                Ten en cuenta que desactivar ciertas cookies puede afectar el funcionamiento de algunas funciones de la plataforma.
                            </p>
                        </Section>

                        <Section id="menores" title="9. Menores de edad">
                            <p>
                                La plataforma <strong>no está dirigida a menores de 14 años</strong>. No recopilamos datos personales
                                de menores de forma intencionada. Si tienes conocimiento de que un menor nos ha proporcionado datos
                                sin el consentimiento de sus padres o tutores, contáctanos para proceder a su eliminación.
                            </p>
                            <p>
                                Para el registro de menores en actividades de la comunidad (grupos juveniles, escuela bíblica, campamentos),
                                el consentimiento será solicitado directamente a los padres o representantes legales a través de los formularios
                                físicos o digitales correspondientes.
                            </p>
                        </Section>

                        <Section id="seguridad" title="10. Seguridad de la información">
                            <p>
                                Implementamos medidas técnicas y organizativas adecuadas para proteger tus datos personales
                                contra pérdida, alteración, divulgación no autorizada o acceso indebido:
                            </p>
                            <ul>
                                <li>Transmisión de datos cifrada mediante <strong>HTTPS/TLS</strong>.</li>
                                <li>Contraseñas almacenadas con algoritmos de <strong>hash criptográfico</strong> (nunca en texto plano).</li>
                                <li>Acceso a datos restringido al personal autorizado bajo el principio de <strong>mínimo privilegio</strong>.</li>
                                <li>Copias de seguridad periódicas con cifrado en reposo.</li>
                                <li>Monitoreo continuo de la infraestructura para detectar accesos no autorizados.</li>
                            </ul>
                            <p>
                                En caso de una violación de seguridad que afecte tus datos, te notificaremos conforme a lo
                                establecido en la normativa colombiana vigente.
                            </p>
                        </Section>

                        <Section id="conservacion" title="11. Conservación de datos">
                            <p>
                                Conservamos tus datos personales durante el tiempo necesario para cumplir las finalidades
                                descritas en esta política y durante el plazo exigido por la ley colombiana:
                            </p>
                            <ul>
                                <li><strong>Datos de cuenta activa:</strong> mientras mantengas una cuenta registrada en la plataforma.</li>
                                <li><strong>Datos de participación en eventos:</strong> hasta 2 años después de la realización del evento.</li>
                                <li><strong>Datos contables y de facturación:</strong> 10 años conforme al Código de Comercio.</li>
                                <li><strong>Datos tras solicitud de supresión:</strong> serán eliminados o anonimizados en un plazo máximo de 30 días hábiles,
                                    salvo que exista una obligación legal que exija su conservación.</li>
                            </ul>
                        </Section>

                        <Section id="cambios" title="12. Cambios a esta política">
                            <p>
                                Nos reservamos el derecho de actualizar esta política cuando sea necesario para reflejar cambios
                                en nuestra plataforma, en la legislación aplicable o en nuestras prácticas de tratamiento de datos.
                            </p>
                            <p>
                                Cuando realicemos cambios materiales, te notificaremos por correo electrónico (si tienes una cuenta
                                registrada) y publicaremos un aviso destacado en la plataforma con al menos <strong>15 días de anticipación</strong>.
                                La fecha de &quot;última actualización&quot; al inicio de esta página siempre reflejará la versión vigente.
                            </p>
                            <p>
                                El uso continuado de la plataforma tras la entrada en vigencia de los cambios constituye tu aceptación
                                de la política actualizada.
                            </p>
                        </Section>

                        <Section id="contacto" title="13. Canal de atención">
                            <p>
                                Para cualquier consulta, solicitud o queja relacionada con el tratamiento de tus datos personales,
                                puedes comunicarte a través de los siguientes canales:
                            </p>
                            <div className="not-prose mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <ContactCard
                                    title={SITE_NAME}
                                    email={SITE_EMAIL}
                                    detail="Para consultas relacionadas con tu participación en la comunidad."
                                />
                                <ContactCard
                                    title="PLES SAS — Soporte técnico"
                                    email="privacidad@ples.com.co"
                                    detail="Para consultas relacionadas con la plataforma tecnológica."
                                    web="https://ples.com.co"
                                />
                            </div>
                            <p className="mt-5">
                                También puedes presentar una queja ante la{" "}
                                <strong>Superintendencia de Industria y Comercio (SIC)</strong> a través de{" "}
                                <a href="https://www.sic.gov.co" target="_blank" rel="noopener noreferrer" className="text-[hsl(var(--primary))] hover:underline">
                                    www.sic.gov.co
                                </a>.
                            </p>
                        </Section>

                    </article>
                </div>
            </div>

            {/* Scroll to top */}
            {showScrollTop && (
                <button
                    onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
                    className="fixed bottom-6 right-6 z-50 w-11 h-11 rounded-full bg-[hsl(var(--primary))] text-white shadow-xl shadow-[hsl(var(--primary))/0.3] flex items-center justify-center hover:scale-110 transition-all"
                    aria-label="Volver arriba"
                >
                    <ArrowUp size={18} />
                </button>
            )}
        </main>
        </CmsPageOverride>
    );
}

/* ── Componentes internos ── */

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
    return (
        <section id={id} className="mb-12 scroll-mt-[108px]">
            <h2 className="text-xl md:text-2xl font-black text-[hsl(var(--text-primary))] dark:text-white tracking-tight mb-1">
                {title}
            </h2>
            <div className="h-0.5 w-10 rounded-full bg-gradient-to-r from-[hsl(var(--primary))] to-[hsl(var(--secondary))] mb-5" />
            <div className="space-y-4 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] text-sm md:text-base leading-relaxed [&_strong]:text-[hsl(var(--text-primary))] [&_strong]:dark:text-white [&_a]:text-[hsl(var(--primary))] [&_a:hover]:underline [&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:space-y-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-2">
                {children}
            </div>
        </section>
    );
}

function Subsection({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="my-3">
            <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] mb-1">{title}</p>
            {children}
        </div>
    );
}

function InfoCard({ children }: { children: React.ReactNode }) {
    return (
        <div className="my-3 rounded-xl border border-[hsl(var(--border))]/60 dark:border-white/[0.06] bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] divide-y divide-[hsl(var(--border))] dark:divide-white/[0.04] overflow-hidden text-sm">
            {children}
        </div>
    );
}

function InfoRow({ label, value, link }: { label: string; value: string; link?: string }) {
    return (
        <div className="flex flex-wrap gap-2 px-4 py-2.5">
            <span className="font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] w-32 shrink-0">{label}</span>
            {link ? (
                <a href={link} target={link.startsWith("http") ? "_blank" : undefined} rel="noopener noreferrer"
                    className="text-[hsl(var(--primary))] hover:underline">
                    {value}
                </a>
            ) : (
                <span className="text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{value}</span>
            )}
        </div>
    );
}

function ContactCard({ title, email, detail, web }: { title: string; email: string; detail: string; web?: string }) {
    return (
        <div className="p-5 rounded-2xl border border-[hsl(var(--border))]/60 dark:border-white/[0.06] bg-[hsl(var(--bg-primary))] dark:bg-[#0f1117] shadow-sm space-y-3">
            <p className="font-bold text-[hsl(var(--text-primary))] dark:text-white text-sm">{title}</p>
            <a href={`mailto:${email}`}
                className="inline-flex items-center gap-2 text-sm text-[hsl(var(--primary))] hover:underline">
                <Mail size={13} /> {email}
            </a>
            {web && (
                <a href={web} target="_blank" rel="noopener noreferrer"
                    className="block text-xs text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors">
                    {web}
                </a>
            )}
            <p className="text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed">{detail}</p>
        </div>
    );
}
