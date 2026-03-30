"use client";

import Link from "next/link";
import React from "react";
import { useContentBlock } from "@/hooks/useContent";

export default function TestimoniosPage() {
    const { data: heroContent } = useContentBlock("faro_testimonios_hero");
    const heroEyebrow = heroContent?.eyebrow || "Impacto Real";
    const heroTitleLead = heroContent?.title_lead || "Historias de";
    const heroAccent = heroContent?.title_accent || "Transformación";
    const heroDescription =
        heroContent?.description ||
        "Descubre cómo la fe y la comunidad han iluminado el camino de personas reales en nuestra comunidad FARO. No son solo palabras, son vidas cambiadas.";

    return (
        <>
            <aside className="hidden lg:flex flex-col h-full w-80 fixed left-0 top-0 z-[60] bg-[#001134] py-8 px-4 font-manrope tracking-tight bg-faro-surface-container-low on surface">
<div className="mb-12 px-4">
<h2 className="text-xl font-black text-[#a5c8ff] mb-1">FARO</h2>
<p className="text-[10px] uppercase tracking-[0.2em] text-[#d9e2ff]/40">Comunidad FARO</p>
</div>
<nav className="space-y-1">
<a className="flex items-center space-x-4 px-4 py-3 text-[#a5c8ff] bg-[#004581]/20 font-bold rounded-[0.5rem] transition-all" href="#">
<span className="material-symbols-outlined">format_quote</span>
<span>Testimonios</span>
</a>
<a className="flex items-center space-x-4 px-4 py-3 text-[#d9e2ff]/60 hover:bg-[#004581]/10 hover:text-[#a5c8ff] transition-all rounded-[0.5rem]" href="#">
<span className="material-symbols-outlined">auto_awesome</span>
<span>Conocer a Jesús</span>
</a>
<a className="flex items-center space-x-4 px-4 py-3 text-[#d9e2ff]/60 hover:bg-[#004581]/10 hover:text-[#a5c8ff] transition-all rounded-[0.5rem]" href="#">
<span className="material-symbols-outlined">info</span>
<span>Sobre Nosotros</span>
</a>
<a className="flex items-center space-x-4 px-4 py-3 text-[#d9e2ff]/60 hover:bg-[#004581]/10 hover:text-[#a5c8ff] transition-all rounded-[0.5rem]" href="#">
<span className="material-symbols-outlined">menu_book</span>
<span>Libros</span>
</a>
<a className="flex items-center space-x-4 px-4 py-3 text-[#d9e2ff]/60 hover:bg-[#004581]/10 hover:text-[#a5c8ff] transition-all rounded-[0.5rem]" href="#">
<span className="material-symbols-outlined">schedule</span>
<span>Horarios</span>
</a>
<a className="flex items-center space-x-4 px-4 py-3 text-[#d9e2ff]/60 hover:bg-[#004581]/10 hover:text-[#a5c8ff] transition-all rounded-[0.5rem]" href="#">
<span className="material-symbols-outlined">mail</span>
<span>Contacto</span>
</a>
</nav>
<div className="mt-auto p-4 flex items-center space-x-3 bg-faro-surface-container-high/30 rounded-2xl">
<div className="w-10 h-10 rounded-[0.75rem] bg-faro-primary-container flex items-center justify-center overflow-hidden">
<img alt="Avatar" data-alt="close-up portrait of a serene man with a gentle smile in soft cinematic lighting with dark blue background" src="https://lh3.googleusercontent.com/aida-public/AB6AXuB8BwzXrERmImvAANYz6YNZKExCpcEM9yppvqoK34tg8zZYyepKHqw1Tjcx48l6GkQWn-vxubGhu20mjLKOIEEJJ2AFwxT36mClfAny7QWx_fsyL_EqIf-S6uUYTX2KS1Lv7M1gyFr1CbAjrjMVFIRXjic-16NPcMLyAd6VQPSye7qzYnl2h4QpIbKm1xErWY_BO5wLMehPwA27A8Bu97Ouxjcf43J4DJi84rq_Ip2me20FlqcS0WkqexRN3HiZuOy8vVaFGxtRN38p"/>
</div>
<div>
<p className="text-sm font-bold text-faro-on-surface">The Radiant Guide</p>
<p className="text-xs text-faro-on-surface-variant">Admin</p>
</div>
</div>
</aside><main className="lg:pl-80 pt-20 pb-32">
{/*  Hero Section  */}
<header className="relative px-8 py-20 overflow-hidden">
{/*  Light Leak Effect  */}
<div className="absolute top-0 right-0 w-[600px] h-[600px] bg-faro-secondary/10 rounded-[0.75rem] blur-[120px] -translate-y-1/2 translate-x-1/3"></div>
<div className="relative z-10 max-w-5xl mx-auto">
<span className="label-md font-label tracking-[0.2em] text-faro-primary uppercase mb-4 block">{heroEyebrow}</span>
<h1 className="text-display-lg font-headline font-extrabold text-7xl leading-tight tracking-tight mb-8 text-glow max-w-3xl">
                    {heroTitleLead} <span className="text-faro-primary italic">{heroAccent}</span>
</h1>
<p className="text-body-lg text-faro-on-surface-variant leading-relaxed max-w-xl text-lg opacity-80">
                    {heroDescription}
                </p>
</div>
</header>
{/*  Bento Grid Testimonials  */}
<section className="px-8 max-w-7xl mx-auto space-y-12">
<div className="grid grid-cols-1 md:grid-cols-12 gap-6">
{/*  Main Featured Card (Large)  */}
<div className="md:col-span-8 bg-faro-surface-container-low rounded-[0.5rem] overflow-hidden relative group">
<div className="absolute inset-0 bg-gradient-to-t from-faro-background via-transparent to-transparent z-10"></div>
<img alt="Transformation Story" className="w-full h-[500px] object-cover group-hover:scale-105 transition-transform duration-700" data-alt="thoughtful young woman looking out a window as sunlight hits her face with warm cinematic glows and deep shadows" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAneccvEkytbIrAv54dHKXzGFgqpPwEnpCL_MR2bmHcnOxCLrxy7ANAraeKh690egsums2WT8T1tjLIsNn1ERHMUmxldM78zh55OIEKF9r4qixqTPgTZMWTULu1gS2jctKaRMwAYhpULI8_MZ85ywKkJnEPEOqaR8Gj1vn-q0u50MsBWJzo6-htLQE_iF0qaN3r2hCVy17rdCXPAuwUH4PKLHgeJPnUpkI7B_75a-RWYiLAHmLzm55ctfiIuxfUjwhhroIDpceFUDWd"/>
<div className="absolute bottom-0 left-0 p-10 z-20">
<span className="material-symbols-outlined text-faro-primary text-5xl mb-4 block" style={{ fontVariationSettings: "'FILL' 1" }}>format_quote</span>
<h3 className="font-headline text-3xl font-bold text-faro-on-surface mb-6 leading-tight">&quot;Encontré un propósito que nunca imaginé posible.&quot;</h3>
<div className="flex items-center space-x-4">
<div className="w-12 h-12 rounded-[0.75rem] border-2 border-faro-primary overflow-hidden">
<img alt="Elena" data-alt="portrait of a smiling woman with curly hair and soft natural lighting against a dark background" src="https://lh3.googleusercontent.com/aida-public/AB6AXuD125FWVIbleriyEIlF10IpLXHuQnOKLAobMi_PoM7uTjz6Rk-PnveseytiCd4vVCXsSmTWWQ9IvOnbSdzPPQuHozU6HK3-0uYmFz72K9Gs2axY_fptjvAFCPQQyDuvZ2Ey-5gqOnxzNbmFMHEHXc5ANBk6k_CJA19g16geXC-AL-4qpczjzLvMNrD98IJ42QRhgCdsL6ps_zl1FhL9zV5ILHDEptaEsqiThu7W96VPBcpPJiBHlkj7K71fjBfSr17hHoY4crzf3GNd"/>
</div>
<div>
<p className="font-bold">Elena Martínez</p>
<p className="text-sm text-faro-on-surface-variant">Sede Norte</p>
</div>
</div>
</div>
</div>
{/*  Video Testimonial Preview  */}
<div className="md:col-span-4 bg-faro-surface-container-high rounded-[0.5rem] p-8 flex flex-col justify-between relative overflow-hidden">
<div className="absolute top-0 right-0 w-32 h-32 bg-faro-primary/5 rounded-[0.75rem] blur-3xl"></div>
<div>
<div className="w-12 h-12 beam-gradient rounded-[0.75rem] flex items-center justify-center mb-8 shadow-[0_0_20px_rgba(165,200,255,0.3)]">
<span className="material-symbols-outlined text-faro-on-primary" style={{ fontVariationSettings: "'FILL' 1" }}>play_arrow</span>
</div>
<h4 className="font-headline text-xl font-bold mb-4">Testimonio en Video</h4>
<p className="text-faro-on-surface-variant text-sm leading-relaxed">Mira la historia de Lucas y su camino hacia la recuperación a través del grupo de apoyo FARO.</p>
</div>
<div className="mt-8 rounded-[0.25rem] overflow-hidden relative">
<img alt="Lucas" data-alt="man in silhouette standing against a bright city light backdrop at night symbolizing hope and clarity" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBzga-EYmiRDmBuVXaeOjqJC8hr_iVZc82tuiuea_aNxMhLGdUyHk6hB4PbX_NZNxT1zI60zoTr5W2niSx0Hoo6f21A7ueS5L3Btr2zG9hGRAWY3g4QxXNUG_R5GRIV0XEJYFtJQSQBIFvbs0L-c_1UxS0ClWINeaFhzt-4R0abjCghezAdwJCm0ufy3MUII4yHs29rP7xngRbkaDdVxzWsOMjKNHyz_aHZVtnmhzg7XgDO8kUTV5ZPlJEySjt8KKZkFO2AyuQqd1DR"/>
<div className="absolute inset-0 flex items-center justify-center bg-black/30">
<span className="text-xs uppercase tracking-widest text-white font-bold">Reproducir</span>
</div>
</div>
</div>
{/*  Quote Only Card  */}
<div className="md:col-span-4 bg-faro-surface-container-low rounded-[0.5rem] p-8 border-l-4 border-faro-primary">
<p className="text-lg italic text-faro-on-surface-variant mb-8 leading-relaxed">
                        &quot;Llegué a FARO buscando respuestas y encontré una familia. El curso de Liderazgo cambió mi forma de ver el trabajo y mis relaciones personales.&quot;
                    </p>
<div className="flex items-center space-x-3">
<div className="w-10 h-10 rounded-[0.75rem] bg-faro-surface-container-highest"></div>
<div>
<p className="text-sm font-bold">Roberto S.</p>
<p className="text-[10px] text-faro-primary uppercase tracking-widest">Egresado Curso 2023</p>
</div>
</div>
</div>
{/*  Image Focused Card  */}
<div className="md:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-6">
<div className="bg-faro-surface-container-high rounded-[0.5rem] overflow-hidden group">
<img alt="Comunidad" className="w-full h-48 object-cover opacity-60 group-hover:opacity-100 transition-opacity" data-alt="group of diverse young adults laughing together in a modern urban indoor setting with soft overhead lighting" src="https://lh3.googleusercontent.com/aida-public/AB6AXuC6Qbo5sesqr5E8g7OciNicDzknAtNikQUo4skmiqXe0DtycWNiW_yJ4p5pmbCUqBvt54B0RLyYLaECTHlLWsk7SNMi1ChGzDDFhbuVukdwOxCpFov-y2Ui2UjCodERM2fQPd77dNgdkuCEBn_ZKVM6g7SGjcIfM8tx3L1cfMQ14Ee1TeMzi9okWpqJkdkf0dcMKDAChJQtbilKvhqXfEjzLxTgnlmMujCaA0WzafT6ecq2qVjX-nR4hf_InVzSKyRaaa5STihT7EfA"/>
<div className="p-6">
<h4 className="font-bold mb-2">Comunidad en Acción</h4>
<p className="text-xs text-faro-on-surface-variant">Historias de voluntariado que impactan la ciudad cada semana.</p>
</div>
</div>
<div className="bg-faro-surface-container-high rounded-[0.5rem] p-6 flex flex-col justify-center text-center">
<div className="text-4xl font-black text-faro-primary mb-2">+500</div>
<p className="label-md uppercase tracking-tighter text-faro-on-surface-variant">Vidas impactadas este mes</p>
<hr className="my-6 border-faro-outline-variant/20"/>
<button className="text-faro-primary font-bold text-sm hover:underline">Sube tu testimonio <span className="material-symbols-outlined align-middle text-sm">arrow_forward</span></button>
</div>
</div>
</div>
</section>
{/*  Featured Quote Section (Editorial Style)  */}
<section className="mt-32 px-8 py-24 bg-faro-surface-container-lowest relative overflow-hidden">
<div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-faro-primary/30 to-transparent"></div>
<div className="max-w-4xl mx-auto text-center relative z-10">
<span className="material-symbols-outlined text-6xl text-faro-primary/20 mb-8 block">format_quote</span>
<blockquote className="text-headline font-headline text-4xl font-bold leading-tight mb-12 text-faro-on-surface italic">
                    &quot;La luz que encontramos en FARO no es para guardarla, es para guiar a otros que aún caminan en la oscuridad.&quot;
                </blockquote>
<div className="flex flex-col items-center">
<p className="font-bold text-xl">Pastor David Vance</p>
<p className="text-faro-primary tracking-widest uppercase text-xs mt-2">Visión 2024</p>
</div>
</div>
</section>
</main>
        </>
    );
}
