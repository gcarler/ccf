"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  PlayCircle,
  ChevronRight,
  MessageCircle,
  Users,
  BookOpen,
  Church,
  Calendar,
  Sparkles,
  ArrowRight,
  Shield,
  Heart,
  Loader2,
  Video,
  ImageIcon
} from 'lucide-react';
import { apiUrl } from '@/lib/api';
import Navbar from '@/components/Navbar';

interface Announcement {
  id: number;
  title: string;
  content: string;
  image_url?: string;
  category: string;
  created_at: string;
}

interface Sermon {
  id: number;
  title: string;
  preacher: string;
  series?: string;
  thumbnail_url?: string;
  video_url: string;
  date: string;
}

interface PageContent {
  page_key: string;
  title?: string;
  content?: string;
  image_url?: string;
  // Dynamic fields
  subtitle?: string;
  cta_primary?: string;
  cta_secondary?: string;
  impact?: string;
  courses?: string;
}

export default function ChurchDashboardPage() {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [sermons, setSermons] = useState<Sermon[]>([]);
  const [pageContents, setPageContents] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [annRes, serRes, heroRes] = await Promise.all([
          fetch(apiUrl('/announcements/')),
          fetch(apiUrl('/sermons/')),
          fetch(apiUrl('/content/home_hero'))
        ]);

        if (annRes.ok) setAnnouncements(await annRes.json());
        if (serRes.ok) setSermons(await serRes.json());

        if (heroRes.ok) {
          const heroData = await heroRes.json();
          setPageContents(prev => ({
            ...prev,
            home_hero: JSON.parse(heroData.content)
          }));
        }

        // Fetch specific page sections
        const keys = ["home_academy_card", "home_giving_card", "home_community_card", "home_prayer_banner", "home_impact_stats"];
        const fetchedContents: Record<string, any> = {};

        await Promise.all(keys.map(async (key) => {
          try {
            const res = await fetch(apiUrl(`/content/${key}`));
            if (res.ok) {
              const data = await res.json();
              try {
                // Try to parse content if it's JSON
                fetchedContents[key] = { ...data, ...JSON.parse(data.content) };
              } catch {
                fetchedContents[key] = data;
              }
            }
          } catch (e) {
            console.error(`Error fetching page content for ${key}`, e);
          }
        }));

        setPageContents(prev => ({ ...prev, ...fetchedContents }));

      } catch (e) {
        console.error("Error fetching home data", e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="min-h-screen bg-[#07090d] text-slate-200 font-display selection:bg-primary selection:text-white pb-24 lg:pb-0">
      <Navbar />

      <div className="relative pt-16">
        {/* Decorative elements */}
        <div className="fixed top-0 left-0 right-0 h-[50vh] bg-gradient-to-b from-navy-dark via-primary/20 to-transparent pointer-events-none z-0"></div>

        <div className="relative z-10 max-w-[1600px] mx-auto flex flex-col min-h-screen">

          <main className="flex-1 p-8 grid grid-cols-1 lg:grid-cols-12 gap-8">

            <div className="lg:col-span-8 space-y-8">

              <section className="relative aspect-[21/9] w-full overflow-hidden rounded-[3rem] shadow-2xl group border border-white/10">
                <img
                  alt="Live background"
                  className="absolute inset-0 w-full h-full object-cover scale-105 group-hover:scale-110 transition-transform duration-1000"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuBrjwJtgSqjB2-3DcMRRBNqo9Ik9j7RBk6PDRrx5DgRY3Sk3a492jXxHaIbuDDa5QMw_gn_vJZbAedgKwTteyIl-Hk6pdcXJpQR0ld0-Ia8Az-uioBoCyC9XGKIXIOT9QyDDITKVZt_gOz6M_kceOV645QxLDK26eA7oQE1Vgq7RFXNxSFeBQWaaEIpPSoZn_Vabh3HOZkwUXSDhzq5cl_u8aqw7XI5eQpNZyZP5MvCT9f6LunkNKErwfB-gg25MT_2sbBBihPsjoo"
                />
                <div className="absolute inset-0 bg-gradient-to-r from-black/90 via-black/40 to-transparent"></div>

                <div className="absolute inset-0 flex flex-col justify-center p-12 lg:p-20">
                  <div className="max-w-2xl">
                    <h2 className="text-4xl lg:text-7xl font-black text-white mb-6 tracking-tight leading-[1.1]">
                      {pageContents.home_hero?.title || "Transformando Vidas a través de la Palabra"}
                    </h2>
                    <p className="text-lg text-white/70 mb-10 font-medium leading-relaxed max-w-lg">
                      {pageContents.home_hero?.subtitle || "Únete a una comunidad vibrante y moderna en busca de la presencia de Dios."}
                    </p>
                    <div className="flex flex-wrap gap-4">
                      <Link href="/academy" className="px-8 py-4 bg-primary text-white rounded-2xl font-black text-xs uppercase tracking-widest shadow-2xl shadow-primary/40 hover:bg-primary/90 hover:-translate-y-1 transition-all active:scale-95 flex items-center gap-2">
                        {pageContents.home_hero?.cta_primary || "Empezar Ahora"} <ArrowRight size={16} />
                      </Link>
                      <Link href="/sermons" className="px-8 py-4 glass-card-dark text-white rounded-2xl font-black text-xs uppercase tracking-widest border border-white/10 hover:bg-white/10 transition-all flex items-center gap-2">
                        <PlayCircle size={18} /> {pageContents.home_hero?.cta_secondary || "Ver Prédicas"}
                      </Link>
                    </div>
                  </div>
                </div>
              </section>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[
                  {
                    title: pageContents.home_academy_card?.title || 'Academia Faro',
                    icon: 'school',
                    color: 'bg-primary/10 text-primary',
                    desc: pageContents.home_academy_card?.content || 'Formación teológica y ministerial.',
                    link: '/academy'
                  },
                  {
                    title: pageContents.home_giving_card?.title || 'Ofrendar',
                    icon: 'volunteer_activism',
                    color: 'bg-emerald-500/10 text-emerald-500',
                    desc: pageContents.home_giving_card?.content || 'Siembra en el Reino de Dios.',
                    link: '/donate'
                  },
                  {
                    title: pageContents.home_community_card?.title || 'Comunidad',
                    icon: 'groups',
                    color: 'bg-purple-500/10 text-purple-500',
                    desc: pageContents.home_community_card?.content || 'Conéctate con una Casa de Gloria.',
                    link: '/groups'
                  }
                ].map((action, i) => (
                  <Link key={i} href={action.link} className="floating-3d group p-8 rounded-[2.5rem] bg-white/5 dark:bg-slate-800/20 backdrop-blur-xl shadow-xl border border-white/10 hover:border-primary/30 transition-all">
                    <div className={`size-16 rounded-2xl ${action.color} flex items-center justify-center mb-6 shadow-inner`}>
                      <span className="material-symbols-outlined text-4xl">{action.icon}</span>
                    </div>
                    <h3 className="text-xl font-black text-white mb-2">{action.title}</h3>
                    <p className="text-sm text-slate-400 font-medium leading-relaxed">{action.desc}</p>
                  </Link>
                ))}
              </div>

              <section className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-3xl font-black tracking-tighter">Últimas Noticias</h2>
                  <Link href="/sermons" className="text-primary text-xs font-black uppercase tracking-widest hover:underline flex items-center gap-2">
                    Explorar todo <ArrowRight size={16} />
                  </Link>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {loading ? (
                    <div className="col-span-full py-10 flex justify-center"><Loader2 className="animate-spin text-primary" /></div>
                  ) : announcements.length > 0 ? (
                    announcements.slice(0, 2).map(ann => (
                      <div key={ann.id} className="glass-card-dark rounded-[2.5rem] p-6 flex gap-6 hover:border-primary/20 transition-all cursor-pointer">
                        <div className="w-40 h-40 shrink-0 rounded-3xl overflow-hidden bg-slate-800 flex items-center justify-center">
                          {ann.image_url ? (
                            <img className="w-full h-full object-cover" src={ann.image_url} alt="News" />
                          ) : (
                            <ImageIcon className="text-slate-400" size={32} />
                          )}
                        </div>
                        <div className="flex flex-col justify-center">
                          <span className="text-[10px] font-black text-primary uppercase tracking-[0.2em] mb-2">{ann.category}</span>
                          <h3 className="text-xl font-black mb-2 line-clamp-1">{ann.title}</h3>
                          <p className="text-sm text-slate-500 line-clamp-2">{ann.content}</p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="col-span-full p-10 text-center border border-dashed border-white/10 rounded-[2.5rem]">
                      <p className="text-slate-500 text-sm font-bold uppercase tracking-widest">No hay noticias hoy.</p>
                    </div>
                  )}
                </div>
              </section>
            </div>

            <div className="lg:col-span-4 space-y-8">

              <div className="glass-card-dark rounded-[3rem] p-10 shadow-[0_0_50px_rgba(25,115,240,0.1)] border-white/10 relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 group-hover:bg-primary/20 transition-colors"></div>
                <div className="relative z-10 flex flex-col items-center text-center">
                  <div className="mb-6 p-5 rounded-3xl bg-primary text-white shadow-2xl shadow-primary/40">
                    <span className="material-symbols-outlined text-5xl">chat_bubble</span>
                  </div>
                  <h2 className="text-2xl lg:text-3xl font-black tracking-tight mb-4 text-white">
                    {pageContents.home_prayer_banner?.title || "Peticiones de Oración"}
                  </h2>
                  <p className="text-slate-400 text-base font-medium mb-10 leading-relaxed">
                    {pageContents.home_prayer_banner?.content || "¿Podemos orar por ti hoy? Envíanos tu petición y nos uniremos en fe."}
                  </p>
                  <Link href="/testimonials" className="w-full py-5 px-6 bg-primary text-white rounded-2xl font-black text-xs uppercase tracking-[0.2em] shadow-2xl shadow-primary/20 active:scale-95 transition-all hover:bg-primary/90 text-center">
                    Enviar Petición
                  </Link>
                </div>
              </div>

              <div className="glass-card-dark rounded-[2.5rem] p-8 border border-white/5 shadow-xl">
                <div className="flex items-center justify-between mb-8">
                  <h3 className="text-xl font-black tracking-tighter text-white">Prédicas Recientes</h3>
                  <Video size={20} className="text-slate-400" />
                </div>

                <div className="space-y-6">
                  {loading ? (
                    <Loader2 className="animate-spin text-primary mx-auto" />
                  ) : sermons.length > 0 ? (
                    sermons.slice(0, 3).map(ser => (
                      <Link key={ser.id} href="/sermons" className="flex items-center gap-5 group cursor-pointer">
                        <div className="size-14 shrink-0 rounded-2xl bg-slate-900 overflow-hidden border border-transparent group-hover:border-primary/30 transition-all flex items-center justify-center">
                          {ser.thumbnail_url ? (
                            <img src={ser.thumbnail_url} className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-opacity" alt="thumb" />
                          ) : (
                            <Video size={20} className="text-slate-600" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-bold text-white group-hover:text-primary transition-colors truncate">{ser.title}</h4>
                          <p className="text-[10px] font-medium text-slate-500">{ser.preacher}</p>
                        </div>
                        <ChevronRight size={16} className="text-slate-300 group-hover:text-primary group-hover:translate-x-1 transition-all" />
                      </Link>
                    ))
                  ) : (
                    <p className="text-center text-xs font-bold text-slate-500 uppercase">Sin prédicas recientes.</p>
                  )}
                </div>

                <Link href="/sermons" className="block w-full mt-10 py-4 border border-white/10 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-white/5 transition-all text-center">
                  Explorar Biblioteca
                </Link>
              </div>

              <div className="p-8 rounded-[2.5rem] bg-gradient-to-br from-primary/10 to-slate-900 border border-white/5 text-white shadow-2xl relative overflow-hidden group">
                <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_bottom_right,_var(--tw-gradient-stops))] from-primary via-transparent to-transparent group-hover:opacity-20 transition-opacity"></div>
                <div className="relative z-10 space-y-6">
                  <div className="flex items-center gap-3 text-primary">
                    <Sparkles size={20} />
                    <span className="text-[10px] font-black uppercase tracking-widest">Impacto Ministerial</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-2xl bg-white/5 border border-white/5 text-center">
                      <p className="text-[8px] font-black text-slate-500 uppercase tracking-widest mb-1">Cursos</p>
                      <p className="text-2xl font-black">
                        {pageContents.home_impact_stats?.courses || "42"}
                      </p>
                    </div>
                    <div className="p-4 rounded-2xl bg-white/5 border border-white/5 text-center">
                      <p className="text-[8px] font-black text-slate-500 uppercase tracking-widest mb-1">Impacto</p>
                      <p className="text-2xl font-black">
                        {pageContents.home_impact_stats?.impact || "2.4k"}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </main>

          <footer className="mt-auto border-t border-white/5 bg-black/20 backdrop-blur-md py-10 px-8">
            <div className="flex flex-col md:flex-row justify-between items-center gap-8">
              <div className="flex items-center gap-3">
                <Shield size={24} className="text-primary" />
                <span className="text-sm font-black uppercase tracking-[0.2em] text-slate-500">© 2026 Comunidad Faro</span>
              </div>
              <div className="flex gap-10">
                <Link href="/privacy" className="text-[10px] font-black uppercase tracking-widest text-slate-500 hover:text-primary transition-colors">Privacidad</Link>
                <Link href="/terms" className="text-[10px] font-black uppercase tracking-widest text-slate-500 hover:text-primary transition-colors">Términos</Link>
                <Link href="/support" className="text-[10px] font-black uppercase tracking-widest text-slate-500 hover:text-primary transition-colors">Soporte</Link>
                <Link href="/donate" className="text-[10px] font-black uppercase tracking-widest text-slate-500 hover:text-primary transition-colors">Donaciones</Link>
              </div>
              <div className="flex gap-4">
                <button className="size-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-primary transition-all group border border-white/5">
                  <Heart size={18} className="text-slate-400 group-hover:text-white" />
                </button>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
