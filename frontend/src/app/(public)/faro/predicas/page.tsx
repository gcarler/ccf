"use client";

import Link from "next/link";
import React from "react";
import { useContentBlock } from "@/hooks/useContent";

export default function PredicasPage() {
    const { data: heroContent } = useContentBlock("faro_sermons_hero");
    const heroEyebrow = heroContent?.eyebrow || "Mensaje Destacado";
    const heroTitleLead = heroContent?.title_lead || "Alimento para el";
    const heroAccent = heroContent?.title_accent || "Alma";
    const heroDescription =
        heroContent?.description ||
        "Explora nuestra biblioteca de mensajes que iluminan el camino. Una guía espiritual diseñada para nutrir tu fe en tiempos de cambio.";

    return (
        <>
            <main className="pt-20 pb-32">
{/*  Hero Section: Cinematic Anchor  */}
<section className="relative h-[716px] w-full overflow-hidden flex items-end px-8 md:px-20 pb-20">
<div className="absolute inset-0 z-0">
<img className="w-full h-full object-cover brightness-[0.4] scale-105" data-alt="dramatic wide shot of a lighthouse beacon cutting through dark night fog with ocean waves crashing in distance cinematic lighting" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBk4oOmMlOHJ1Q0a_j0hT6dwsM59HKhiMz3T7yWt4gedGtM7_w9C60ThuZK2_rxLKh_C26Hd5SWFixqxe7XQvvBn36iOhvDQG41gD4ZexkG1kTTfrW7KSnKfbu1Uh2RNVfIoRiRvxtE6djC9E_Usx2GABdV19D8Lq5H-fWeJzxqjkEWUJRS_EeKXNgFWaGLL_gCbA9HdyZXZqieucWegwhpakTaCMLAh-KsNZ1cDTcJXm0yhY2Aj2rwOxMaREbnlyecA3ijnZVMntjN"/>
<div className="absolute inset-0 bg-gradient-to-t from-faro-background via-transparent to-transparent"></div>
<div className="absolute inset-0 bg-gradient-to-r from-faro-background/80 via-transparent to-transparent"></div>
</div>
<div className="relative z-10 max-w-4xl space-y-6">
<div className="flex items-center space-x-3">
<span className="w-12 h-[2px] bg-faro-primary"></span>
<span className="font-headline font-bold text-faro-primary tracking-widest uppercase text-sm">{heroEyebrow}</span>
</div>
<h1 className="font-headline text-5xl md:text-7xl font-extrabold tracking-tight text-glow leading-tight">
                    {heroTitleLead} <span className="text-faro-primary italic">{heroAccent}</span>
</h1>
<p className="text-lg md:text-xl text-faro-on-surface-variant max-w-2xl leading-relaxed">
                    {heroDescription}
                </p>
<div className="flex flex-wrap gap-4 pt-4">
<button className="bg-gradient-to-br from-faro-primary to-faro-primary-container text-faro-on-primary px-8 py-4 rounded-[0.75rem] font-bold flex items-center space-x-2 shadow-[0_0_20px_rgba(165,200,255,0.3)] transition-transform hover:scale-105">
<span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>play_arrow</span>
<span>Ver ahora</span>
</button>
<button className="bg-faro-surface-bright/20 backdrop-blur-md border border-faro-outline-variant/30 text-faro-on-surface px-8 py-4 rounded-[0.75rem] font-bold hover:bg-faro-surface-bright/40 transition-all">
                        Añadir a mi lista
                    </button>
</div>
</div>
</section>
{/*  Categories & Filter Section  */}
<section className="px-8 md:px-20 -mt-12 relative z-20">
<div className="glass-card rounded-[0.5rem] p-8 flex flex-col md:flex-row items-center justify-between gap-8 border border-faro-outline-variant/10">
<div className="flex flex-wrap gap-6 font-manrope font-bold text-sm tracking-widest uppercase">
<a className="text-faro-primary border-b-2 border-faro-primary pb-1" href="#">Todas</a>
<a className="text-faro-on-surface-variant hover:text-faro-primary transition-colors" href="#">Series</a>
<a className="text-faro-on-surface-variant hover:text-faro-primary transition-colors" href="#">Oradores</a>
<a className="text-faro-on-surface-variant hover:text-faro-primary transition-colors" href="#">Tópicos</a>
</div>
<div className="flex items-center space-x-4 w-full md:w-auto">
<div className="relative flex-grow md:w-72">
<span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-faro-on-surface-variant/60">filter_list</span>
<select className="w-full bg-faro-surface-container-highest border-none rounded-[0.25rem] pl-12 pr-4 py-3 text-sm focus:ring-1 focus:ring-faro-primary/50 appearance-none text-faro-on-surface">
<option>Más recientes</option>
<option>Más vistos</option>
<option>Recomendados</option>
</select>
</div>
</div>
</div>
</section>
{/*  Video Gallery: Bento Grid Style  */}
<section className="px-8 md:px-20 mt-20 space-y-12">
<div className="flex items-center justify-between">
<h2 className="font-headline text-3xl font-bold">Nuevos Lanzamientos</h2>
<a className="text-faro-primary text-sm font-bold flex items-center space-x-1 hover:underline" href="#">
<span>Ver todo</span>
<span className="material-symbols-outlined text-lg">chevron_right</span>
</a>
</div>
<div className="grid grid-cols-1 md:grid-cols-12 gap-6">
{/*  Large Featured Card  */}
<div className="md:col-span-8 group cursor-pointer relative overflow-hidden rounded-[0.5rem] bg-faro-surface-container-low">
<div className="aspect-video relative overflow-hidden">
<img className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105 brightness-75" data-alt="intense speaker on stage with dramatic blue and amber stage lights atmospheric smoke and silhouetted crowd" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBz85hegWU-3KHI2lhv-e9o_7W7_9qNyYh2rIWM6kQWdZyIPLTjreuTuZedui9bWGSfc6iFYtX3Y7QZw3gGj4YzEedudNOrRr1TCKv5mHWbF58rvpUxaFqNrBO70h0vNvUSa84sAlqgCuIn22AI4i7YWvsDqltLNTEJVJ3ySvAdf7stj3cHMVvAD7qRX28UI8C5CTNnu4rXliR4atUXY9EEnGbgSfajCFaQEoyk-uKSaTQoOqHbdCtWpv52Pi2LK7iFOjz5rhuxhVrB"/>
<div className="absolute inset-0 bg-gradient-to-t from-faro-surface-container-low to-transparent opacity-80"></div>
<div className="absolute top-4 left-4 bg-faro-primary text-faro-on-primary text-[10px] font-bold px-3 py-1 rounded-[0.75rem] uppercase tracking-widest">Estreno</div>
<div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
<div className="w-20 h-20 rounded-[0.75rem] bg-faro-primary/20 backdrop-blur-xl border border-faro-primary/30 flex items-center justify-center shadow-[0_0_30px_rgba(165,200,255,0.4)]">
<span className="material-symbols-outlined text-faro-primary text-5xl" style={{ fontVariationSettings: "'FILL' 1" }}>play_arrow</span>
</div>
</div>
</div>
<div className="p-8">
<div className="flex items-center space-x-4 mb-3">
<span className="text-faro-primary text-xs font-bold uppercase tracking-widest">Serie: Renacer</span>
<span className="text-faro-on-surface-variant/40">•</span>
<span className="text-faro-on-surface-variant text-xs">45 min</span>
</div>
<h3 className="font-headline text-2xl font-bold mb-3 group-hover:text-faro-primary transition-colors">Encontrando luz en medio del desierto</h3>
<p className="text-faro-on-surface-variant line-clamp-2 max-w-2xl">Un mensaje profundo sobre la perseverancia y la fe cuando los caminos parecen cerrarse.</p>
</div>
</div>
{/*  Secondary Cards  */}
<div className="md:col-span-4 flex flex-col gap-6">
<div className="group cursor-pointer bg-faro-surface-container-low rounded-[0.5rem] overflow-hidden border border-transparent hover:border-faro-primary/20 transition-all">
<div className="aspect-video relative">
<img className="w-full h-full object-cover brightness-75 transition-transform group-hover:scale-105" data-alt="abstract warm golden light particles floating in dark space ethereal spiritual atmosphere" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDsz0naQyRI2FVlDfYJ6upoYm6_muRgqJAMLyz4R6TkKfVYdAHlkew5ywUVbaxBuQhgeCNHHTPCP7UQDvNOh5eqFsXbu-rmLDAjTuEmxvJDQxJyUR_syvU1VI7675xHjf_tvkXIjL-G6NC2QiPy2UPvWHpzU_A2HIeV6DhkGdWgA10-xtM9_7IiAH9u9jjWcvgz5Qh57JDy3TBBKwQhR7LidMnFJYelRkgpzERq7F1WWLiJkt915hJ4J3CsFjQjjuFo7Wum1zsc3rrf"/>
<div className="absolute bottom-2 right-2 bg-black/60 backdrop-blur-md text-[10px] px-2 py-1 rounded text-white font-mono">32:15</div>
</div>
<div className="p-4">
<h4 className="font-headline font-bold text-lg mb-1 group-hover:text-faro-primary transition-colors">La paz que sobrepasa entendimiento</h4>
<p className="text-faro-on-surface-variant text-xs">Pr. David Miller</p>
</div>
</div>
<div className="group cursor-pointer bg-faro-surface-container-low rounded-[0.5rem] overflow-hidden border border-transparent hover:border-faro-primary/20 transition-all">
<div className="aspect-video relative">
<img className="w-full h-full object-cover brightness-75 transition-transform group-hover:scale-105" data-alt="close-up of ancient book pages with warm sunlight highlighting the texture of the paper" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBwuUSN7zl3j08eb9oGB-wVJeMPU6MX1eXCanAItaoDz_G2RvdRG9h00K3EF4UAvFpBlx5x7gJ2qAORkXc1CUhKF-tYeRjWrQ3TuhtS4-cS1W1qmwLlDBifvVgJhBurO78lsMvXqut9SVaAhCzc8h4LDrqxn03bPPONTmJyKcXFn750drZ8Q_yO792WaUYEmt9m0xukysN67gJuTCMK7Vz43n-qYSJ-G3ctzOT-meTghA-RRZwIFL6e3oTjhbZa3lVLxC1SCR7lI8cW"/>
<div className="absolute bottom-2 right-2 bg-black/60 backdrop-blur-md text-[10px] px-2 py-1 rounded text-white font-mono">28:40</div>
</div>
<div className="p-4">
<h4 className="font-headline font-bold text-lg mb-1 group-hover:text-faro-primary transition-colors">Principios de sabiduría eterna</h4>
<p className="text-faro-on-surface-variant text-xs">Dra. Sarah Jenkins</p>
</div>
</div>
</div>
</div>
{/*  Series Grid  */}
<div className="pt-20">
<div className="flex items-center justify-between mb-8">
<h2 className="font-headline text-3xl font-bold">Series Populares</h2>
</div>
<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
<div className="group relative aspect-[3/4] rounded-[0.5rem] overflow-hidden bg-faro-surface-container-highest cursor-pointer">
<img className="w-full h-full object-cover brightness-50 transition-transform duration-500 group-hover:scale-110" data-alt="modern architecture building reflecting golden hour sunlight with deep shadows and clean lines" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBGTKRhWNFhg0Zu0VT-FfcMv8YgRQ6VJn6CFOyhb9cpEE9d9q7N73RQMi-3nLCfvf6CxOekL6kMld-2VIOyeoOMjrCx_CaNshr74H6htrkaaXV_VvM8WxMyWWThBP5HHFx89Z1UwkUBEosvj_MM1ufo-iJh8BS8l3EwEWSCdcFajUMrhG2t306EFZi0dbYz6qpLAJoAcBLzPA4dX9YgeT8GAeY6ueWF9Sz3OB_tK8PU_tVjuYL6XLgCeaCPORh98-Pc4v8MEMv2g7e2"/>
<div className="absolute inset-0 bg-gradient-to-t from-faro-primary-container/90 to-transparent flex flex-col justify-end p-6">
<span className="text-faro-primary text-[10px] font-bold uppercase tracking-widest mb-1">12 Episodios</span>
<h3 className="font-headline font-bold text-xl leading-tight">Fundamentos</h3>
</div>
</div>
<div className="group relative aspect-[3/4] rounded-[0.5rem] overflow-hidden bg-faro-surface-container-highest cursor-pointer">
<img className="w-full h-full object-cover brightness-50 transition-transform duration-500 group-hover:scale-110" data-alt="lush forest path with rays of morning sun breaking through dense green canopy creating glowing trails of light" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDt8o8QUSc78EW8Nbb683kJwFNhRuU8xlPt2_1FRnNcbnSsQE2vHVF5KGZDldZEbiIUFBTClM0NBGbjDJ-dfRqzd52tMl48-4iTdvJ3nPNTCo02rKVSJi804gtrMInHuSNj8Nz2xC2bD8yabGriFtS5Uz7c5m77RRnCg99qzyiof1578uAg3a3LQFVVSN1OTvGoQRvUI3Ckr613saCbctpNIyT2PrI3KaDBT_Ut-3n50u4Fx3J8tZ1tb905diMelcdfnuJxWilqLxUF"/>
<div className="absolute inset-0 bg-gradient-to-t from-faro-primary-container/90 to-transparent flex flex-col justify-end p-6">
<span className="text-faro-primary text-[10px] font-bold uppercase tracking-widest mb-1">8 Episodios</span>
<h3 className="font-headline font-bold text-xl leading-tight">El Camino</h3>
</div>
</div>
<div className="group relative aspect-[3/4] rounded-[0.5rem] overflow-hidden bg-faro-surface-container-highest cursor-pointer">
<img className="w-full h-full object-cover brightness-50 transition-transform duration-500 group-hover:scale-110" data-alt="starry night sky over a quiet dark mountain range with deep navy and violet tones" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDjvbPEFdlyKy9GlRk3eQyGen49RuMwLIJ9SVvI7Kk7GQFtXJSzG7xo8mvAQhyPZkvb23LAPAisbCItZxxKEWGHgfdnaNLa3B2O4AaghMDgvdWJdH3QvNYhETl19jiHwifkLspkeZJBCSvLx11cd9lfVLFX5iagV8ygIiLnY7OwaL7SzTLRvK8MKp0SE2Lj8aXSn9N-jSngCjm3baYKA4Cq79yLduWbfGYbZQZRFFkTfcOahEWsepCa-VxO7HneZ-k8shlvs2Ias-uy"/>
<div className="absolute inset-0 bg-gradient-to-t from-faro-primary-container/90 to-transparent flex flex-col justify-end p-6">
<span className="text-faro-primary text-[10px] font-bold uppercase tracking-widest mb-1">15 Episodios</span>
<h3 className="font-headline font-bold text-xl leading-tight">Noches de Gloria</h3>
</div>
</div>
<div className="group relative aspect-[3/4] rounded-[0.5rem] overflow-hidden bg-faro-surface-container-highest cursor-pointer">
<img className="w-full h-full object-cover brightness-50 transition-transform duration-500 group-hover:scale-110" data-alt="close up of a compass on an old map with warm directional lighting suggesting a journey" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDGMQxxG1JTBnOpsY-e7jZYTFwgP3Kl4F7bzjR_BK3OrVfJd_Abkv75nG8xexxVu3pHNJTN1EpJrfBsCRq_shAmRk06yhHJ7HOPPIGPdoF_SAvVHOzhFvK8zcNOXOaSo9477twU0GHv7DnzhzDevOkECT6gufv34C_uy0kIIyD3f8hi4RMV-IVbcxFMr0xxxHkjMd7Fvm076kruLdjLrKKR4Qri1YdLD479TWTgxCBxAgtiuMVcMCSVTLbul002aVbsJOVD2kddG3Kf"/>
<div className="absolute inset-0 bg-gradient-to-t from-faro-primary-container/90 to-transparent flex flex-col justify-end p-6">
<span className="text-faro-primary text-[10px] font-bold uppercase tracking-widest mb-1">6 Episodios</span>
<h3 className="font-headline font-bold text-xl leading-tight">Nuevos Rumbos</h3>
</div>
</div>
</div>
</div>
</section>
</main>
        </>
    );
}
