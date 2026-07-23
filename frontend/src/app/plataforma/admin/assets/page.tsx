"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Download, File, FileText, Folder, HardDrive, Image as ImageIcon, Layers, LayoutGrid, List as ListIcon, Loader2, Plus, Search, Trash2, Upload, Video } from "lucide-react";
import clsx from "clsx";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import AdminHero from "@/components/admin/AdminHero";
import AdminShell from "@/components/admin/AdminShell";

type Asset = {
    id: number;
    filename: string;
    url: string;
    type: "image" | "video" | "document";
    sizeBytes: number;
    createdAt?: string;
};

export default function AssetLibrary() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [assets, setAssets] = useState<Asset[]>([]);
    const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");

    const fetchAssets = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<{ items: Asset[]; total: number }>("/cms/media", { token, cache: "no-store", signal });
            setAssets((data?.items || []).map(normalizeAsset));
        } catch {
            setAssets([]);
            addToast("No se pudieron cargar los activos", "error");
        } finally {
            setLoading(false);
        }
    }, [addToast, token]);

    useEffect(() => {
        if (!isAuthenticated) return;
        const controller = new AbortController();
        fetchAssets(controller.signal);
        return () => controller.abort();
    }, [fetchAssets, isAuthenticated]);

    const uploadFiles = async (files: FileList | null) => {
        if (!token || !files?.length) return;
        setUploading(true);
        try {
            for (const file of Array.from(files)) {
                const body = new FormData();
                body.append("file", file);
                body.append("alt_text", file.name);
                await apiFetch("/cms/media/upload", { method: "POST", token, body });
            }
            await fetchAssets();
            addToast("Archivo subido correctamente", "success");
        } catch {
            addToast("No se pudo subir el archivo", "error");
        } finally {
            setUploading(false);
        }
    };

    const deleteAsset = async (asset: Asset) => {
        if (!token) return;
        try {
            await apiFetch(`/cms/media/${asset.id}`, { method: "DELETE", token });
            setAssets((prev) => prev.filter((item) => item.id !== asset.id));
            addToast("Activo eliminado", "success");
        } catch {
            addToast("No se pudo eliminar el activo", "error");
        }
    };

    const filteredAssets = assets.filter((asset) => asset.filename.toLowerCase().includes(searchTerm.toLowerCase()));
    const stats = useMemo(() => {
        const byType = (type: Asset["type"]) => assets.filter((asset) => asset.type === type);
        const sizeOf = (items: Asset[]) => items.reduce((sum, item) => sum + item.sizeBytes, 0);
        const documents = byType("document");
        const images = byType("image");
        const videos = byType("video");
        return {
            documents: { count: documents.length, size: formatBytes(sizeOf(documents)) },
            images: { count: images.length, size: formatBytes(sizeOf(images)) },
            videos: { count: videos.length, size: formatBytes(sizeOf(videos)) },
            total: { count: assets.length, size: formatBytes(sizeOf(assets)) },
        };
    }, [assets]);

    if (!isAuthenticated) return null;

    return (
        <AdminShell breadcrumbs={[{ label: "Recursos", icon: Layers }, { label: "Biblioteca Multimedia", icon: Folder }]}>
            <input ref={fileInputRef} type="file" multiple className="hidden" onChange={(event) => { uploadFiles(event.target.files); event.target.value = ""; }} />
            <AdminHero
                eyebrow="Asset Management"
                title="Gestion de Activos Digitales"
                description="Control del repositorio multimedia institucional con subida, descarga y limpieza de archivos reales."
                tags={["CMS Media", "Upload Real", "Inventario"]}
                watchers={["Media Team", "Creative Director"]}
                primaryAction={{ label: uploading ? "Subiendo..." : "Subir Recurso", icon: uploading ? Loader2 : Upload, onClick: () => fileInputRef.current?.click() }}
                secondaryAction={{ label: "Abrir Medios CMS", icon: Plus, onClick: () => window.location.assign("/plataforma/cms/media") }}
            />

            <div className="space-y-3 pb-4">
                <section className="grid grid-cols-1 gap-3 md:grid-cols-4">
                    <StorageStat label="Documentos" count={`${stats.documents.count} archivos`} size={stats.documents.size} icon={FileText} color="blue" />
                    <StorageStat label="Imagenes" count={`${stats.images.count} archivos`} size={stats.images.size} icon={ImageIcon} color="cyan" />
                    <StorageStat label="Videos" count={`${stats.videos.count} archivos`} size={stats.videos.size} icon={Video} color="emerald" />
                    <StorageStat label="Uso Total" count={`${stats.total.count} archivos`} size={stats.total.size} icon={HardDrive} color="slate" />
                </section>

                <section className="space-y-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 shadow-xl dark:border-white/10 dark:bg-white/5">
                    <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
                        <div className="flex items-center gap-3">
                            <h3 className="text-xl font-semibold uppercase tracking-wide">Explorador de Medios</h3>
                            <div className="flex rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-1.5 dark:border-white/5 dark:bg-white/10">
                                <button onClick={() => setViewMode("grid")} className={clsx("rounded-md p-2.5", viewMode === "grid" ? "bg-[hsl(var(--bg-primary))] text-[hsl(var(--primary))] shadow-md dark:bg-[hsl(var(--primary))] dark:text-white" : "text-[hsl(var(--text-secondary))]")}><LayoutGrid size={20} /></button>
                                <button onClick={() => setViewMode("list")} className={clsx("rounded-md p-2.5", viewMode === "list" ? "bg-[hsl(var(--bg-primary))] text-[hsl(var(--primary))] shadow-md dark:bg-[hsl(var(--primary))] dark:text-white" : "text-[hsl(var(--text-secondary))]")}><ListIcon size={20} /></button>
                            </div>
                        </div>
                        <div className="relative">
                            <input value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Buscar por nombre..." className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-3 text-sm font-bold outline-none md:w-80 dark:border-white/10 dark:bg-white/5" />
                            <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                        </div>
                    </div>

                    {loading ? (
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
                            {[1, 2, 3, 4].map((item) => <div key={item} className="aspect-square animate-pulse rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5" />)}
                        </div>
                    ) : filteredAssets.length === 0 ? (
                        <div className="rounded-lg border border-dashed border-[hsl(var(--border))] p-4 text-center text-sm text-[hsl(var(--text-secondary))] dark:border-white/10">No hay activos para mostrar.</div>
                    ) : (
                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={clsx("grid gap-3", viewMode === "grid" ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5" : "grid-cols-1")}>
                            {filteredAssets.map((asset) => <AssetCard key={asset.id} asset={asset} mode={viewMode} onDelete={() => deleteAsset(asset)} />)}
                        </motion.div>
                    )}
                </section>
            </div>
        </AdminShell>
    );
}

function AssetCard({ asset, mode, onDelete }: { asset: Asset; mode: "grid" | "list"; onDelete: () => void }) {
    const icons = { document: FileText, image: ImageIcon, video: Video };
    const Icon = icons[asset.type] || File;
    const date = asset.createdAt ? new Date(asset.createdAt).toLocaleDateString("es-CO") : "Sin fecha";
    if (mode === "list") {
        return (
            <div className="flex items-center justify-between rounded-lg border border-transparent p-3 transition-all hover:border-[hsl(var(--info)/100%)]/20 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-[hsl(var(--info))]/5">
                <div className="flex items-center gap-3">
                    <div className="flex size-7 items-center justify-center rounded-lg bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-secondary))] shadow-sm dark:bg-white/10"><Icon size={24} /></div>
                    <div>
                        <p className="text-sm font-semibold uppercase text-[hsl(var(--text-primary))] dark:text-white">{asset.filename}</p>
                        <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{formatBytes(asset.sizeBytes)} | {date} | {asset.type}</p>
                    </div>
                </div>
                <div className="flex gap-2">
                    <a href={asset.url} download className="rounded-md bg-[hsl(var(--bg-primary))] p-2.5 text-[hsl(var(--text-secondary))] shadow-sm hover:text-[hsl(var(--primary))] dark:bg-white/10"><Download size={18} /></a>
                    <button onClick={onDelete} className="rounded-md bg-[hsl(var(--bg-primary))] p-2.5 text-[hsl(var(--text-secondary))] shadow-sm hover:text-danger-text dark:bg-white/10"><Trash2 size={18} /></button>
                </div>
            </div>
        );
    }
    return (
        <div className="group relative flex flex-col items-center rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 text-center shadow-sm transition-all hover:-translate-y-1 hover:border-[hsl(var(--info)/100%)]/30 hover:shadow-xl dark:border-white/5 dark:bg-white/5">
            <div className="mb-3 flex aspect-square w-full items-center justify-center rounded-lg bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-secondary))] shadow-inner transition-all group-hover:text-[hsl(var(--primary))] dark:bg-white/5">
                <Icon size={64} strokeWidth={1} />
            </div>
            <h4 className="w-full truncate px-2 text-[13px] font-semibold uppercase text-[hsl(var(--text-primary))] dark:text-white">{asset.filename}</h4>
            <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">{formatBytes(asset.sizeBytes)} | {date}</p>
            <div className="absolute right-4 top-4 flex flex-col gap-2 opacity-0 transition-all group-hover:opacity-100">
                <a href={asset.url} download className="rounded-lg bg-[hsl(var(--bg-primary))] p-3 text-[hsl(var(--text-secondary))] shadow-xl hover:text-[hsl(var(--primary))] dark:bg-[hsl(var(--surface-2))]"><Download size={18} /></a>
                <button onClick={onDelete} className="rounded-lg bg-[hsl(var(--bg-primary))] p-3 text-[hsl(var(--text-secondary))] shadow-xl hover:text-danger-text dark:bg-[hsl(var(--surface-2))]"><Trash2 size={18} /></button>
            </div>
        </div>
    );
}

function StorageStat({ label, count, size, icon: Icon, color }: any) {
    const colors: Record<string, string> = {
        blue: "bg-info-soft text-[hsl(var(--primary))] dark:bg-[hsl(var(--info))]/20",
        cyan: "bg-[hsl(var(--domain-cyan)/10%)] text-[hsl(var(--domain-cyan)/90%)] dark:bg-[hsl(var(--domain-cyan)/20%)]",
        emerald: "bg-success-soft text-success-text dark:bg-[hsl(var(--success))]/20",
        slate: "bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:bg-[hsl(var(--bg-muted))]/20",
    };
    return (
        <div className="space-y-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 shadow-sm dark:border-white/10 dark:bg-white/5">
            <div className={clsx("flex size-7 items-center justify-center rounded-lg", colors[color])}><Icon size={28} /></div>
            <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</p>
                <h4 className="text-xl font-bold tracking-tighter text-[hsl(var(--text-primary))] dark:text-white">{size}</h4>
                <p className="mt-3 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{count}</p>
            </div>
        </div>
    );
}

function normalizeAsset(asset: any): Asset {
    const mime = asset.mime_type || "";
    return {
        id: asset.id,
        filename: asset.filename,
        url: asset.url,
        type: mime.startsWith("image/") ? "image" : mime.startsWith("video/") ? "video" : "document",
        sizeBytes: asset.file_size || 0,
        createdAt: asset.created_at,
    };
}

function formatBytes(bytes: number) {
    if (!bytes) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
