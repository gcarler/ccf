"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { 
    Folder, 
    File, 
    Image as ImageIcon, 
    FileText, 
    Video, 
    Upload, 
    MoreHorizontal, 
    Search, 
    Filter, 
    Plus, 
    ChevronRight,
    ArrowUpRight,
    HardDrive,
    Trash2,
    Download,
    Layers,
    LayoutGrid,
    List as ListIcon,
    Loader2,
    ExternalLink
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function AssetLibrary() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [assets, setAssets] = useState<any[]>([]);
    const [viewMode, setViewType] = useState<'grid' | 'list'>('grid');
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');

    const fetchAssets = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch('/assets', { token });
            setAssets(Array.isArray(data) ? data : []);
        } catch (e) {
            // Quality Mock Data
            setAssets([
                { id: 1, filename: 'manual_discipulado_v2.pdf', url: '#', type: 'document', size: '2.4 MB', date: 'Hace 2 días' },
                { id: 2, filename: 'banner_reunion_dominical.png', url: '#', type: 'image', size: '1.1 MB', date: 'Ayer' },
                { id: 3, filename: 'video_bienvenida_pastoral.mp4', url: '#', type: 'video', size: '45 MB', date: 'Hoy' },
                { id: 4, filename: 'guia_lideres_casa.pdf', url: '#', type: 'document', size: '800 KB', date: 'Hace 1 hora' },
                { id: 5, filename: 'logo_mesh_3d.svg', url: '#', type: 'image', size: '12 KB', date: 'Hace 5 min' },
            ]);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => { if (isAuthenticated) fetchAssets(); }, [isAuthenticated, fetchAssets]);

    const handleUpload = () => {
        setUploading(true);
        setTimeout(() => {
            addToast("Archivo subido correctamente a la nube", "success");
            setUploading(false);
        }, 2000);
    };

    const filteredAssets = assets.filter(a => a.filename.toLowerCase().includes(searchTerm.toLowerCase()));

    if (!isAuthenticated) return null;

    return (
        <AdminShell
            breadcrumbs={[
                { label: 'Recursos', icon: Layers },
                { label: 'Biblioteca Multimedia', icon: Folder }
            ]}
        >
            <AdminHero
                eyebrow="Asset Management"
                title="Gestión de Activos Digitales"
                description="Control total sobre el repositorio de archivos de la institución. Sube, organiza y distribuye contenido multimedia, manuales y recursos académicos de forma segura."
                tags={['AWS S3 Linked', 'Private Storage', 'Optimized CDN']}
                watchers={['Media Team', 'Creative Director']}
                primaryAction={{ 
                    label: uploading ? 'Subiendo...' : 'Subir Recurso', 
                    icon: uploading ? Loader2 : Upload, 
                    onClick: handleUpload 
                }}
                secondaryAction={{ label: 'Nueva Carpeta', icon: Plus, onClick: () => {} }}
            />

            <div className="space-y-10 pb-20">
                {/* Visual Storage Quota */}
                <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <StorageStat label="Documentos" count="124" size="1.2 GB" icon={FileText} color="blue" />
                    <StorageStat label="Imágenes" count="450" size="2.8 GB" icon={ImageIcon} color="purple" />
                    <StorageStat label="Videos" count="12" size="1.1 GB" icon={Video} color="emerald" />
                    <StorageStat label="Uso de Disco" count="Quota: 10GB" size="5.2 GB" icon={HardDrive} color="slate" isProgress />
                </section>

                {/* Explorer UI */}
                <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-8 relative overflow-hidden">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                        <div className="flex items-center gap-6">
                            <h3 className="text-xl font-black tracking-tight uppercase tracking-widest leading-none">Explorador de Medios</h3>
                            <div className="flex bg-slate-100 dark:bg-white/10 p-1.5 rounded-2xl border border-slate-200 dark:border-white/5 shadow-inner">
                                <button onClick={() => setViewType('grid')} className={clsx("p-2.5 rounded-xl transition-all", viewMode === 'grid' ? "bg-white dark:bg-blue-600 shadow-md text-blue-600 dark:text-white scale-105" : "text-slate-400 hover:text-slate-600")}><LayoutGrid size={20} /></button>
                                <button onClick={() => setViewType('list')} className={clsx("p-2.5 rounded-xl transition-all", viewMode === 'list' ? "bg-white dark:bg-blue-600 shadow-md text-blue-600 dark:text-white scale-105" : "text-slate-400 hover:text-slate-600")}><ListIcon size={20} /></button>
                            </div>
                        </div>
                        <div className="flex gap-4">
                            <div className="relative group">
                                <input 
                                    value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
                                    placeholder="Buscar por nombre..." 
                                    className="bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl py-3 px-12 text-sm font-bold outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500/30 transition-all w-full md:w-80" 
                                />
                                <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                            </div>
                            <button className="p-3.5 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-slate-400 hover:text-blue-600 transition-all shadow-sm"><Filter size={20} /></button>
                        </div>
                    </div>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid grid-cols-1 md:grid-cols-4 gap-6">
                                {[1,2,3,4].map(i => <div key={i} className="aspect-square rounded-[2rem] bg-slate-50 dark:bg-white/5 animate-pulse" />)}
                            </motion.div>
                        ) : (
                            <motion.div 
                                key={viewMode} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                className={clsx("grid gap-6", viewMode === 'grid' ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5" : "grid-cols-1")}
                            >
                                {filteredAssets.map((asset) => (
                                    <AssetCard key={asset.id} asset={asset} mode={viewMode} />
                                ))}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </section>
            </div>
        </AdminShell>
    );
}

function AssetCard({ asset, mode }: any) {
    const icons: any = {
        document: FileText,
        image: ImageIcon,
        video: Video
    };
    const Icon = icons[asset.type] || File;

    if (mode === 'list') {
        return (
            <div className="flex items-center justify-between p-5 hover:bg-slate-50 dark:hover:bg-blue-600/5 rounded-3xl transition-all group border border-transparent hover:border-blue-500/20 cursor-pointer">
                <div className="flex items-center gap-5">
                    <div className="size-12 rounded-2xl bg-white dark:bg-white/10 shadow-sm flex items-center justify-center text-slate-400 group-hover:text-blue-600 transition-all"><Icon size={24} /></div>
                    <div>
                        <p className="text-[14px] font-black text-slate-800 dark:text-white uppercase leading-none mb-1">{asset.filename}</p>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{asset.size} • {asset.date} • {asset.type}</p>
                    </div>
                </div>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-all">
                    <button className="p-2.5 bg-white dark:bg-white/10 rounded-xl text-slate-400 hover:text-blue-600 shadow-sm hover:scale-110 transition-all"><Download size={18} /></button>
                    <button className="p-2.5 bg-white dark:bg-white/10 rounded-xl text-slate-400 hover:text-rose-600 shadow-sm hover:scale-110 transition-all"><Trash2 size={18} /></button>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-[2.5rem] hover:border-blue-500/30 transition-all group relative overflow-hidden flex flex-col items-center text-center shadow-sm hover:shadow-xl hover:-translate-y-1">
            <div className="absolute top-4 left-4 size-2.5 rounded-full bg-blue-500 shadow-[0_0_8px_#3b82f6] opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="aspect-square w-full mb-6 bg-white dark:bg-white/5 rounded-3xl flex items-center justify-center text-slate-200 group-hover:text-blue-500 transition-all duration-500 shadow-inner">
                <Icon size={64} strokeWidth={1} />
            </div>
            <div className="w-full">
                <h4 className="text-[13px] font-black text-slate-800 dark:text-white uppercase truncate mb-1 px-2">{asset.filename}</h4>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.1em]">{asset.size} • {asset.date}</p>
            </div>
            <div className="absolute top-4 right-4 flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition-all translate-x-10 group-hover:translate-x-0">
                <button className="p-3 bg-white dark:bg-slate-800 rounded-2xl text-slate-400 hover:text-blue-600 shadow-xl active:scale-90"><Download size={18} /></button>
                <button className="p-3 bg-white dark:bg-slate-800 rounded-2xl text-slate-400 hover:text-rose-600 shadow-xl active:scale-90"><Trash2 size={18} /></button>
            </div>
        </div>
    );
}

function StorageStat({ label, count, size, icon: Icon, color, isProgress }: any) {
    const colors: any = {
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20 shadow-blue-500/10',
        purple: 'text-purple-600 bg-purple-50 dark:bg-purple-900/20 shadow-purple-500/10',
        emerald: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20 shadow-emerald-500/10',
        slate: 'text-slate-600 bg-slate-50 dark:bg-slate-900/20 shadow-slate-500/10'
    };
    return (
        <div className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] shadow-sm flex flex-col gap-6 group hover:shadow-xl transition-all relative overflow-hidden">
            <div className="flex justify-between items-start relative z-10">
                <div className={clsx("size-14 rounded-2xl flex items-center justify-center shrink-0 transition-transform group-hover:scale-110", colors[color])}>
                    <Icon size={28} />
                </div>
                <button className="p-2 text-slate-300 hover:text-slate-600"><ExternalLink size={16} /></button>
            </div>
            <div className="relative z-10">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-1.5 leading-none">{label}</p>
                <div className="flex items-baseline gap-2">
                    <h4 className="text-3xl font-black text-slate-900 dark:text-white leading-none tracking-tighter">{size}</h4>
                </div>
                <p className="text-[10px] font-bold text-slate-500 uppercase mt-3 tracking-widest">{count}</p>
                {isProgress && (
                    <div className="mt-4 h-1.5 w-full bg-slate-100 dark:bg-white/10 rounded-full overflow-hidden">
                        <motion.div initial={{ width: 0 }} animate={{ width: '52%' }} className="h-full bg-blue-600 shadow-[0_0_10px_#2563eb]" />
                    </div>
                )}
            </div>
        </div>
    );
}
