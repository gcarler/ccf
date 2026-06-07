"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Users, MapPin, Clock, Search, Plus, Filter, X, ArrowLeft } from 'lucide-react';

const groupsData = [
  {
    id: 1,
    name: "Conexión Vida - Norte",
    leader: "Carlos & Ana Méndez",
    location: "Col. San Benito",
    schedule: "Jueves, 7:30 PM",
    total_personas: 12,
    category: "Familias",
    image: "https://picsum.photos/seed/grupo1/800/600"
  },
  {
    id: 2,
    name: "Jóvenes Proezas",
    leader: "Josué G.",
    location: "Auditorio CCF",
    schedule: "Sábados, 5:00 PM",
    total_personas: 45,
    category: "Jóvenes",
    image: "https://picsum.photos/seed/grupo2/800/600"
  },
  {
    id: 3,
    name: "Hombres de Honor",
    leader: "David R.",
    location: "Virtual (Zoom)",
    schedule: "Martes, 6:00 AM",
    total_personas: 28,
    category: "Hombres",
    image: "https://picsum.photos/seed/grupo3/800/600"
  }
];

interface DrawerState {
  open: boolean;
  group: (typeof groupsData)[0] | null;
}

export default function CommunityGruposPage() {
  const [drawer, setDrawer] = useState<DrawerState>({ open: false, group: null });

  const openDrawer = (group: (typeof groupsData)[0]) => {
    setDrawer({ open: true, group });
  };

  const closeDrawer = () => {
    setDrawer({ open: false, group: null });
  };

  return (
    <div className="w-full space-y-4 pb-4 animate-in fade-in duration-700">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide text-[10px]">
            <div className="size-2 rounded-full bg-[hsl(var(--primary))] shadow-[0_0_10px_hsl(var(--primary))]"></div>
            Grupos Pequeños
          </div>
          <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] tracking-tighter">Comunidades</h1>
          <p className="text-[hsl(var(--text-secondary))] font-medium">Encuentra un grupo para crecer juntos en fe y amistad.</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] size-4" />
            <input
              placeholder="Buscar grupo..."
              className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg h-8 pl-12 pr-6 text-sm font-medium w-64 focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] focus:border-[hsl(var(--primary))] outline-none transition-all text-[hsl(var(--text-primary))]"
            />
          </div>
          <button className="size-9 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all">
            <Filter size={18} />
          </button>
          <button className="h-8 px-4 rounded-lg bg-[hsl(var(--primary))] text-white font-semibold uppercase tracking-wide text-[10px] flex items-center gap-2 shadow-lg hover:opacity-90 transition-all">
            <Plus size={16} strokeWidth={3} />
            Unirse a un Grupo
          </button>
        </div>
      </header>

      {/* Grid de grupos */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {groupsData.map((group, idx) => (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.1 }}
            key={group.id}
            className="group bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md overflow-hidden hover:border-[hsl(var(--primary)/0.3)] hover:shadow-2xl transition-all shadow-sm flex flex-col cursor-pointer"
            onClick={() => openDrawer(group)}
          >
            <div className="h-48 relative overflow-hidden">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={group.image}
                alt={group.name}
                className="object-cover w-full h-full group-hover:scale-110 transition-transform duration-1000"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[hsl(var(--surface-2))] via-transparent to-transparent"></div>
              <div className="absolute top-4 left-4 h-8 px-4 rounded-full bg-[hsl(var(--primary)/0.2)] backdrop-blur-md border border-[hsl(var(--primary)/0.3)] flex items-center justify-center text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">
                {group.category}
              </div>
            </div>

            <div className="p-4 space-y-3 flex-1 flex flex-col">
              <div className="space-y-1">
                <h3 className="text-base font-bold text-[hsl(var(--text-primary))] tracking-tighter group-hover:text-[hsl(var(--primary))] transition-colors">
                  {group.name}
                </h3>
                <p className="text-[hsl(var(--text-secondary))] text-xs font-bold uppercase tracking-wide">
                  {group.leader}
                </p>
              </div>

              <div className="space-y-3 pt-2">
                <div className="flex items-center gap-3 text-[hsl(var(--text-secondary))] text-xs font-medium">
                  <MapPin size={14} />
                  {group.location}
                </div>
                <div className="flex items-center gap-3 text-[hsl(var(--text-secondary))] text-xs font-medium">
                  <Clock size={14} />
                  {group.schedule}
                </div>
                <div className="flex items-center gap-3 text-[hsl(var(--text-secondary))] text-xs font-medium">
                  <Users size={14} />
                  {group.total_personas} Integrantes
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Drawer lateral (en vez de modal) */}
      {drawer.open && drawer.group && (
        <>
          <div
            className="fixed inset-x-0 bottom-0 top-10 bg-black/40 z-40"
            onClick={closeDrawer}
          />
          <div className="fixed top-10 right-0 h-[calc(100vh-2.5rem)] w-full max-w-xl bg-[hsl(var(--surface-1))] border-l border-[hsl(var(--border))] z-50 shadow-2xl animate-in slide-in-from-right duration-300 overflow-y-auto">
            <div className="p-4 space-y-6">
              <div className="flex items-center justify-between">
                <button
                  onClick={closeDrawer}
                  className="size-8 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-all"
                >
                  <ArrowLeft size={16} />
                </button>
                <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                  Detalles del Grupo
                </span>
                <button
                  onClick={closeDrawer}
                  className="size-8 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-all"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="space-y-4">
                {/* Imagen */}
                <div className="h-48 rounded-md overflow-hidden">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={drawer.group.image}
                    alt={drawer.group.name}
                    className="w-full h-full object-cover"
                  />
                </div>

                {/* Info */}
                <div className="space-y-4">
                  <div>
                    <div className="inline-flex h-6 px-3 rounded-full bg-[hsl(var(--primary)/0.1)] border border-[hsl(var(--primary)/0.2)] items-center text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] mb-2">
                      {drawer.group.category}
                    </div>
                    <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] tracking-tighter">
                      {drawer.group.name}
                    </h2>
                    <p className="text-[hsl(var(--text-secondary))] text-sm font-semibold uppercase tracking-wide">
                      Liderado por {drawer.group.leader}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                      <MapPin size={16} className="text-[hsl(var(--primary))]" />
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Ubicación</p>
                        <p className="text-sm font-medium text-[hsl(var(--text-primary))]">{drawer.group.location}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                      <Clock size={16} className="text-[hsl(var(--primary))]" />
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Horario</p>
                        <p className="text-sm font-medium text-[hsl(var(--text-primary))]">{drawer.group.schedule}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] col-span-2">
                      <Users size={16} className="text-[hsl(var(--primary))]" />
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Integrantes</p>
                        <p className="text-sm font-medium text-[hsl(var(--text-primary))]">{drawer.group.total_personas} personas</p>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 space-y-2">
                    <button className="w-full h-9 rounded-lg bg-[hsl(var(--primary))] text-white font-semibold text-xs uppercase tracking-wide hover:opacity-90 transition-all">
                      Contactar al Líder
                    </button>
                    <button className="w-full h-9 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] font-semibold text-xs uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] transition-all">
                      Solicitar Unirme
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
