"use client";

import Link from "next/link";
import React from "react";
import { useContentBlock } from "@/hooks/useContent";

export default function PublicHomePage() {
    const { data: heroContent } = useContentBlock("faro_home_hero");

    const heroEyebrow = heroContent?.eyebrow || "Comunidad FARO";
    const heroTitleLead = heroContent?.title_lead || "Ilumina tu";
    const heroTitleAccent = heroContent?.title_accent || "Camino";
    const heroDescription =
        heroContent?.description ||
        "Una comunidad vibrante donde la fe encuentra propósito. Descubre un espacio diseñado para guiarte, inspirarte y conectarte con lo trascendente.";
    const heroPrimaryCta = heroContent?.primary_cta || "Únete a nosotros";
    const heroSecondaryCta = heroContent?.secondary_cta || "Ver Predicaciones";

    return (
        <main className="pt-20">
            {/* Hero Section: The Radiant Guide */}
            <section className="relative min-h-[819px] flex items-center px-8 md:px-24 overflow-hidden bg-faro-surface-container-lowest">
                <div className="absolute top-0 right-0 w-2/3 h-full opacity-20 pointer-events-none">
                    <div className="absolute inset-0 faro-beam-glow"></div>
                </div>
                <div className="grid grid-cols-12 gap-8 w-full z-10">
                    <div className="col-span-12 md:col-span-7 flex flex-col justify-center">
                        <span className="label-md font-label uppercase tracking-[0.2em] text-faro-primary mb-6">{heroEyebrow}</span>
                        <h1 className="font-headline text-5xl md:text-7xl font-extrabold text-faro-on-background tracking-tight leading-[1.1] mb-8">
                            {heroTitleLead} <span className="text-faro-primary">{heroTitleAccent}</span>
                        </h1>
                        <p className="text-faro-on-surface-variant text-lg md:text-xl max-w-xl leading-relaxed mb-10">
                            {heroDescription}
                        </p>
                        <div className="flex flex-wrap gap-4">
                            <button className="faro-hero-gradient text-white px-8 py-4 rounded-[0.75rem] font-semibold shadow-lg shadow-faro-primary/20 hover:opacity-90 transition-all">
                                {heroPrimaryCta}
                            </button>
                            <button className="bg-faro-surface-bright text-faro-on-surface px-8 py-4 rounded-[0.75rem] font-semibold border border-faro-outline-variant/20 hover:bg-faro-surface-container-high transition-all">
                                {heroSecondaryCta}
                            </button>
                        </div>
                    </div>
                    <div className="hidden md:block col-span-5 relative">
                        <div className="aspect-[4/5] rounded-[0.5rem] overflow-hidden shadow-2xl rotate-2 hover:rotate-0 transition-transform duration-700 bg-faro-surface-container-high">
                            <img alt="Interior of a modern lighthouse-style architecture" className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAz78aXa2qNQ1jGydSEwIbbTrNWO9LoGzhRShhql8ZORpTR0fFFhdDW5sgxm5PjScfDcZOnTiChsYsgKKnTv6HGGKjuPW7U5Heq_Gf8zVJ1hR-uSHDqwfTqdSPAfNukwwZh7li8HMXcynTHhBGHpyG17fPbXiJLcVw4yC73p5spgl2gldkYezE8oi-tJtbALtu36almHf0BHRCvC_pNvUzCx21eoEIYszGo7lUKT4esv63L4BxbsP4jsxXaCXY_1SgzrA9Oh6UpZxuS" />
                        </div>
                        <div className="absolute -bottom-12 -left-12 w-64 h-64 rounded-[0.5rem] overflow-hidden shadow-xl -rotate-6 hidden lg:block border-8 border-faro-surface-container-lowest bg-faro-surface-container">
                            <img alt="Community gathering" className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBir6959YdCNlDdLJ-RnUDuOpfcMqjpktnNZyMCgAs4CbM5MhRGiXtspo0I5Y2YtZhVibV-wUhMBDOuXzpfLAmqNyqm-JypmCESNhspOGcU8d401iimNv6OymVkZ3nI_2_Psdcw73dTeMd0WLooghb16pF1NHizXhSZSTEB7PRM59yZmycCINixQHGQ5bXME64MCBmdSmqrS-W58ZpFjG19dW4oyNQHwrcbJlmuU5h7fmszOZR5T-qO5rDQHdiMqFrewffsJl14f3n7" />
                        </div>
                    </div>
                </div>
            </section>

            {/* Welcome Section (Asymmetric Bento) */}
            <section className="py-24 px-8 md:px-24 bg-faro-surface">
                <div className="mb-16">
                    <h2 className="font-headline text-3xl md:text-4xl font-bold text-faro-on-background mb-4">Bienvenidos a Casa</h2>
                    <div className="w-20 h-1 bg-faro-primary rounded-[0.75rem]"></div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {/* Large Feature */}
                    <div className="md:col-span-2 bg-faro-surface-container-low rounded-[0.5rem] p-10 flex flex-col justify-between group overflow-hidden relative">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-faro-primary/5 rounded-[0.75rem] -mr-20 -mt-20 group-hover:scale-110 transition-transform duration-500"></div>
                        <div className="z-10">
                            <span className="material-symbols-outlined text-4xl text-faro-primary mb-6">auto_awesome</span>
                            <h3 className="font-headline text-2xl font-bold mb-4">Conocer a Jesús</h3>
                            <p className="text-faro-on-surface-variant max-w-md leading-relaxed">
                                Descubre la base de nuestra fe a través de un viaje personal y transformador. En FARO, te acompañamos en cada paso de tu crecimiento espiritual.
                            </p>
                        </div>
                        <div className="mt-12 z-10">
                            <Link href="/conocer-a-jesus" className="text-faro-primary font-bold flex items-center gap-2 group-hover:gap-4 transition-all">
                                Empezar el camino <span className="material-symbols-outlined">arrow_forward</span>
                            </Link>
                        </div>
                    </div>

                    {/* Secondary Feature */}
                    <div className="bg-faro-primary-container/20 rounded-[0.5rem] p-10 flex flex-col justify-center items-center text-center border border-faro-primary/10">
                        <span className="material-symbols-outlined text-5xl text-faro-primary mb-6">format_quote</span>
                        <h3 className="font-headline text-xl font-bold mb-4">Testimonios</h3>
                        <p className="text-faro-on-surface-variant text-sm mb-8 italic">
                            &quot;Encontré una familia y un propósito real cuando más lo necesitaba. FARO iluminó mi oscuridad.&quot;
                        </p>
                        <span className="font-bold text-faro-primary">— Elena M.</span>
                    </div>

                    {/* Bento Row 2 */}
                    <div className="bg-faro-surface-container-high rounded-[0.5rem] p-8 flex items-center gap-6">
                        <div className="w-16 h-16 rounded-[0.75rem] bg-faro-primary/10 flex items-center justify-center shrink-0">
                            <span className="material-symbols-outlined text-faro-primary text-3xl">menu_book</span>
                        </div>
                        <div>
                            <h4 className="font-bold text-faro-on-surface">Librería</h4>
                            <p className="text-xs text-faro-on-surface-variant">Recursos para profundizar en tu estudio bíblico.</p>
                        </div>
                    </div>

                    <div className="bg-faro-surface-container-high rounded-[0.5rem] p-8 flex items-center gap-6">
                        <div className="w-16 h-16 rounded-[0.75rem] bg-faro-primary/10 flex items-center justify-center shrink-0">
                            <span className="material-symbols-outlined text-faro-primary text-3xl">schedule</span>
                        </div>
                        <div>
                            <h4 className="font-bold text-faro-on-surface">Horarios</h4>
                            <p className="text-xs text-faro-on-surface-variant">Consulta nuestras reuniones presenciales y online.</p>
                        </div>
                    </div>

                    <div className="bg-faro-surface-container-high rounded-[0.5rem] p-8 flex items-center gap-6">
                        <div className="w-16 h-16 rounded-[0.75rem] bg-faro-primary/10 flex items-center justify-center shrink-0">
                            <span className="material-symbols-outlined text-faro-primary text-3xl">mail</span>
                        </div>
                        <div>
                            <h4 className="font-bold text-faro-on-surface">Contacto</h4>
                            <p className="text-xs text-faro-on-surface-variant">¿Tienes alguna duda? Escríbenos directamente.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Highlights Section */}
            <section className="py-24 px-8 md:px-24 bg-faro-surface-container-low">
                <div className="flex justify-between items-end mb-16">
                    <div>
                        <span className="label-md font-label uppercase tracking-widest text-faro-primary mb-4 block">Actualidad</span>
                        <h2 className="font-headline text-3xl md:text-4xl font-bold text-faro-on-background">Actividades Recientes</h2>
                    </div>
                    <Link href="/faro/eventos" className="hidden md:block text-faro-primary font-semibold border-b border-faro-primary hover:border-b-2 transition-all pb-1">Ver todo el calendario</Link>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
                    {/* Activity Card 1 */}
                    <div className="group">
                        <div className="aspect-video rounded-[0.5rem] overflow-hidden mb-6 shadow-md bg-faro-surface-container-highest">
                            <img alt="Worship event" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDc33oXvitpSsv0Bwpp8ckpG0f8NoO0EqqhjqJ1g_mOtV_Bgdk17kdTNUcmazaYqFnXKdnH1jPnYJHmU_VCsmRlskD6LVCCKvHcUzNEWrBHhjYjDgcE9bcDW3VwhsMTygn4itVBz_BancTkIVG635KLZsJD4WpW4VK4h1miWc8IzuA7SzSwlqVcAx5L26WWALF851WYyDLJq6zxJR08z2eTSzgj54caSVquNtrSGpVXnRJ1c7xkzbc-rsnL-S0QHbBjy4kdLGJjk8Xd" />
                        </div>
                        <div className="flex gap-4 mb-4">
                            <span className="bg-faro-secondary-container text-faro-on-secondary-container px-3 py-1 rounded-[0.75rem] text-[10px] font-bold uppercase tracking-wider">Música</span>
                            <span className="text-faro-on-surface-variant text-[10px] font-medium uppercase tracking-wider">12 OCT 2023</span>
                        </div>
                        <h3 className="font-headline text-xl font-bold mb-3 group-hover:text-faro-primary transition-colors">Noche de Adoración: Luz en Casa</h3>
                        <p className="text-faro-on-surface-variant text-sm leading-relaxed line-clamp-2">
                            Una experiencia inmersiva de música y oración para toda la familia en nuestra sede central.
                        </p>
                    </div>
                    {/* Activity Card 2 */}
                    <div className="group">
                        <div className="aspect-video rounded-[0.5rem] overflow-hidden mb-6 shadow-md bg-faro-surface-container-highest">
                            <img alt="Training workshop" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDUDN3aTmJGORWz7ydz9LeUr0ZjdD4RbIFuF8C2AVqCF5xYrBzaswBC3WZJcWBEOK2xt0UM7CYyyAPz9ZeR95VZA3CTd_ozX_5wLKw40HvN26cczDQJzULGxeBJjbfvBDy1yVi9xVh6oDktGYRwRg9Rvu1zhZs3LBdcEdu8lstCdqLqvHQm--TOARtL48fjt7wwskronL2gMwITPik_1ej3eCv5hBS8iimdufuWWL5Uq2H7Xt5Z08eN20HCQCAa6R_0tWqW0qwrknVj" />
                        </div>
                        <div className="flex gap-4 mb-4">
                            <span className="bg-faro-secondary-container text-faro-on-secondary-container px-3 py-1 rounded-[0.75rem] text-[10px] font-bold uppercase tracking-wider">Liderazgo</span>
                            <span className="text-faro-on-surface-variant text-[10px] font-medium uppercase tracking-wider">15 OCT 2023</span>
                        </div>
                        <h3 className="font-headline text-xl font-bold mb-3 group-hover:text-faro-primary transition-colors">Curso: Liderazgo con Propósito</h3>
                        <p className="text-faro-on-surface-variant text-sm leading-relaxed line-clamp-2">
                            Herramientas prácticas para influir positivamente en tu entorno laboral y personal.
                        </p>
                    </div>
                    {/* Activity Card 3 */}
                    <div className="group">
                        <div className="aspect-video rounded-[0.5rem] overflow-hidden mb-6 shadow-md bg-faro-surface-container-highest">
                            <img alt="Social work" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCaCEE312T5mZgSA_QssV6J8YRfi-86mm9PDWDwSQftCaIUoYs1vtARVm7Np1eiSajqK-mNt96ZD2Ez37JZ-Iu9Q6epd9KE65PogaKJxR2pp6ZDsV_aWt-J8v1ef17KRror9w-wrODRxx9K2zSGL0WHsna_FAjS03VISwJpIp3UB-kjnJ8XoTlaOJhka6Afj3TAmIsfTBopgVjRgtXAQX61-lhHk7mS19JHG15hpNjvtQ9KNAiit3r-Lam9N3TlGe6QYqFoNCdN6V6-" />
                        </div>
                        <div className="flex gap-4 mb-4">
                            <span className="bg-faro-secondary-container text-faro-on-secondary-container px-3 py-1 rounded-[0.75rem] text-[10px] font-bold uppercase tracking-wider">Social</span>
                            <span className="text-faro-on-surface-variant text-[10px] font-medium uppercase tracking-wider">20 OCT 2023</span>
                        </div>
                        <h3 className="font-headline text-xl font-bold mb-3 group-hover:text-faro-primary transition-colors">Proyecto: Manos que Iluminan</h3>
                        <p className="text-faro-on-surface-variant text-sm leading-relaxed line-clamp-2">
                            Nuestra jornada mensual de apoyo comunitario y entrega de alimentos en zonas vulnerables.
                        </p>
                    </div>
                </div>
            </section>

            {/* Newsletter / CTA */}
            <section className="py-24 px-8 md:px-24">
                <div className="bg-faro-primary rounded-3xl p-12 md:p-20 relative overflow-hidden text-center">
                    <div className="absolute inset-0 opacity-10 pointer-events-none">
                        <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_30%_50%,#fff_0%,transparent_50%)]"></div>
                    </div>
                    <div className="relative z-10 max-w-2xl mx-auto">
                        <h2 className="font-headline text-3xl md:text-5xl font-black text-white mb-6">¿Quieres recibir nuestras novedades?</h2>
                        <p className="text-faro-primary-fixed mb-10 text-lg">Únete a nuestra lista de correo y recibe meditaciones semanales e información sobre eventos exclusivos.</p>
                        <form className="flex flex-col md:flex-row gap-4">
                            <input className="flex-grow rounded-[0.75rem] border-none px-8 py-4 focus:ring-2 focus:ring-white bg-white/20 text-white placeholder:text-white/60" placeholder="Tu correo electrónico" type="email" />
                            <button type="button" className="bg-white text-faro-primary px-10 py-4 rounded-[0.75rem] font-bold hover:bg-faro-surface-dim transition-all">
                                Suscribirme
                            </button>
                        </form>
                    </div>
                </div>
            </section>
        </main>
    );
}
