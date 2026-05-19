"use client";

import React from "react";
import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { PASTORS, type PastorProfile } from "@/lib/data/pastors";
import { useContentBlock } from "@/hooks/useContent";

export default function PastoresPage() {
    const { data: pastorsContent } = useContentBlock("faro_pastors_feed");

    const allPastors: PastorProfile[] = (() => {
        if (pastorsContent?.parsed && typeof pastorsContent.parsed === "object" && !Array.isArray(pastorsContent.parsed)) {
            const parsed = pastorsContent.parsed as Record<string, unknown>;
            if (Array.isArray(parsed.pastors) && (parsed.pastors as PastorProfile[]).length > 0) {
                return parsed.pastors as PastorProfile[];
            }
        }
        if (Array.isArray(pastorsContent?.parsed) && pastorsContent.parsed.length > 0) {
            return pastorsContent.parsed as PastorProfile[];
        }
        return PASTORS;
    })();

    const apostles = allPastors.filter(p => p.category === "apostles");
    const pastors = allPastors.filter(p => p.category === "pastors");

    const containerVariants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: { staggerChildren: 0.1 }
        }
    };

    const cardVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
    };

    return (
        <main className="pt-[120px] pb-24 px-6 md:px-16 lg:px-24 bg-faro-surface min-h-screen">
            <div className="max-w-6xl mx-auto">
                {/* HERO */}
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-20 text-center max-w-3xl mx-auto"
                >
                    <span className="text-xs font-black uppercase tracking-[0.4em] mb-6 block text-faro-primary">
                        Liderazgo
                    </span>
                    <h1 className="text-4xl md:text-6xl font-black mb-8 text-faro-on-background tracking-tight">
                        Nuestro <span className="italic bg-clip-text text-transparent bg-gradient-to-r from-faro-primary to-faro-secondary">Equipo Pastoral</span>
                    </h1>
                    <p className="text-lg text-faro-on-surface-variant leading-relaxed">
                        Conoce a los hombres y mujeres que Dios ha puesto al frente de nuestra casa para guiarnos, enseñarnos y caminar junto a nosotros.
                    </p>
                </motion.div>

                {/* APÓSTOLES */}
                <div className="mb-24">
                    <div className="flex items-center gap-4 mb-10">
                        <h2 className="text-3xl font-black text-faro-on-surface">Apóstoles</h2>
                        <div className="h-px flex-1 bg-faro-outline-variant/30" />
                    </div>
                    
                    <motion.div 
                        variants={containerVariants}
                        initial="hidden"
                        whileInView="visible"
                        viewport={{ once: true, margin: "-50px" }}
                        className="grid grid-cols-1 md:grid-cols-2 gap-8"
                    >
                        {apostles.map(person => (
                            <Link href={`/faro/pastores/${person.slug}`} key={person.id}>
                                <motion.div 
                                    variants={cardVariants}
                                    className="group relative overflow-hidden rounded-[2.5rem] bg-faro-surface-container hover:shadow-2xl transition-all duration-500 cursor-pointer border border-transparent hover:border-faro-primary/20 flex flex-col md:flex-row h-full min-h-[280px]"
                                >
                                    <div className="w-full md:w-2/5 relative min-h-[240px] md:min-h-full">
                                        <Image 
                                            src={person.img} 
                                            alt={person.name} 
                                            fill 
                                            className="object-cover group-hover:scale-105 transition-transform duration-700"
                                        />
                                        <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent md:bg-gradient-to-r md:from-transparent md:to-faro-surface-container" />
                                    </div>
                                    <div className="w-full md:w-3/5 p-8 flex flex-col justify-center">
                                        <span className="text-[10px] font-black uppercase tracking-widest text-faro-primary mb-3">
                                            {person.role}
                                        </span>
                                        <h3 className="text-2xl font-black text-faro-on-surface mb-4 group-hover:text-faro-primary transition-colors">
                                            {person.name}
                                        </h3>
                                        <p className="text-sm text-faro-on-surface-variant line-clamp-3 leading-relaxed mb-6">
                                            {person.description}
                                        </p>
                                        <div className="mt-auto flex items-center gap-2 text-xs font-black uppercase tracking-widest text-faro-secondary group-hover:translate-x-2 transition-transform">
                                            Ver Perfil <ArrowRight size={14} />
                                        </div>
                                    </div>
                                </motion.div>
                            </Link>
                        ))}
                    </motion.div>
                </div>

                {/* PASTORES */}
                <div>
                    <div className="flex items-center gap-4 mb-10">
                        <h2 className="text-3xl font-black text-faro-on-surface">Equipo Pastoral</h2>
                        <div className="h-px flex-1 bg-faro-outline-variant/30" />
                    </div>
                    
                    <motion.div 
                        variants={containerVariants}
                        initial="hidden"
                        whileInView="visible"
                        viewport={{ once: true, margin: "-50px" }}
                        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
                    >
                        {pastors.map(person => (
                            <Link href={`/faro/pastores/${person.slug}`} key={person.id}>
                                <motion.div 
                                    variants={cardVariants}
                                    className="group rounded-3xl overflow-hidden bg-faro-surface-container-low hover:bg-faro-surface-container transition-all hover:-translate-y-1 hover:shadow-xl border border-faro-outline-variant/10 flex flex-col h-full"
                                >
                                    <div className="relative aspect-[4/3] overflow-hidden">
                                        <Image 
                                            src={person.img} 
                                            alt={person.name} 
                                            fill 
                                            className="object-cover group-hover:scale-105 transition-transform duration-700"
                                        />
                                        <div className="absolute inset-0 bg-black/10 group-hover:bg-transparent transition-colors" />
                                    </div>
                                    <div className="p-6 flex flex-col flex-1">
                                        <h3 className="text-xl font-black text-faro-on-surface mb-2 group-hover:text-faro-primary transition-colors">
                                            {person.name}
                                        </h3>
                                        <p className="text-xs font-bold uppercase tracking-widest text-faro-primary/70 mb-4">
                                            {person.role}
                                        </p>
                                        <p className="text-sm text-faro-on-surface-variant line-clamp-3 mb-6 flex-1">
                                            {person.description}
                                        </p>
                                        <div className="flex justify-end">
                                            <div className="w-8 h-8 rounded-full bg-faro-primary-container text-faro-primary flex items-center justify-center group-hover:bg-faro-primary group-hover:text-white transition-colors">
                                                <ArrowRight size={14} />
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            </Link>
                        ))}
                    </motion.div>
                </div>
            </div>
        </main>
    );
}
