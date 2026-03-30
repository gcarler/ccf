"use client";

import Link from "next/link";
import React from "react";
import { useContentBlock } from "@/hooks/useContent";

export default function CursosPage() {
    const { data: heroContent } = useContentBlock("faro_courses_hero");
    const heroEyebrow = heroContent?.eyebrow || "Formación & Sabiduría";
    const heroTitleLead = heroContent?.title_lead || "El Camino";
    const heroAccent = heroContent?.title_accent || "del Faro";
    const heroDescription =
        heroContent?.description ||
        "Explora nuestra academia de cursos especializados y sumérgete en una selección literaria diseñada para iluminar tu entendimiento y profundizar tu fe.";

    return (
        <>
            <main className="pt-20 pb-32">
{/*  Hero Section: Editorial Style  */}
<section className="relative h-[614px] flex items-center px-8 md:px-20 overflow-hidden">
<div className="absolute inset-0 z-0">
<img className="w-full h-full object-cover opacity-40 grayscale-[0.5]" data-alt="Modern high-end library with soft natural light streaming through large windows, deep shadows, and a serene scholarly atmosphere" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDMdIOkuhnKUQoceljRNX0EA7oce7diAGmnD9LnD5MKHdQe-jaT3h-GHACgDsHa3iwUUaYk_wQ2vZA89r86x0Mvif59ZlN3idUMr_yWxAw3J3YcZMVr4jlndqqFOky-vllETfghJLABpCY10ytxBH3-RRTiiavUtvTYO4ZVPW6e6Pe8qW_vaO369mpL6fTY5n8emeWD134jeqMej1YlLqLKcS3wxQfC1L2dQGOPZxPwh66Wjrxj-B_YkvX4zkzoidHrVPj0-eJDWzYv"/>
<div className="absolute inset-0 bg-gradient-to-r from-faro-background via-faro-background/80 to-transparent"></div>
</div>
<div className="relative z-10 max-w-4xl">
<span className="label-md tracking-[0.2em] text-faro-primary uppercase font-bold mb-4 block">{heroEyebrow}</span>
<h1 className="text-6xl md:text-8xl font-headline font-extrabold text-faro-on-background tracking-tighter leading-none mb-6">
                    {heroTitleLead} <br/><span className="text-transparent bg-clip-text bg-gradient-to-r from-faro-primary to-faro-secondary">{heroAccent}.</span>
</h1>
<p className="text-xl text-faro-on-surface-variant max-w-xl leading-relaxed font-light">
                    {heroDescription}
                </p>
</div>
</section>
{/*  Courses Section (Cursos & Academia)  */}
<section className="px-8 md:px-20 mt-24">
<div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-8">
<div className="max-w-2xl">
<h2 className="text-4xl font-headline font-bold text-faro-on-surface mb-4">Cursos &amp; Academia</h2>
<p className="text-faro-on-surface-variant leading-relaxed">Programas académicos estructurados para líderes, estudiantes y buscadores de la verdad. Formación teológica y práctica con estándares de excelencia.</p>
</div>
<div className="flex gap-4">
<button className="px-6 py-2 rounded-[0.75rem] border border-faro-outline-variant text-faro-on-surface-variant hover:border-faro-primary hover:text-faro-primary transition-all text-sm font-medium">Ver todos</button>
</div>
</div>
{/*  Bento Grid for Courses  */}
<div className="grid grid-cols-1 md:grid-cols-12 gap-6">
{/*  Featured Course  */}
<div className="md:col-span-8 group relative rounded-[0.5rem] overflow-hidden bg-faro-surface-container-low transition-transform duration-500 hover:-translate-y-1">
<div className="aspect-video md:aspect-auto md:h-full relative">
<img className="w-full h-full object-cover opacity-60 group-hover:scale-105 transition-transform duration-700" data-alt="Young professionals in a bright modern classroom engaging in discussion, soft warm lighting, cinematic depth of field" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAFCyo5jdOom6vT_Jy4CUK2ZegzffrIWwEWDg4Ong9qvH18HQHVa3vou-ywQ8H3eMWC--E0ynzcU0PwVPul4R3V7bNGC2KI0R8E63AVRysjtP4_ExJNEn5B8wc1JrbzqKYLWliOd8BBgRdtgTIPWHpjCzKiAzKZLQMG1oNfs6XWLoYH201JfjnnbVQAbdR-bezXMamFL9_-KKMWJRTIV3tYQW9vPpzDtkZtGN484BR-pXF52ShqQUuxd2nnF5_xlB1N0CIk9dV_-yOz"/>
<div className="absolute inset-0 bg-gradient-to-t from-faro-surface-container-low via-transparent to-transparent"></div>
<div className="absolute bottom-0 p-8 w-full">
<span className="inline-block px-3 py-1 rounded-[0.75rem] bg-faro-primary/20 text-faro-primary text-xs font-bold uppercase tracking-widest mb-4">Certificación Master</span>
<h3 className="text-3xl font-headline font-bold text-faro-on-surface mb-2">Fundamentos de Teología Contemporánea</h3>
<p className="text-faro-on-surface-variant max-w-lg mb-6 line-clamp-2">Un recorrido profundo por las bases de la fe aplicadas al contexto social y cultural del siglo XXI.</p>
<div className="flex items-center gap-6">
<div className="flex items-center text-faro-primary">
<span className="material-symbols-outlined text-sm mr-2">schedule</span>
<span className="text-xs font-medium">12 Semanas</span>
</div>
<div className="flex items-center text-faro-primary">
<span className="material-symbols-outlined text-sm mr-2">person</span>
<span className="text-xs font-medium">Dr. Samuel Méndez</span>
</div>
<button className="ml-auto bg-gradient-to-br from-faro-primary to-faro-primary-container text-faro-on-primary px-8 py-3 rounded-[0.75rem] font-bold text-sm shadow-xl active:scale-95 transition-all">Inscribirse</button>
</div>
</div>
</div>
</div>
{/*  Secondary Course 1  */}
<div className="md:col-span-4 flex flex-col gap-6">
<div className="bg-faro-surface-container-high rounded-[0.5rem] p-8 flex-1 group hover:bg-faro-surface-bright transition-colors">
<span className="text-faro-secondary text-[10px] font-black uppercase tracking-widest mb-4 block">Taller Práctico</span>
<h4 className="text-xl font-headline font-bold text-faro-on-surface mb-3 group-hover:text-faro-primary transition-colors">Liderazgo Eclesial Efectivo</h4>
<p className="text-sm text-faro-on-surface-variant leading-relaxed mb-6">Herramientas de gestión y pastoreo para la nueva generación de líderes locales.</p>
<div className="flex justify-between items-center">
<span className="text-faro-primary font-bold">Inscripciones Abiertas</span>
<span className="material-symbols-outlined text-faro-primary group-hover:translate-x-2 transition-transform">arrow_forward</span>
</div>
</div>
<div className="bg-faro-surface-container-low border border-faro-outline-variant/20 rounded-[0.5rem] p-8 flex-1 group hover:border-faro-primary/50 transition-all">
<span className="text-faro-secondary text-[10px] font-black uppercase tracking-widest mb-4 block">Seminario Online</span>
<h4 className="text-xl font-headline font-bold text-faro-on-surface mb-3 group-hover:text-faro-primary transition-colors">Arqueología Bíblica Nivel I</h4>
<p className="text-sm text-faro-on-surface-variant leading-relaxed mb-6">Descubre los hallazgos que dan contexto histórico a las escrituras sagradas.</p>
<div className="flex justify-between items-center">
<span className="text-faro-on-surface-variant text-xs">Inicio: Octubre 15</span>
<span className="material-symbols-outlined text-faro-primary group-hover:translate-x-2 transition-transform">arrow_forward</span>
</div>
</div>
</div>
</div>
</section>
{/*  Books Section (Nuestra Librería)  */}
<section className="px-8 md:px-20 mt-32 py-24 bg-faro-surface-container-lowest/50 relative">
{/*  Background Decoration  */}
<div className="absolute top-0 right-0 w-1/3 h-full bg-gradient-to-l from-faro-primary/5 to-transparent"></div>
<div className="relative z-10">
<div className="max-w-xl mb-16">
<h2 className="text-4xl font-headline font-bold text-faro-on-surface mb-4">Nuestra Librería</h2>
<p className="text-faro-on-surface-variant">Una curaduría de obras que han transformado generaciones. Desde clásicos de la patrística hasta literatura contemporánea.</p>
</div>
{/*  Horizontal Scroll for Books  */}
<div className="flex gap-10 overflow-x-auto pb-12 no-scrollbar snap-x">
{/*  Book Item 1  */}
<div className="flex-none w-72 snap-start group">
<div className="relative aspect-[2/3] rounded-[0.25rem] mb-6 overflow-hidden shadow-2xl transition-transform duration-500 group-hover:-rotate-2 group-hover:scale-105">
<img className="w-full h-full object-cover" data-alt="Clean minimalist book cover design on a wooden desk, soft shadows, premium paper texture" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBd5Bmgs5WUQLFHf75g-DE3KdA_2lFIgeiRSOmuv0YUfVlxr4jetB8XfGygjOKT9WO9QdQx7khGcrqvlgFe92eFUqkiTMnVegOHV54Zgqi8wh3pWribxQE7II07JgE0lQ9bA4wMduH_fg1dK-3PWX0-Ef8H5h5wk8Sd2IxJaHnlkwgsGdC3xuLt5NRyyLniTkU3X87QZRCMA_rZRnVZRhi7htDDH_uCGbH0YjL2Mpe9pV10CZBexDrsd2t6tyM-mh3F6ucGBHghLLd0"/>
<div className="absolute inset-0 bg-black/20 group-hover:bg-transparent transition-colors"></div>
</div>
<h5 className="text-lg font-headline font-bold text-faro-on-surface mb-1">La Luz en la Tiniebla</h5>
<p className="text-xs text-faro-primary font-medium mb-3 uppercase tracking-tighter">Autor: Roberto V. Solis</p>
<p className="text-sm text-faro-on-surface-variant line-clamp-2 font-light leading-relaxed mb-4">Un ensayo profundo sobre la esperanza en tiempos de incertidumbre social y espiritual.</p>
<div className="flex items-center justify-between">
<span className="text-xl font-bold text-faro-on-surface">$24.90</span>
<button className="w-10 h-10 rounded-[0.75rem] bg-faro-surface-container-highest flex items-center justify-center text-faro-primary hover:bg-faro-primary hover:text-faro-on-primary transition-all">
<span className="material-symbols-outlined">shopping_bag</span>
</button>
</div>
</div>
{/*  Book Item 2  */}
<div className="flex-none w-72 snap-start group">
<div className="relative aspect-[2/3] rounded-[0.25rem] mb-6 overflow-hidden shadow-2xl transition-transform duration-500 group-hover:-rotate-2 group-hover:scale-105">
<img className="w-full h-full object-cover" data-alt="Stack of vintage leather bound books with gold lettering, warm ambient light, high contrast" src="https://lh3.googleusercontent.com/aida-public/AB6AXuApdinHi_W4_S4owziO_AqzjiDUsGRCxiu-FEiXlPx8p1EUorXaJYtypgFvaWtYzwGHdkJSb2R30VflRqi6dIcSF30VOe1bkgvxN3Qu-DP9XQyTMgpTg-ECDRtD--LAUZHxureBg7kgATxwR3eTMcz5FGK1t8KU-gxc2F09LLUqtPSf8px_TCIauD3lrvuX5qlwTDVWi6gfFBWPSsnC3g6bj-lITBAkCNg-Xva7BJt7qfDPVLH0y53ugIILTaj31-2z79va2Nr6xkAW"/>
<div className="absolute inset-0 bg-black/20 group-hover:bg-transparent transition-colors"></div>
</div>
<h5 className="text-lg font-headline font-bold text-faro-on-surface mb-1">Caminando con Gigantes</h5>
<p className="text-xs text-faro-primary font-medium mb-3 uppercase tracking-tighter">Autor: Elena de los Ríos</p>
<p className="text-sm text-faro-on-surface-variant line-clamp-2 font-light leading-relaxed mb-4">Biografías inspiradoras de hombres y mujeres que cambiaron el rumbo de la historia cristiana.</p>
<div className="flex items-center justify-between">
<span className="text-xl font-bold text-faro-on-surface">$19.50</span>
<button className="w-10 h-10 rounded-[0.75rem] bg-faro-surface-container-highest flex items-center justify-center text-faro-primary hover:bg-faro-primary hover:text-faro-on-primary transition-all">
<span className="material-symbols-outlined">shopping_bag</span>
</button>
</div>
</div>
{/*  Book Item 3  */}
<div className="flex-none w-72 snap-start group">
<div className="relative aspect-[2/3] rounded-[0.25rem] mb-6 overflow-hidden shadow-2xl transition-transform duration-500 group-hover:-rotate-2 group-hover:scale-105">
<img className="w-full h-full object-cover" data-alt="Modern book cover with geometric shapes and soft pastel colors, clean studio lighting" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBq0av-ZN7s4kZkrWYR_Ao7Ggat_dWoP89qvIFfqJY9Ddcq7i9sWGg7R5IiX8sTCInP2wKuT1fAOCcTfgDFE-s2jkkNh5CV-_Mz3xebE5yl4bnNz0fDJhGcKMsKvhe13o0LBs1crm8SuXVNBWeVFM0n9hhp2dsQgRHysRJ8OzU3fljVbdYAd3-d1ugcvPMglqV2e_l9Aqoyg51wCdYqtPENa2KyOiHh5ohXU8dpKDwcrR8TIuemxhJQpZkm3ymE2oG6rGChfebe30bi"/>
<div className="absolute inset-0 bg-black/20 group-hover:bg-transparent transition-colors"></div>
</div>
<h5 className="text-lg font-headline font-bold text-faro-on-surface mb-1">El Faro Interior</h5>
<p className="text-xs text-faro-primary font-medium mb-3 uppercase tracking-tighter">Autor: Manuel Farías</p>
<p className="text-sm text-faro-on-surface-variant line-clamp-2 font-light leading-relaxed mb-4">Manual de devoción diaria enfocado en la paz mental y el crecimiento espiritual sólido.</p>
<div className="flex items-center justify-between">
<span className="text-xl font-bold text-faro-on-surface">$22.00</span>
<button className="w-10 h-10 rounded-[0.75rem] bg-faro-surface-container-highest flex items-center justify-center text-faro-primary hover:bg-faro-primary hover:text-faro-on-primary transition-all">
<span className="material-symbols-outlined">shopping_bag</span>
</button>
</div>
</div>
{/*  Book Item 4  */}
<div className="flex-none w-72 snap-start group">
<div className="relative aspect-[2/3] rounded-[0.25rem] mb-6 overflow-hidden shadow-2xl transition-transform duration-500 group-hover:-rotate-2 group-hover:scale-105">
<img className="w-full h-full object-cover" data-alt="Hardcover book lying open on white linen, bright morning sunlight creating long shadows" src="https://lh3.googleusercontent.com/aida-public/AB6AXuC6Wrh1QjyZPPD38wTpMBCBrxQfqhST2BJl1-GKp6JOQk7LfRiBrfZBe2Xn-xVjtaSx98cRGEgg4J9CUVbDrrko9TZaHc9DbC-372KBdO3V0cnLRy1YmNA11YSZW9L5jIEY70KPiaXK5cUCcxGu7kPaTZjXVhoG6BiPgAN_ECO-5R4TyFYTb0qQA-YlxbNk0nGuvTG9oyZTh7a_6v2-1ZQ1UEya5Bd8nuy2Co7SsGm7GUvRaWCCHVi2pj3UU1bK2DRq7aCFHeRN8hZ7"/>
<div className="absolute inset-0 bg-black/20 group-hover:bg-transparent transition-colors"></div>
</div>
<h5 className="text-lg font-headline font-bold text-faro-on-surface mb-1">Mente &amp; Espíritu</h5>
<p className="text-xs text-faro-primary font-medium mb-3 uppercase tracking-tighter">Autor: Varios Autores</p>
<p className="text-sm text-faro-on-surface-variant line-clamp-2 font-light leading-relaxed mb-4">Compendio de artículos sobre la intersección entre la psicología moderna y la fe.</p>
<div className="flex items-center justify-between">
<span className="text-xl font-bold text-faro-on-surface">$31.00</span>
<button className="w-10 h-10 rounded-[0.75rem] bg-faro-surface-container-highest flex items-center justify-center text-faro-primary hover:bg-faro-primary hover:text-faro-on-primary transition-all">
<span className="material-symbols-outlined">shopping_bag</span>
</button>
</div>
</div>
</div>
</div>
</section>
{/*  Newsletter / Community Section  */}
<section className="px-8 md:px-20 mt-32">
<div className="bg-gradient-to-br from-faro-surface-container-high to-faro-surface-container-lowest rounded-3xl p-12 md:p-20 relative overflow-hidden border border-faro-outline-variant/10">
<div className="absolute top-0 right-0 w-64 h-64 bg-faro-primary/10 blur-[100px] rounded-[0.75rem] -mr-20 -mt-20"></div>
<div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-16 items-center">
<div>
<h2 className="text-4xl md:text-5xl font-headline font-bold text-faro-on-surface mb-6">Únete a la Academia FARO</h2>
<p className="text-faro-on-surface-variant text-lg leading-relaxed mb-8">Recibe actualizaciones sobre nuevos cursos, lanzamientos de libros y eventos exclusivos de formación directamente en tu correo.</p>
<form className="flex flex-col sm:flex-row gap-4">
<input className="flex-1 bg-faro-surface-container-highest border-none rounded-[0.75rem] px-8 py-4 text-faro-on-surface focus:ring-2 focus:ring-faro-primary transition-all" placeholder="Tu correo electrónico" type="email"/>
<button className="bg-faro-primary text-faro-on-primary px-10 py-4 rounded-[0.75rem] font-bold shadow-lg shadow-faro-primary/20 hover:scale-105 active:scale-95 transition-all">Suscribirme</button>
</form>
</div>
<div className="hidden md:block">
<div className="grid grid-cols-2 gap-4">
<div className="aspect-square rounded-2xl overflow-hidden bg-faro-surface">
<img className="w-full h-full object-cover opacity-80" data-alt="Person writing in a notebook next to a cup of coffee and a laptop, morning light, organized desk" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCoudBEr_fb-1TVhJXdMXejKSJoQgi3QkKVJmmzXpvg2-hr3UZPrDJbmRSLhsuVRoH7QqA5QcEQri5azGnRQJh_PUxiQ79h7vJh0AU70iy6o4vH5AiujrmQ9MzbmU8-hH5JMRc5_mBEw6IQGGNdgtRqE_amOwPBRoUwDnvmnFczlymtB38TXJo7i3ZNMR3tL6HCur_pn63ye4AYBa1R1L6NHbMD05X8-eirIAtgMpk-A45A83UmsZW5Udnh18JOBUrRtnRhA1xRZO9x"/>
</div>
<div className="aspect-square rounded-2xl overflow-hidden bg-faro-surface mt-8">
<img className="w-full h-full object-cover opacity-80" data-alt="Detailed view of a bookshelf with diverse collection of books, shallow depth of field, warm lighting" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAfn5A17sWbZkxOXXrRf09GglIzya0wmq4RyPgsAQuQV6GGbDBbv4IrTMBv8vmSnq_98xtwTWiCpu-Ld0-ZuAg5KLYhulI9vccAtOaFcQySpwIxv3n_B-ag7FG-58p-y1hhz5s9kK8mgbp9L1Qa4T8ZcBeoDL8vyyf9aHx2xEiHiK4E_msDgoI9o-L-EZxRU4PGAwAx4UDBdWLBKyAHKAJnC25F4hXfWs-nCOrZTejPXEgFGx706FxsVW4um46gAYPhN4JIfL45hwBD"/>
</div>
</div>
</div>
</div>
</div>
</section>
</main>
        </>
    );
}
