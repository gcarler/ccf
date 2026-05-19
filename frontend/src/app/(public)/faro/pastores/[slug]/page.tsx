"use client";

"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Instagram, Facebook, Mail } from "lucide-react";
import { getPastorBySlug, type PastorProfile } from "@/lib/data/pastors";
import { notFound } from "next/navigation";
import { apiFetch } from "@/lib/http";

export default function PastorProfilePage({ params }: { params: Promise<{ slug: string }> }) {
    const { slug } = React.use(params);
    const [cmsPastors, setCmsPastors] = useState<PastorProfile[] | null>(null);

    useEffect(() => {
        apiFetch<{ parsed?: PastorProfile[] }>("/content/faro_pastors_feed")
            .then((data) => {
                if (data?.parsed && Array.isArray(data.parsed)) {
                    setCmsPastors(data.parsed as PastorProfile[]);
                }
            })
            .catch(() => setCmsPastors(null));
    }, []);

    const pastor = cmsPastors?.find((p) => p.slug === slug) || getPastorBySlug(slug);

    if (!pastor) {
        notFound();
    }

    return (
        <main className="min-h-screen bg-faro-surface pt-[88px]">
            {/* HERO SECTION */}
            <section className="relative h-[60vh] md:h-[70vh] w-full overflow-hidden">
                <Image 
                    src={pastor.img} 
                    alt={pastor.name} 
                    fill 
                    className="object-cover"
                    priority
                />
                <div className="absolute inset-0 bg-gradient-to-t from-faro-surface via-faro-surface/80 to-transparent" />
                <div className="absolute inset-0 bg-gradient-to-r from-faro-surface/90 to-transparent" />
                
                <div className="absolute inset-0 flex items-end">
                    <div className="max-w-6xl mx-auto w-full px-6 md:px-16 lg:px-24 pb-20">
                        <Link 
                            href="/faro/pastores" 
                            className="inline-flex items-center gap-2 text-faro-primary font-black text-[10px] uppercase tracking-widest hover:-translate-x-2 transition-transform mb-8 bg-faro-primary-container px-4 py-2 rounded-full"
                        >
                            <ArrowLeft size={14} /> Volver a Liderazgo
                        </Link>
                        <motion.div
                            initial={{ opacity: 0, y: 30 }}
                            animate={{ opacity: 1, y: 0 }}
                        >
                            <span className="text-sm font-black uppercase tracking-[0.4em] text-faro-primary mb-4 block">
                                {pastor.role}
                            </span>
                            <h1 className="text-5xl md:text-7xl font-black text-faro-on-background tracking-tighter mb-6">
                                {pastor.name}
                            </h1>
                            <div className="flex gap-4">
                                <a href="https://instagram.com/comunidadfaro" target="_blank" rel="noopener noreferrer" className="w-10 h-10 rounded-full bg-faro-surface-container-high border border-faro-outline-variant/20 flex items-center justify-center text-faro-on-surface-variant hover:text-faro-primary hover:border-faro-primary transition-colors">
                                    <Instagram size={18} />
                                </a>
                                <a href="https://facebook.com/comunidadfaro" target="_blank" rel="noopener noreferrer" className="w-10 h-10 rounded-full bg-faro-surface-container-high border border-faro-outline-variant/20 flex items-center justify-center text-faro-on-surface-variant hover:text-faro-primary hover:border-faro-primary transition-colors">
                                    <Facebook size={18} />
                                </a>
                                <a href="mailto:hola@comunidadfaro.org" className="w-10 h-10 rounded-full bg-faro-surface-container-high border border-faro-outline-variant/20 flex items-center justify-center text-faro-on-surface-variant hover:text-faro-primary hover:border-faro-primary transition-colors">
                                    <Mail size={18} />
                                </a>
                            </div>
                        </motion.div>
                    </div>
                </div>
            </section>

            {/* CONTENT SECTION */}
            <section className="py-24 px-6 md:px-16 lg:px-24">
                <div className="max-w-4xl mx-auto grid md:grid-cols-3 gap-16">
                    <div className="md:col-span-2">
                        <h2 className="text-3xl font-black text-faro-on-surface mb-8">Biografía</h2>
                        <div className="prose prose-lg dark:prose-invert prose-p:text-faro-on-surface-variant prose-p:leading-relaxed">
                            <p className="text-xl font-medium text-faro-on-surface mb-6">
                                {pastor.description}
                            </p>
                            <p>
                                Con una trayectoria marcada por el servicio y la pasión por las almas, 
                                {pastor.name.includes(" y ") ? " han dedicado su vida" : " ha dedicado su vida"} al desarrollo de una comunidad fundamentada 
                                en el amor, la gracia y el poder de Dios. Su enfoque no solo se centra en la 
                                enseñanza dentro de la iglesia, sino en equipar a los creyentes para que sean 
                                luz en cada área de la sociedad.
                            </p>
                            <p>
                                A través de su ministerio, {pastor.name.includes(" y ") ? "han inspirado" : "ha inspirado"} a cientos de personas a descubrir su 
                                propósito y a caminar en la plenitud que ofrece una relación personal con Jesús.
                            </p>
                        </div>
                    </div>
                    
                    <div className="md:col-span-1 space-y-8">
                        <div className="bg-faro-surface-container rounded-[2rem] p-8 border border-faro-outline-variant/10">
                            <h3 className="text-xl font-black text-faro-on-surface mb-6">Información</h3>
                            <ul className="space-y-6">
                                <li>
                                    <p className="text-[10px] font-black uppercase tracking-widest text-faro-primary mb-1">Rol Ministerial</p>
                                    <p className="text-faro-on-surface font-bold">{pastor.role}</p>
                                </li>
                                <li>
                                    <p className="text-[10px] font-black uppercase tracking-widest text-faro-primary mb-1">Ministerio</p>
                                    <p className="text-faro-on-surface font-bold">Comunidad Faro</p>
                                </li>
                            </ul>
                        </div>
                        
                        <div className="bg-gradient-to-br from-faro-primary to-faro-secondary rounded-[2rem] p-8 text-white text-center">
                            <h3 className="text-xl font-black mb-4">Conéctate</h3>
                            <p className="text-sm opacity-90 mb-6">Únete a nosotros este domingo y recibe una palabra que iluminará tu semana.</p>
                            <Link href="/faro/sedes" className="inline-block bg-white text-faro-primary font-black text-[10px] uppercase tracking-widest px-6 py-3 rounded-xl hover:scale-105 transition-transform">
                                Ver Horarios
                            </Link>
                        </div>
                    </div>
                </div>
            </section>
        </main>
    );
}
