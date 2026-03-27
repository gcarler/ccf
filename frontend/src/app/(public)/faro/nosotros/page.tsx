"use client";

import Link from "next/link";
import React from "react";

export default function NosotrosPage() {
    return (
        <>
            <aside className="hidden lg:flex flex-col h-full py-8 px-4 h-full w-80 fixed left-0 top-0 z-[60] bg-[#001134] pt-28">
<div className="mb-12 px-4">
<h2 className="text-xl font-black text-[#a5c8ff]">The Radiant Guide</h2>
<p className="text-xs font-medium text-[#d9e2ff]/50 uppercase tracking-widest mt-1">Comunidad FARO</p>
</div>
<div className="space-y-2 flex-1">
<a className="flex items-center gap-4 px-4 py-3 rounded-[0.5rem] text-[#d9e2ff]/60 hover:bg-[#004581]/10 hover:text-[#a5c8ff] transition-all font-manrope tracking-tight" href="#">
<span className="material-symbols-outlined">format_quote</span> Testimonios
            </a>
<a className="flex items-center gap-4 px-4 py-3 rounded-[0.5rem] text-[#d9e2ff]/60 hover:bg-[#004581]/10 hover:text-[#a5c8ff] transition-all font-manrope tracking-tight" href="#">
<span className="material-symbols-outlined">auto_awesome</span> Conocer a Jesús
            </a>
<a className="flex items-center gap-4 px-4 py-3 rounded-[0.5rem] text-[#a5c8ff] bg-[#004581]/20 font-bold font-manrope tracking-tight" href="#">
<span className="material-symbols-outlined">info</span> Sobre Nosotros
            </a>
<a className="flex items-center gap-4 px-4 py-3 rounded-[0.5rem] text-[#d9e2ff]/60 hover:bg-[#004581]/10 hover:text-[#a5c8ff] transition-all font-manrope tracking-tight" href="#">
<span className="material-symbols-outlined">menu_book</span> Libros
            </a>
<a className="flex items-center gap-4 px-4 py-3 rounded-[0.5rem] text-[#d9e2ff]/60 hover:bg-[#004581]/10 hover:text-[#a5c8ff] transition-all font-manrope tracking-tight" href="#">
<span className="material-symbols-outlined">schedule</span> Horarios
            </a>
<a className="flex items-center gap-4 px-4 py-3 rounded-[0.5rem] text-[#d9e2ff]/60 hover:bg-[#004581]/10 hover:text-[#a5c8ff] transition-all font-manrope tracking-tight" href="#">
<span className="material-symbols-outlined">mail</span> Contacto
            </a>
</div>
</aside><main className="lg:ml-80 pt-20 min-h-screen">
{/*  Hero Section: Editorial Impact  */}
<section className="relative px-8 pt-20 pb-32 overflow-hidden">
<div className="absolute inset-0 bg-light-glow pointer-events-none"></div>
<div className="max-w-6xl mx-auto editorial-grid">
<div className="col-span-12 lg:col-span-8">
<span className="label-md uppercase tracking-[0.2em] text-faro-secondary font-semibold mb-6 block">Nuestra Identidad</span>
<h1 className="text-6xl md:text-8xl font-headline font-extrabold text-faro-on-background leading-tight tracking-tighter mb-8">
                        Iluminando el <br/><span className="text-transparent bg-clip-text bg-gradient-to-r from-faro-primary to-faro-secondary">camino juntos.</span>
</h1>
<p className="text-xl md:text-2xl text-faro-on-surface-variant font-body leading-relaxed max-w-2xl">
                        Somos una comunidad vibrante dedicada a guiar a las personas hacia una vida llena de propósito y luz a través del mensaje de esperanza.
                    </p>
</div>
</div>
</section>
{/*  Vision & Mission: Asymmetric Bento Grid  */}
<section className="px-8 py-24 bg-faro-surface-container-low">
<div className="max-w-6xl mx-auto">
<div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-stretch">
{/*  Vision Card  */}
<div className="md:col-span-7 bg-faro-surface-container-high rounded-[0.5rem] p-12 relative overflow-hidden flex flex-col justify-end min-h-[400px]">
<div className="absolute top-0 right-0 w-64 h-64 bg-faro-primary/5 rounded-[0.75rem] -mr-20 -mt-20 blur-3xl"></div>
<span className="material-symbols-outlined text-faro-primary text-5xl mb-6" style={{ fontVariationSettings: "'FILL' 1" }}>visibility</span>
<h3 className="text-4xl font-headline font-bold text-faro-on-surface mb-6">Nuestra Visión</h3>
<p className="text-lg text-faro-on-surface-variant leading-relaxed">
                            Ser un faro global de transformación espiritual, donde cada individuo descubra su luz interior y se convierta en un agente de cambio positivo en su sociedad, fundamentado en el amor y la verdad.
                        </p>
</div>
{/*  Mission Card  */}
<div className="md:col-span-5 bg-faro-surface-bright rounded-[0.5rem] p-12 border border-faro-outline-variant/20 flex flex-col justify-between">
<div>
<span className="material-symbols-outlined text-faro-secondary text-5xl mb-6">explore</span>
<h3 className="text-4xl font-headline font-bold text-faro-on-surface mb-6">Nuestra Misión</h3>
</div>
<p className="text-lg text-faro-on-surface-variant leading-relaxed">
                            Guiar, equipar y movilizar a la comunidad a través de la enseñanza práctica, el compañerismo genuino y el servicio desinteresado, reflejando el carácter de Jesús en cada acción.
                        </p>
</div>
</div>
</div>
</section>
{/*  Founders Section: The Human Connection  */}
<section className="px-8 py-32">
<div className="max-w-6xl mx-auto">
<div className="flex flex-col lg:flex-row items-center gap-20">
<div className="w-full lg:w-1/2 relative">
{/*  Founder Image Overlay Pattern  */}
<div className="relative z-10 aspect-[4/5] rounded-[0.5rem] overflow-hidden shadow-2xl">
<img className="w-full h-full object-cover" data-alt="Modern professional portrait of a couple, David and Sara Mendoza, smiling warmly in a bright contemporary office setting with soft natural sunlight" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCEnj5pxBR1roMdX9LhwTMqT8HG1NEe5M1j96Exx-x82E0kOvjyAOfNB9YmrRXYnJsaooh5d3VhcKTfBMKURrDdPUONpDFv9ld9tur12Iqqm4prgobkxJ5hVqjgAAwcoTqVZiMcDMV3uUOCQPHt5Wl6tiRxma5uPUO5e7qGKDIW_9ZvWnsrgyF4IwJsB8p07X01rzk1UfFgyIZMHpGKwFcvDncIOw4X-zsLLW_j4iPwJ1wZf1svG1JQLFLBXijDz2cszCAwQGQk62UK"/>
</div>
<div className="absolute -bottom-8 -right-8 w-48 h-48 bg-faro-primary-container/30 rounded-[0.75rem] blur-3xl -z-10"></div>
<div className="absolute -top-8 -left-8 w-64 h-64 bg-faro-secondary-container/20 rounded-[0.75rem] blur-3xl -z-10"></div>
</div>
<div className="w-full lg:w-1/2">
<span className="label-md uppercase tracking-widest text-faro-primary font-bold mb-4 block">Nuestros Fundadores</span>
<h2 className="text-5xl font-headline font-extrabold text-faro-on-background mb-8 leading-tight">David &amp; Sara Mendoza</h2>
<div className="space-y-6 text-faro-on-surface-variant text-lg leading-relaxed">
<p>
                                Con más de dos décadas de liderazgo comunitario, David y Sara fundaron FARO con el sueño de crear un espacio donde la fe y la modernidad se encontraran de manera relevante.
                            </p>
<p>
                                Su enfoque editorial y estético no es solo una elección visual, sino una declaración de que la espiritualidad puede ser clara, profesional y profundamente hermosa. Juntos, han dedicado sus vidas a construir puentes de luz en medio de la oscuridad.
                            </p>
<div className="pt-8 flex gap-8">
<div className="flex flex-col">
<span className="text-3xl font-bold text-faro-primary">25+</span>
<span className="text-sm uppercase tracking-tighter text-[#d9e2ff]/50">Años de Servicio</span>
</div>
<div className="w-px h-12 bg-faro-outline-variant/30"></div>
<div className="flex flex-col">
<span className="text-3xl font-bold text-faro-secondary">15k</span>
<span className="text-sm uppercase tracking-tighter text-[#d9e2ff]/50">Vidas Impactadas</span>
</div>
</div>
</div>
</div>
</div>
</div>
</section>
{/*  Values Section: Editorial List  */}
<section className="px-8 py-24 bg-faro-surface-container-lowest">
<div className="max-w-6xl mx-auto">
<div className="mb-20 text-center">
<h2 className="text-4xl font-headline font-bold text-faro-on-surface">Valores que nos Guían</h2>
<div className="h-1.5 w-24 bg-gradient-to-r from-faro-primary to-faro-secondary mx-auto mt-6 rounded-[0.75rem]"></div>
</div>
<div className="grid grid-cols-1 md:grid-cols-3 gap-16">
<div className="space-y-4">
<div className="text-6xl font-black text-faro-outline-variant/20 font-headline">01</div>
<h4 className="text-2xl font-bold text-faro-on-surface">Integridad Radial</h4>
<p className="text-faro-on-surface-variant">Vivir con transparencia absoluta, permitiendo que nuestra luz interior sea coherente con nuestras acciones exteriores.</p>
</div>
<div className="space-y-4">
<div className="text-6xl font-black text-faro-outline-variant/20 font-headline">02</div>
<h4 className="text-2xl font-bold text-faro-on-surface">Innovación Guiada</h4>
<p className="text-faro-on-surface-variant">Abrazamos el futuro y las nuevas formas de conectar sin perder la esencia de los principios eternos.</p>
</div>
<div className="space-y-4">
<div className="text-6xl font-black text-faro-outline-variant/20 font-headline">03</div>
<h4 className="text-2xl font-bold text-faro-on-surface">Amor Radical</h4>
<p className="text-faro-on-surface-variant">Un compromiso inquebrantable de servir a todos, sin importar su origen o camino recorrido.</p>
</div>
</div>
</div>
</section>
{/*  Call to Action  */}
<section className="px-8 py-32 text-center">
<div className="max-w-3xl mx-auto bg-faro-surface-container rounded-[2rem] p-16 shadow-2xl relative overflow-hidden">
<div className="absolute inset-0 bg-gradient-to-br from-faro-primary/10 to-transparent"></div>
<div className="relative z-10">
<h2 className="text-4xl font-headline font-bold mb-6 text-faro-on-surface">¿Listo para unirte al camino?</h2>
<p className="text-lg text-faro-on-surface-variant mb-10">Descubre cómo puedes ser parte de esta comunidad que ilumina el mundo.</p>
<div className="flex flex-col sm:flex-row gap-4 justify-center">
<button className="bg-gradient-to-r from-faro-primary to-faro-primary-container text-faro-on-primary font-bold px-10 py-4 rounded-[0.75rem] shadow-lg hover:brightness-110 transition-all">Visítanos este Domingo</button>
<button className="bg-faro-surface-bright text-faro-on-surface font-bold px-10 py-4 rounded-[0.75rem] border border-faro-outline-variant/30 hover:bg-faro-surface-container-highest transition-all">Conoce nuestras Sedes</button>
</div>
</div>
</div>
</section>
{/*  Footer Footer (Simple)  */}
<footer className="px-8 py-12 border-t border-faro-outline-variant/10 text-center">
<div className="text-sm text-faro-on-surface-variant/60 tracking-widest uppercase">
                FARO © 2024 — El Faro de la Comunidad
            </div>
</footer>
</main>
        </>
    );
}
