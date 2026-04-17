"use client";

import Link from "next/link";
import React from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { ArrowRight, Target, Users, Heart, Star, Sparkles, Quote } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";

export default function NosotrosPage() {
    const { data: heroContent } = useContentBlock("faro_about_hero");
    
    const heroEyebrow = heroContent?.eyebrow || "Nuestra Identidad";
    const heroTitleLead = heroContent?.title_lead || "Iluminando el";
    const heroTitleAccent = heroContent?.title_accent || "camino juntos";
    const heroDescription = heroContent?.description || "Somos una comunidad vibrante dedicada a guiar a las personas hacia una vida llena de propósito y luz a través del mensaje de esperanza.";

    return (
        <main className="pt-[88px]">
            {/* ── HERO EDITORIAL ────────────────────────────────── */}
            <section className="relative px-6 md:px-16 lg:px-24 py-24 overflow-hidden">
                <div className="absolute inset-0 bg-light-glow pointer-events-none opacity-50" />
                <div className="max-w-6xl mx-auto relative z-10">
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="max-w-3xl"
                    >
                        <span 
                            className="text-xs font-black uppercase tracking-[0.4em] mb-8 block"
                            style={{ color: "var(--faro-primary)" }}
                        >
                            {heroEyebrow}
                        </span>
                        <h1 
                            className="font-black tracking-tighter leading-[0.9] mb-10"
                            style={{ 
                                fontSize: "clamp(3.5rem, 8vw, 7.5rem)",
                                color: "var(--faro-on-background)"
                            }}
                        >
                            {heroTitleLead} <br/>
                            <span 
                                className="italic"
                                style={{ 
                                    background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                    WebkitBackgroundClip: "text",
                                    WebkitTextFillColor: "transparent"
                                }}
                            >
                                {heroTitleAccent}.
                            </span>
                        </h1>
                        <p 
                            className="text-xl md:text-2xl leading-relaxed opacity-80"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                        >
                            {heroDescription}
                        </p>
                    </motion.div>
                </div>
            </section>

            {/* ── VISIÓN Y MISIÓN: BENTO GRID ────────────────────── */}
            <section 
                className="py-24 px-6 md:px-16 lg:px-24"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div className="max-w-6xl mx-auto">
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
                        <motion.div 
                            initial={{ opacity: 0, x: -20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true }}
                            className="md:col-span-7 rounded-[2.5rem] p-12 relative overflow-hidden flex flex-col justify-end min-h-[400px]"
                            style={{ background: "var(--faro-surface-container-high)" }}
                        >
                            <div className="absolute top-10 left-10 opacity-20">
                                <Target size={80} style={{ color: "var(--faro-primary)" }} />
                            </div>
                            <div className="relative z-10">
                                <h3 className="text-4xl font-black mb-6" style={{ color: "var(--faro-on-surface)" }}>Nuestra Visión</h3>
                                <p className="text-lg leading-relaxed opacity-80" style={{ color: "var(--faro-on-surface-variant)" }}>
                                    Ser un faro global de transformación espiritual, donde cada individuo descubra su luz interior y se convierta en un agente de cambio positivo en su sociedad, fundamentado en el amor y la verdad.
                                </p>
                            </div>
                        </motion.div>

                        <motion.div 
                            initial={{ opacity: 0, x: 20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true }}
                            className="md:col-span-5 rounded-[2.5rem] p-12 flex flex-col justify-between border"
                            style={{ 
                                background: "var(--faro-surface-bright)",
                                borderColor: "var(--faro-outline-variant)"
                            }}
                        >
                            <Sparkles size={48} style={{ color: "var(--faro-secondary)" }} className="mb-6" />
                            <div>
                                <h3 className="text-4xl font-black mb-6" style={{ color: "var(--faro-on-surface)" }}>Nuestra Misión</h3>
                                <p className="text-lg leading-relaxed opacity-80" style={{ color: "var(--faro-on-surface-variant)" }}>
                                    Guiar, equipar y movilizar a la comunidad a través de la enseñanza práctica, el compañerismo genuino y el servicio desinteresado, reflejando el carácter de Jesús.
                                </p>
                            </div>
                        </motion.div>
                    </div>
                </div>
            </section>

            {/* ── FUNDADORES ────────────────────────────────────── */}
            <section className="py-32 px-6 md:px-16 lg:px-24">
                <div className="max-w-6xl mx-auto flex flex-col lg:flex-row items-center gap-20">
                    <div className="w-full lg:w-1/2 relative">
                        <div className="relative z-10 aspect-[4/5] rounded-[3rem] overflow-hidden shadow-2xl">
                            <Image 
                                className="object-cover" 
                                alt="David & Sara Mendoza"
                                src="https://images.unsplash.com/photo-1516585424602-c210be8163f5?w=800&q=80"
                                fill
                            />
                        </div>
                        <div 
                            className="absolute -bottom-8 -right-8 w-64 h-64 blur-[100px] -z-10 rounded-full"
                            style={{ background: "rgba(1, 138, 189, 0.15)" }}
                        />
                    </div>
                    <div className="w-full lg:w-1/2">
                        <span className="text-xs font-black uppercase tracking-widest mb-4 block" style={{ color: "var(--faro-primary)" }}>
                            Nuestros Fundadores
                        </span>
                        <h2 className="text-5xl md:text-6xl font-black mb-8 leading-tight" style={{ color: "var(--faro-on-background)" }}>
                            David & Sara Mendoza
                        </h2>
                        <div className="space-y-6 text-lg leading-relaxed opacity-80" style={{ color: "var(--faro-on-surface-variant)" }}>
                            <p>
                                Con más de dos décadas de liderazgo comunitario, David y Sara fundaron FARO con el sueño de crear un espacio donde la fe y la modernidad se encontraran de manera relevante.
                            </p>
                            <p>
                                Su enfoque editorial y estético no es solo una elección visual, sino una declaración de que la espiritualidad puede ser clara, profesional y profundamente hermosa.
                            </p>
                            <div className="pt-8 flex gap-12">
                                <div>
                                    <span className="text-4xl font-black block" style={{ color: "var(--faro-primary)" }}>25+</span>
                                    <span className="text-[10px] font-black uppercase tracking-widest opacity-50">Años de Servicio</span>
                                </div>
                                <div className="w-px h-12 bg-slate-200 dark:bg-white/10" />
                                <div>
                                    <span className="text-4xl font-black block" style={{ color: "var(--faro-secondary)" }}>15k</span>
                                    <span className="text-[10px] font-black uppercase tracking-widest opacity-50">Vidas Impactadas</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ── VALORES ───────────────────────────────────────── */}
            <section 
                className="py-24 px-6 md:px-16 lg:px-24"
                style={{ background: "var(--faro-surface-container-lowest)" }}
            >
                <div className="max-w-6xl mx-auto">
                    <div className="mb-20 text-center">
                        <h2 className="text-4xl font-black" style={{ color: "var(--faro-on-surface)" }}>Valores que nos Guían</h2>
                        <div 
                            className="h-1.5 w-24 mx-auto mt-6 rounded-full"
                            style={{ background: "linear-gradient(to right, var(--faro-primary), var(--faro-secondary))" }}
                        />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-16">
                        {[
                            { num: "01", title: "Integridad Radial", desc: "Vivir con transparencia absoluta, permitiendo que nuestra luz interior sea coherente con nuestras acciones." },
                            { num: "02", title: "Innovación Guiada", desc: "Abrazamos el futuro y las nuevas formas de conectar sin perder la esencia de los principios eternos." },
                            { num: "03", title: "Amor Radical", desc: "Un compromiso inquebrantable de servir a todos, sin importar su origen o camino recorrido." }
                        ].map((v) => (
                            <div key={v.num} className="space-y-4">
                                <div className="text-7xl font-black opacity-10" style={{ color: "var(--faro-primary)" }}>{v.num}</div>
                                <h4 className="text-2xl font-black" style={{ color: "var(--faro-on-surface)" }}>{v.title}</h4>
                                <p className="leading-relaxed opacity-70" style={{ color: "var(--faro-on-surface-variant)" }}>{v.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── QUOTE EDITORIAL ───────────────────────────────── */}
            <section className="py-32 px-6 md:px-16 text-center">
                <div className="max-w-3xl mx-auto">
                    <Quote size={60} className="mx-auto mb-8 opacity-20" style={{ color: "var(--faro-primary)" }} />
                    <blockquote 
                        className="text-3xl md:text-5xl font-black leading-tight italic mb-10"
                        style={{ color: "var(--faro-on-surface)" }}
                    >
                        La luz que encontramos en FARO no es para guardarla, es para guiar a otros que aún caminan en la oscuridad.
                    </blockquote>
                    <p className="font-black text-xl" style={{ color: "var(--faro-on-surface)" }}>Pastor David Vance</p>
                    <p className="text-xs font-black uppercase tracking-[0.4em] mt-2" style={{ color: "var(--faro-primary)" }}>Visión 2026</p>
                </div>
            </section>
        </main>
    );
}

