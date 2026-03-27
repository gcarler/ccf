"use client";

import Link from "next/link";
import React from "react";

export default function SedesPage() {
    return (
        <main className="pt-[88px] min-h-screen flex flex-col md:flex-row overflow-hidden bg-faro-surface">
            {/* Asider for Locations */}
            <aside className="w-full md:w-[450px] lg:w-[550px] bg-faro-surface-container-lowest flex flex-col h-[calc(100vh-88px)] z-10">
                <div className="p-10 border-b border-white/5">
                    <span className="text-faro-primary font-headline font-bold text-xs tracking-[0.2em] uppercase block mb-4">Nuestra Presencia</span>
                    <h1 className="text-4xl font-headline font-extrabold tracking-tighter text-faro-on-surface mb-6">Nuestras Sedes</h1>
                    <div className="relative group">
                        <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-faro-outline">search</span>
                        <input className="w-full bg-faro-surface-container-highest border-none rounded-[0.5rem] py-4 pl-12 pr-4 text-faro-on-surface placeholder:text-faro-outline focus:ring-1 focus:ring-faro-primary/50 transition-all font-body" placeholder="Buscar ciudad o dirección..." type="text" />
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto hide-scrollbar p-6 space-y-4">
                    {/* Location 1 */}
                    <div className="bg-faro-surface-container-high p-8 rounded-[0.5rem] border border-transparent hover:border-faro-primary/20 transition-all group cursor-pointer">
                        <div className="flex justify-between items-start mb-4">
                            <div className="bg-faro-primary/10 p-3 rounded-[0.25rem]">
                                <span className="material-symbols-outlined text-faro-primary" style={{ fontVariationSettings: "'FILL' 1" }}>church</span>
                            </div>
                            <span className="text-faro-secondary font-label text-[10px] font-bold tracking-widest uppercase bg-faro-secondary/10 px-2 py-1 rounded">Sede Principal</span>
                        </div>
                        <h3 className="text-xl font-headline font-bold text-faro-on-surface mb-2">FARO Central</h3>
                        <p className="text-faro-on-surface-variant font-body text-sm mb-6 leading-relaxed">Av. de la Iluminación 450, Distrito Tecnológico, Ciudad de México.</p>
                        <div className="space-y-3 border-t border-white/5 pt-6">
                            <div className="flex items-center gap-3 text-faro-on-surface-variant text-xs">
                                <span className="material-symbols-outlined text-faro-primary scale-75">schedule</span>
                                <span className="font-medium">Domingos: 09:00 AM • 11:30 AM • 06:00 PM</span>
                            </div>
                            <div className="flex items-center gap-3 text-faro-on-surface-variant text-xs">
                                <span className="material-symbols-outlined text-faro-primary scale-75">event</span>
                                <span className="font-medium">Miércoles: 07:30 PM (Noche de Oración)</span>
                            </div>
                        </div>
                        <button className="mt-8 w-full py-3 rounded-[0.25rem] border border-faro-outline-variant hover:bg-faro-surface-bright text-faro-on-surface text-xs font-bold uppercase tracking-widest transition-all opacity-0 group-hover:opacity-100 transform translate-y-2 group-hover:translate-y-0">
                            Ver Detalles
                        </button>
                    </div>

                    {/* Location 2 */}
                    <div className="bg-faro-surface-container-low p-8 rounded-[0.5rem] border border-transparent hover:border-faro-primary/20 transition-all group cursor-pointer">
                        <div className="bg-faro-surface-container-highest w-fit p-3 rounded-[0.25rem] mb-4">
                            <span className="material-symbols-outlined text-faro-primary">location_city</span>
                        </div>
                        <h3 className="text-xl font-headline font-bold text-faro-on-surface mb-2">FARO Norte</h3>
                        <p className="text-faro-on-surface-variant font-body text-sm mb-6 leading-relaxed">Calle del Resplandor 12, Zona Esmeralda, Monterrey.</p>
                        <div className="space-y-3 border-t border-white/5 pt-6">
                            <div className="flex items-center gap-3 text-faro-on-surface-variant text-xs">
                                <span className="material-symbols-outlined text-faro-outline scale-75">schedule</span>
                                <span className="font-medium">Domingos: 10:00 AM • 01:00 PM</span>
                            </div>
                        </div>
                    </div>

                    {/* Location 3 */}
                    <div className="bg-faro-surface-container-low p-8 rounded-[0.5rem] border border-transparent hover:border-faro-primary/20 transition-all group cursor-pointer">
                        <div className="bg-faro-surface-container-highest w-fit p-3 rounded-[0.25rem] mb-4">
                            <span className="material-symbols-outlined text-faro-primary">apartment</span>
                        </div>
                        <h3 className="text-xl font-headline font-bold text-faro-on-surface mb-2">FARO Poniente</h3>
                        <p className="text-faro-on-surface-variant font-body text-sm mb-6 leading-relaxed">Boulevard de los Guías 889, Santa Fe, Ciudad de México.</p>
                        <div className="space-y-3 border-t border-white/5 pt-6">
                            <div className="flex items-center gap-3 text-faro-on-surface-variant text-xs">
                                <span className="material-symbols-outlined text-faro-outline scale-75">schedule</span>
                                <span className="font-medium">Domingos: 11:00 AM • 05:00 PM</span>
                            </div>
                        </div>
                    </div>
                </div>
            </aside>

            <section className="flex-1 relative bg-faro-surface-container">
                <div className="absolute inset-0 z-0">
                    <div className="w-full h-full bg-[#001134]" style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuAZkRuHHrWj7PB3hROLu3jCW7gPboYcxgpRksnZTuAzufJY2ffGgidnwy-tc16iJOzegkwZ4Su-lQYvfRrbTuvJNEjginKpcyPYnjtLEtFktIYZSdfheLVop3wq_haqLTCDQcF8_SKJnSvcKw4g16JWnHai-_6gMoTSu1K3GndldTBwc3gny45SRUbe09EtlB10MEPar0X64XsFK-MQ_MGlwKAzKXwOSYqo27M9Z0tJFzyT6zSa409d5xfCDP7AGbMLco36f4spci_S')", backgroundSize: "cover", backgroundPosition: "center", filter: "contrast(1.1) brightness(0.6) saturate(0.8)" }}>
                        <div className="absolute inset-0 bg-gradient-to-r from-faro-surface-container-lowest via-transparent to-transparent"></div>
                        <div className="absolute inset-0 bg-[#001134]/40"></div>
                    </div>
                </div>
                <div className="absolute top-1/2 left-1/3 -translate-x-1/2 -translate-y-1/2 z-10">
                    <div className="relative">
                        <div className="absolute inset-0 bg-faro-primary/40 blur-2xl rounded-[0.75rem] animate-pulse"></div>
                        <div className="relative bg-faro-primary text-faro-on-primary p-4 rounded-[0.75rem] shadow-[0_0_50px_rgba(165,200,255,0.4)]">
                            <span className="material-symbols-outlined text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>navigation</span>
                        </div>
                        <div className="absolute top-16 left-1/2 -translate-x-1/2 whitespace-nowrap bg-faro-surface-container-highest/90 backdrop-blur-md px-4 py-2 rounded-[0.25rem] border border-faro-primary/20 shadow-2xl">
                            <p className="text-xs font-headline font-bold text-faro-primary uppercase tracking-widest">Sede Central</p>
                        </div>
                    </div>
                </div>
                <div className="absolute top-1/3 right-1/4 z-10">
                    <div className="relative cursor-pointer group">
                        <div className="absolute inset-0 bg-faro-secondary/20 blur-xl rounded-[0.75rem] group-hover:bg-faro-secondary/40 transition-all"></div>
                        <div className="relative bg-faro-surface-container-high border-2 border-faro-secondary text-faro-secondary p-2 rounded-[0.75rem] shadow-xl">
                            <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>location_on</span>
                        </div>
                    </div>
                </div>
                <div className="absolute bottom-10 right-10 flex flex-col gap-4 z-20">
                    <button className="w-14 h-14 bg-faro-surface-container-highest/80 backdrop-blur-xl border border-white/10 rounded-[0.75rem] flex items-center justify-center text-faro-primary shadow-2xl hover:bg-faro-primary hover:text-faro-on-primary transition-all">
                        <span className="material-symbols-outlined">add</span>
                    </button>
                    <button className="w-14 h-14 bg-faro-surface-container-highest/80 backdrop-blur-xl border border-white/10 rounded-[0.75rem] flex items-center justify-center text-faro-primary shadow-2xl hover:bg-faro-primary hover:text-faro-on-primary transition-all">
                        <span className="material-symbols-outlined">remove</span>
                    </button>
                    <button className="w-14 h-14 bg-faro-primary text-faro-on-primary rounded-[0.75rem] flex items-center justify-center shadow-[0_10px_30px_rgba(165,200,255,0.4)] hover:scale-105 transition-all">
                        <span className="material-symbols-outlined">my_location</span>
                    </button>
                </div>
                <div className="absolute top-10 right-10 z-20 flex gap-4">
                    <div className="bg-faro-surface-container-highest/90 backdrop-blur-xl p-1 rounded-[0.75rem] border border-white/10 flex">
                        <button className="px-6 py-2 rounded-[0.75rem] bg-faro-primary text-faro-on-primary text-[10px] font-bold uppercase tracking-widest transition-all">Mapa</button>
                        <button className="px-6 py-2 rounded-[0.75rem] text-faro-on-surface/60 text-[10px] font-bold uppercase tracking-widest hover:text-faro-on-surface transition-all">Satélite</button>
                    </div>
                </div>
            </section>
        </main>
    );
}
