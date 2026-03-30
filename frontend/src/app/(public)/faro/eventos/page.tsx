"use client";

import Link from "next/link";
import React from "react";
import { useContentBlock } from "@/hooks/useContent";
import { FARO_EVENTS_BLOCK_KEY } from "@/lib/cms/blocks";

interface PublicEventItem {
    title?: string;
    date?: string;
    location?: string;
    excerpt?: string;
    category?: string;
    featured?: boolean;
}

export default function EventosPage() {
    const { data: heroContent } = useContentBlock("faro_events_hero");
    const { data: eventsContent } = useContentBlock(FARO_EVENTS_BLOCK_KEY);
    const heroEyebrow = heroContent?.eyebrow || "Calendario de Comunidad";
    const heroTitle = heroContent?.title || "Nuestra Agenda";
    const heroDescription =
        heroContent?.description ||
        "Espacios diseñados para el crecimiento, la conexión y la guía espiritual. Únete a nuestras próximas actividades.";
    const parsedEvents = Array.isArray(eventsContent?.parsed) ? (eventsContent?.parsed as PublicEventItem[]) : [];
    const featuredEvent =
        parsedEvents.find((event) => event.featured) ||
        parsedEvents[0] || {
            date: "24 DE JUNIO, 2024",
            title: "Noche de Iluminación: Adoración & Palabra",
            location: "Auditorio Central"
        };
    const upcomingEvent =
        parsedEvents[1] || {
            date: "12",
            title: "Cena de Jóvenes",
            location: "Sede Norte • 19:30 hrs"
        };

    return (
        <>
            <main className="pt-32 pb-20 px-6 md:px-12 max-w-7xl mx-auto">
<header className="mb-16 md:grid md:grid-cols-12 gap-8 items-end">
<div className="md:col-span-8">
<span className="font-label text-xs tracking-[0.2em] uppercase text-faro-secondary mb-4 block">{heroEyebrow}</span>
<h1 className="font-headline text-5xl md:text-7xl font-extrabold tracking-tighter text-faro-on-surface leading-tight">{heroTitle}</h1>
</div>
<div className="md:col-span-4 mt-6 md:mt-0">
<p className="text-faro-on-surface-variant leading-relaxed opacity-80">
                    {heroDescription}
                </p>
</div>
</header>
<section className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-20">
<div className="md:col-span-2 relative h-[500px] rounded-[0.5rem] overflow-hidden group">
<img alt="Gran Evento Destacado" className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" data-alt="Modern worship event with bright stage lights, atmospheric blue haze, and a crowd of people in silhouette against a radiant background" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDlfe5nWlCY5n15IXPMDiT038q3Ub-A4sNfRFYcKcqqPor7XME2XkgXXK-Nd82oa3q3jNisTCpWTG5egEcodKp1GJ72Gd6TAuiWsIDpmw6FK8GS1rWDQbFamacLIxNqaT2-cEC_6PKmuFHXViCY1nJyIc_B8J08Rwbuuv4l6ZalNUlf4ja69TfZ_s2h0DXoG7t5KrnibidyhZgV48ahvkcKjoowTbYX52yeedKmgVHn-tPKkqteabjfC8prCR2GHeS8y_3SyHoG0_bi"/>
<div className="absolute inset-0 bg-gradient-to-t from-faro-background via-faro-background/40 to-transparent"></div>
<div className="absolute bottom-0 p-10 w-full">
<div className="flex items-center gap-2 mb-4">
<span className="bg-faro-primary-container text-faro-primary px-3 py-1 rounded-[0.75rem] text-[10px] font-bold tracking-widest uppercase">Destacado</span>
<span className="text-faro-on-surface/60 text-xs font-label">{featuredEvent.date}</span>
</div>
<h2 className="font-headline text-4xl font-bold mb-4 text-glow">{featuredEvent.title}</h2>
<div className="flex items-center gap-6">
<button className="beam-effect text-faro-on-primary px-8 py-3 rounded-[0.75rem] font-bold text-sm tracking-wide transition-transform active:scale-95">RESERVAR LUGAR</button>
<span className="flex items-center gap-2 text-faro-primary font-medium">
<span className="material-symbols-outlined text-lg">location_on</span> {featuredEvent.location}
                        </span>
</div>
</div>
</div>
<div className="bg-faro-surface-container-low rounded-[0.5rem] p-8 flex flex-col justify-between">
<div>
<h3 className="font-headline text-2xl font-bold mb-6">Filtros de Búsqueda</h3>
<div className="space-y-4">
<div className="bg-faro-surface-container-highest p-4 rounded-[0.5rem] flex items-center justify-between group cursor-pointer hover:bg-faro-surface-bright transition-colors border border-transparent hover:border-faro-primary/20">
<span className="text-sm font-medium">Todos los Eventos</span>
<span className="material-symbols-outlined text-faro-primary">arrow_forward_ios</span>
</div>
<div className="bg-faro-surface-container-highest p-4 rounded-[0.5rem] flex items-center justify-between group cursor-pointer hover:bg-faro-surface-bright transition-colors border border-transparent hover:border-faro-primary/20">
<span className="text-sm font-medium">Conferencias</span>
<span className="material-symbols-outlined text-faro-on-surface/40">arrow_forward_ios</span>
</div>
<div className="bg-faro-surface-container-highest p-4 rounded-[0.5rem] flex items-center justify-between group cursor-pointer hover:bg-faro-surface-bright transition-colors border border-transparent hover:border-faro-primary/20">
<span className="text-sm font-medium">Grupos de Conexión</span>
<span className="material-symbols-outlined text-faro-on-surface/40">arrow_forward_ios</span>
</div>
<div className="bg-faro-surface-container-highest p-4 rounded-[0.5rem] flex items-center justify-between group cursor-pointer hover:bg-faro-surface-bright transition-colors border border-transparent hover:border-faro-primary/20">
<span className="text-sm font-medium">Cursos &amp; Talleres</span>
<span className="material-symbols-outlined text-faro-on-surface/40">arrow_forward_ios</span>
</div>
</div>
</div>
<div className="mt-8 pt-8 border-t border-faro-outline-variant/20">
<p className="text-xs text-faro-on-surface-variant uppercase tracking-widest mb-4">Próximo en 48 horas</p>
<div className="flex items-center gap-4">
<div className="w-12 h-12 bg-faro-primary/10 rounded-[0.75rem] flex items-center justify-center text-faro-primary font-bold">{upcomingEvent.date}</div>
<div>
<p className="text-sm font-bold">{upcomingEvent.title}</p>
<p className="text-xs text-faro-on-surface/60 italic">{upcomingEvent.location}</p>
</div>
</div>
</div>
</div>
</section>
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10 mb-20">
<article className="bg-faro-surface-container-low rounded-[0.5rem] overflow-hidden group hover:bg-faro-surface-container-high transition-all duration-300">
<div className="h-56 relative overflow-hidden">
<img alt="Evento de Jóvenes" className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" data-alt="Large contemporary indoor auditorium with blue theatrical lighting and empty seats before a major community event" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAlpHff3VgpF_WKWF2016_knUqMnVjEZbGVOE-KRCRIlLk4lfKp3tIHxjIYIZ37Wxu_Kwopc146QgNXA6EFqF89Q-__L_Ced7nnh7L5OwtW8DeehJ_M7cFRvZ7GHGCQXfemL2Ro0wCujsI9BQ0ccZrhuqK3Hg_FZLUKMaJabek5Ch-ELzdbIL8E0-ebJp4Wpk3o_hUfZtH6QgEetuxMBegJ6ixmd4Pte32bvJ6LdckubiLDjab8TBZYFtEJnoE7AWeC6s0mTau8S6eS"/>
<div className="absolute top-4 right-4 bg-faro-background/80 backdrop-blur-md p-3 rounded-[0.5rem] text-center min-w-[60px]">
<p className="text-xs font-label uppercase tracking-tighter">JUL</p>
<p className="text-xl font-bold text-faro-primary">05</p>
</div>
</div>
<div className="p-8">
<span className="font-label text-[10px] tracking-[0.15em] uppercase text-faro-secondary font-semibold mb-2 block">Conferencia</span>
<h4 className="font-headline text-xl font-bold mb-4 group-hover:text-faro-primary transition-colors">Liderazgo Radiante</h4>
<p className="text-sm text-faro-on-surface-variant mb-6 line-clamp-2">Descubre las herramientas para guiar con propósito en un mundo en constante cambio.</p>
<div className="flex items-center justify-between">
<div className="flex -space-x-3">
<div className="w-8 h-8 rounded-[0.75rem] border-2 border-faro-surface bg-faro-surface-container-highest flex items-center justify-center text-[10px]">+12</div>
<div className="w-8 h-8 rounded-[0.75rem] border-2 border-faro-surface bg-faro-surface-container-highest"></div>
<div className="w-8 h-8 rounded-[0.75rem] border-2 border-faro-surface bg-faro-surface-container-highest"></div>
</div>
<button className="text-faro-primary text-sm font-bold flex items-center gap-1 group/btn">
                            VER MÁS <span className="material-symbols-outlined text-sm group-hover/btn:translate-x-1 transition-transform">arrow_forward</span>
</button>
</div>
</div>
</article>
<article className="bg-faro-surface-container-low rounded-[0.5rem] overflow-hidden group hover:bg-faro-surface-container-high transition-all duration-300">
<div className="h-56 relative overflow-hidden">
<img alt="Evento Musical" className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" data-alt="Close up of a guitarist on stage under soft blue and purple lighting, atmospheric and intimate concert setting" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBW9z4SKaWBOdvIrWPAqBcSItdN-u6Wz_qRTcj7ELe_DrXAIjnd3ADxIccD3ijx0XnVmcf63O54WsljxF6QqIYhpT4BN1f3YNodKh7VI5I6KRj0xt4lgv3tBiXMWA5bV9r7sOuKSFBPGf-O-z-S-PH1bgFDKoiZJ5ve4Pl3pLSXodd9gMoDeDQxFBoX6uWCacA4knZd9T8MFqwu8UB_6JzMpbi09di76aHNAO68FQ1hQv3VB5I2374yhqqtKtYJ1ofF8sBq5adY4HwX"/>
<div className="absolute top-4 right-4 bg-faro-background/80 backdrop-blur-md p-3 rounded-[0.5rem] text-center min-w-[60px]">
<p className="text-xs font-label uppercase tracking-tighter">JUL</p>
<p className="text-xl font-bold text-faro-primary">12</p>
</div>
</div>
<div className="p-8">
<span className="font-label text-[10px] tracking-[0.15em] uppercase text-faro-secondary font-semibold mb-2 block">Música</span>
<h4 className="font-headline text-xl font-bold mb-4 group-hover:text-faro-primary transition-colors">Festival FARO Sound</h4>
<p className="text-sm text-faro-on-surface-variant mb-6 line-clamp-2">Una tarde de música en vivo, arte y comunidad al aire libre en nuestra Sede Jardín.</p>
<div className="flex items-center justify-between">
<div className="flex -space-x-3">
<div className="w-8 h-8 rounded-[0.75rem] border-2 border-faro-surface bg-faro-surface-container-highest flex items-center justify-center text-[10px]">+45</div>
<div className="w-8 h-8 rounded-[0.75rem] border-2 border-faro-surface bg-faro-surface-container-highest"></div>
<div className="w-8 h-8 rounded-[0.75rem] border-2 border-faro-surface bg-faro-surface-container-highest"></div>
</div>
<button className="text-faro-primary text-sm font-bold flex items-center gap-1 group/btn">
                            VER MÁS <span className="material-symbols-outlined text-sm group-hover/btn:translate-x-1 transition-transform">arrow_forward</span>
</button>
</div>
</div>
</article>
<article className="bg-faro-surface-container-low rounded-[0.5rem] overflow-hidden group hover:bg-faro-surface-container-high transition-all duration-300">
<div className="h-56 relative overflow-hidden">
<img alt="Taller de Biblia" className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" data-alt="Open bible on a rustic wooden table with a soft candle glowing nearby, warm and peaceful study atmosphere" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDXGvzLetQpzZDwpJJfznGypLa6O6s41nfCR0WT4EQXcgxXHOChzcbijVVNgc3s2-jslZV581kELaQVH6CsXPfFN96aCMjONQGb_sTIdljH_GpQTcarfoagQaBTqCGm2G1ERp5tZHeWclYzfGuUGIJwRcC1ryur7sAZHC7w6om6cZCsmWu34hgUE9md2ryUTF6yYQpQctPffBjxV8AAHgrSq5OT_bLihUo3M0dvdBeKHi32rS0nCSMwzx1V-6GzsBwUi2n51HD3rYO2"/>
<div className="absolute top-4 right-4 bg-faro-background/80 backdrop-blur-md p-3 rounded-[0.5rem] text-center min-w-[60px]">
<p className="text-xs font-label uppercase tracking-tighter">AGO</p>
<p className="text-xl font-bold text-faro-primary">02</p>
</div>
</div>
<div className="p-8">
<span className="font-label text-[10px] tracking-[0.15em] uppercase text-faro-secondary font-semibold mb-2 block">Estudio</span>
<h4 className="font-headline text-xl font-bold mb-4 group-hover:text-faro-primary transition-colors">Profundidad Teológica</h4>
<p className="text-sm text-faro-on-surface-variant mb-6 line-clamp-2">Taller intensivo sobre los Salmos y su aplicación en la vida moderna.</p>
<div className="flex items-center justify-between">
<div className="flex -space-x-3">
<div className="w-8 h-8 rounded-[0.75rem] border-2 border-faro-surface bg-faro-surface-container-highest flex items-center justify-center text-[10px]">+8</div>
<div className="w-8 h-8 rounded-[0.75rem] border-2 border-faro-surface bg-faro-surface-container-highest"></div>
<div className="w-8 h-8 rounded-[0.75rem] border-2 border-faro-surface bg-faro-surface-container-highest"></div>
</div>
<button className="text-faro-primary text-sm font-bold flex items-center gap-1 group/btn">
                            VER MÁS <span className="material-symbols-outlined text-sm group-hover/btn:translate-x-1 transition-transform">arrow_forward</span>
</button>
</div>
</div>
</article>
</div>
{/*  Interactive Event Calendar Section  */}
<section className="mb-32">
<div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
<div>
<h2 className="font-headline text-3xl font-extrabold tracking-tight text-faro-on-surface">Explora nuestro Calendario</h2>
<p className="text-faro-on-surface-variant text-sm mt-1">Organiza tu tiempo con nuestras actividades comunitarias.</p>
</div>
<div className="inline-flex bg-faro-surface-container-high p-1 rounded-[0.75rem] shadow-inner">
<button className="px-6 py-2 rounded-[0.75rem] text-xs font-bold tracking-widest uppercase transition-all duration-300 hover:text-faro-primary">Semanal</button>
<button className="px-6 py-2 rounded-[0.75rem] text-xs font-bold tracking-widest uppercase bg-faro-primary text-faro-on-primary shadow-lg transition-all duration-300">Mensual</button>
<button className="px-6 py-2 rounded-[0.75rem] text-xs font-bold tracking-widest uppercase transition-all duration-300 hover:text-faro-primary">Anual</button>
</div>
</div>
<div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
{/*  Main Calendar UI  */}
<div className="lg:col-span-8 bg-faro-surface-container-low rounded-2xl p-6 md:p-10 shadow-xl border border-faro-outline-variant/10">
<div className="flex items-center justify-between mb-8">
<div className="flex items-center gap-4">
<h3 className="font-headline text-2xl font-bold">Junio 2024</h3>
<div className="flex gap-1">
<button className="p-2 hover:bg-faro-surface-container-highest rounded-[0.75rem] transition-colors">
<span className="material-symbols-outlined text-xl">chevron_left</span>
</button>
<button className="p-2 hover:bg-faro-surface-container-highest rounded-[0.75rem] transition-colors">
<span className="material-symbols-outlined text-xl">chevron_right</span>
</button>
</div>
</div>
<button className="text-faro-primary text-xs font-bold tracking-widest uppercase flex items-center gap-1">HOY</button>
</div>
<div className="calendar-grid gap-1 mb-2">
<div className="text-center py-2 text-[10px] font-bold text-faro-on-surface-variant uppercase tracking-widest">Dom</div>
<div className="text-center py-2 text-[10px] font-bold text-faro-on-surface-variant uppercase tracking-widest">Lun</div>
<div className="text-center py-2 text-[10px] font-bold text-faro-on-surface-variant uppercase tracking-widest">Mar</div>
<div className="text-center py-2 text-[10px] font-bold text-faro-on-surface-variant uppercase tracking-widest">Mié</div>
<div className="text-center py-2 text-[10px] font-bold text-faro-on-surface-variant uppercase tracking-widest">Jue</div>
<div className="text-center py-2 text-[10px] font-bold text-faro-on-surface-variant uppercase tracking-widest">Vie</div>
<div className="text-center py-2 text-[10px] font-bold text-faro-on-surface-variant uppercase tracking-widest">Sáb</div>
</div>
<div className="calendar-grid gap-1">
{/*  Row 1  */}
<div className="aspect-square p-2 bg-faro-surface-container-highest/20 rounded-[0.25rem] flex items-start justify-center text-faro-on-surface-variant/30 text-sm">26</div>
<div className="aspect-square p-2 bg-faro-surface-container-highest/20 rounded-[0.25rem] flex items-start justify-center text-faro-on-surface-variant/30 text-sm">27</div>
<div className="aspect-square p-2 bg-faro-surface-container-highest/20 rounded-[0.25rem] flex items-start justify-center text-faro-on-surface-variant/30 text-sm">28</div>
<div className="aspect-square p-2 bg-faro-surface-container-highest/20 rounded-[0.25rem] flex items-start justify-center text-faro-on-surface-variant/30 text-sm">29</div>
<div className="aspect-square p-2 bg-faro-surface-container-highest/20 rounded-[0.25rem] flex items-start justify-center text-faro-on-surface-variant/30 text-sm">30</div>
<div className="aspect-square p-2 bg-faro-surface-container-highest/20 rounded-[0.25rem] flex items-start justify-center text-faro-on-surface-variant/30 text-sm">31</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer border border-transparent hover:border-faro-primary/30">
<span className="text-sm">1</span>
</div>
{/*  Row 2  */}
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">2</span>
<div className="w-1.5 h-1.5 bg-faro-primary rounded-[0.75rem]"></div>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">3</span>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">4</span>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer border-2 border-faro-primary/50">
<span className="text-sm font-bold text-faro-primary">5</span>
<div className="flex gap-0.5">
<div className="w-1 h-1 bg-faro-secondary rounded-[0.75rem]"></div>
<div className="w-1 h-1 bg-faro-primary rounded-[0.75rem]"></div>
</div>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">6</span>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">7</span>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">8</span>
</div>
{/*  Row 3  */}
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">9</span>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">10</span>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">11</span>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">12</span>
<div className="w-1.5 h-1.5 bg-faro-secondary rounded-[0.75rem]"></div>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">13</span>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">14</span>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">15</span>
</div>
{/*  Simplified rows for visual representation  */}
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex items-start justify-center text-sm">16</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex items-start justify-center text-sm">17</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex items-start justify-center text-sm">18</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex items-start justify-center text-sm">19</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex items-start justify-center text-sm">20</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex items-start justify-center text-sm">21</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex items-start justify-center text-sm">22</div>
{/*  Day with featured event highlight style  */}
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer">
<span className="text-sm">23</span>
</div>
<div className="aspect-square p-2 bg-faro-primary/20 rounded-[0.25rem] flex flex-col items-center justify-between cursor-pointer border border-faro-primary/40 relative overflow-hidden group/day">
<div className="absolute inset-0 bg-faro-primary/10 opacity-0 group-hover/day:opacity-100 transition-opacity"></div>
<span className="text-sm font-bold text-faro-primary relative z-10">24</span>
<span className="material-symbols-outlined text-[10px] text-faro-primary fill-1 relative z-10">star</span>
</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex items-start justify-center text-sm">25</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex items-start justify-center text-sm">26</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex items-start justify-center text-sm">27</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex items-start justify-center text-sm">28</div>
<div className="aspect-square p-2 hover:bg-faro-surface-container-highest transition-colors rounded-[0.25rem] flex items-start justify-center text-sm">29</div>
</div>
</div>
{/*  Sidebar: Próximos Destacados  */}
<div className="lg:col-span-4 space-y-6">
<div className="bg-faro-surface-container-low rounded-2xl p-8 border border-faro-outline-variant/10">
<h3 className="font-headline text-xl font-bold mb-6 flex items-center gap-2">
<span className="material-symbols-outlined text-faro-primary">auto_awesome</span>
                    Destacados de Junio
                </h3>
<div className="space-y-6">
<div className="flex gap-4 group cursor-pointer">
<div className="flex-shrink-0 w-16 h-16 rounded-[0.5rem] overflow-hidden">
<img alt="Event" className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-300" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBW9z4SKaWBOdvIrWPAqBcSItdN-u6Wz_qRTcj7ELe_DrXAIjnd3ADxIccD3ijx0XnVmcf63O54WsljxF6QqIYhpT4BN1f3YNodKh7VI5I6KRj0xt4lgv3tBiXMWA5bV9r7sOuKSFBPGf-O-z-S-PH1bgFDKoiZJ5ve4Pl3pLSXodd9gMoDeDQxFBoX6uWCacA4knZd9T8MFqwu8UB_6JzMpbi09di76aHNAO68FQ1hQv3VB5I2374yhqqtKtYJ1ofF8sBq5adY4HwX"/>
</div>
<div>
<p className="text-[10px] font-bold text-faro-secondary uppercase tracking-widest mb-1">Música • 12 JUN</p>
<h4 className="text-sm font-bold group-hover:text-faro-primary transition-colors">Festival FARO Sound</h4>
<p className="text-xs text-faro-on-surface-variant line-clamp-1">Música en vivo en Sede Jardín.</p>
</div>
</div>
<div className="flex gap-4 group cursor-pointer">
<div className="flex-shrink-0 w-16 h-16 rounded-[0.5rem] overflow-hidden">
<img alt="Event" className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-300" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDlfe5nWlCY5n15IXPMDiT038q3Ub-A4sNfRFYcKcqqPor7XME2XkgXXK-Nd82oa3q3jNisTCpWTG5egEcodKp1GJ72Gd6TAuiWsIDpmw6FK8GS1rWDQbFamacLIxNqaT2-cEC_6PKmuFHXViCY1nJyIc_B8J08Rwbuuv4l6ZalNUlf4ja69TfZ_s2h0DXoG7t5KrnibidyhZgV48ahvkcKjoowTbYX52yeedKmgVHn-tPKkqteabjfC8prCR2GHeS8y_3SyHoG0_bi"/>
</div>
<div>
<p className="text-[10px] font-bold text-faro-primary uppercase tracking-widest mb-1">Especial • 24 JUN</p>
<h4 className="text-sm font-bold group-hover:text-faro-primary transition-colors">Noche de Iluminación</h4>
<p className="text-xs text-faro-on-surface-variant line-clamp-1">Adoración y Palabra profética.</p>
</div>
</div>
<div className="flex gap-4 group cursor-pointer">
<div className="flex-shrink-0 w-16 h-16 rounded-[0.5rem] overflow-hidden border border-faro-outline-variant/30 flex items-center justify-center bg-faro-surface-container-highest">
<span className="material-symbols-outlined text-faro-on-surface/20">event_repeat</span>
</div>
<div>
<p className="text-[10px] font-bold text-faro-on-surface-variant uppercase tracking-widest mb-1">Semanal • Domingos</p>
<h4 className="text-sm font-bold group-hover:text-faro-primary transition-colors">Reuniones Generales</h4>
<p className="text-xs text-faro-on-surface-variant">09:00, 11:00 y 18:00 hrs.</p>
</div>
</div>
</div>
<button className="w-full mt-8 py-3 rounded-[0.5rem] border border-faro-primary/30 text-faro-primary text-xs font-bold tracking-widest uppercase hover:bg-faro-primary/5 transition-colors">
                    Sincronizar Calendario
                </button>
</div>
<div className="bg-faro-primary-container/20 rounded-2xl p-6 border border-faro-primary/20 flex items-center gap-4">
<div className="bg-faro-primary text-faro-on-primary p-3 rounded-[0.75rem]">
<span className="material-symbols-outlined">notifications_active</span>
</div>
<div>
<h4 className="font-bold text-sm">¿Quieres recordatorios?</h4>
<p className="text-xs text-faro-on-surface-variant">Recibe avisos de tus eventos favoritos.</p>
</div>
</div>
</div>
</div>
</section>
</main>
        </>
    );
}
