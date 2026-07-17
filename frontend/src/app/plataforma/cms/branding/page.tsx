"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Church,
  Image as ImageIcon,
  Loader2,
  Save,
  Trash2,
  Upload,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useSiteBranding } from "@/lib/site-branding";
import { apiFetch } from "@/lib/http";
import { SITE_KEY } from "@/lib/site-config";
import { listCmsThemes, patchCmsTheme } from "@/lib/cms/v2";
import { canEditCms } from "@/lib/cms/permissions";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { toast } from "sonner";

interface CmsMediaItem {
  id: number;
  url: string;
  filename?: string | null;
  mime_type?: string | null;
  alt_text?: string | null;
  section?: string;
}

export default function CmsBrandingPage() {
  const { token, user } = useAuth();
  const canEdit = canEditCms(user?.role);
  const { logoUrl: currentLogoUrl, logoName: currentLogoName } = useSiteBranding();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [logoUrl, setLogoUrl] = useState("");
  const [logoName, setLogoName] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [mediaItems, setMediaItems] = useState<CmsMediaItem[]>([]);
  const [showMediaPicker, setShowMediaPicker] = useState(false);

  // Initialize from current branding
  useEffect(() => {
    setLogoUrl(currentLogoUrl || "");
    setLogoName(currentLogoName || "");
  }, [currentLogoUrl, currentLogoName]);

  // Load media items for picker
  useEffect(() => {
    if (!showMediaPicker || !token) return;
    apiFetch<{ items: CmsMediaItem[]; total: number }>("/cms/media", {
      token,
      cache: "no-store",
    })
      .then((data) => setMediaItems(data?.items || []))
      .catch(() => setMediaItems([]));
  }, [showMediaPicker, token]);

  const handleUpload = useCallback(async (file: File) => {
    if (!token || !canEdit) {
      toast.error("No tienes permisos para editar el branding");
      return;
    }
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("section", "site_logo");
      formData.append("alt_text", logoName || "Logo del sitio");
      const created = await apiFetch<CmsMediaItem>("/cms/media/upload", {
        method: "POST",
        token,
        body: formData,
      });
      if (created?.url) {
        setLogoUrl(created.url);
        toast.success("Logo subido correctamente");
      }
    } catch {
      toast.error("Error al subir el logo");
    } finally {
      setUploading(false);
    }
  }, [token, logoName, canEdit]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
    e.target.value = "";
  };

  const handleSave = async () => {
    if (!token || !canEdit) {
      toast.error("No tienes permisos para guardar el branding");
      return;
    }
    setSaving(true);
    try {
      // Get the active theme for this site
      const themes = await listCmsThemes(SITE_KEY, token);
      const activeTheme = themes?.find((t) => t.is_active) || themes?.[0];
      if (!activeTheme) {
        toast.error("No hay un tema activo para este sitio");
        return;
      }
      const currentTokens = activeTheme.tokens_json || {};
      const updatedTokens = {
        ...currentTokens,
        "--site-logo-url": logoUrl,
        "--site-logo-name": logoName,
      };
      await patchCmsTheme(SITE_KEY, activeTheme.id, { tokens_json: updatedTokens }, token);
      toast.success("Branding guardado correctamente");
    } catch {
      toast.error("Error al guardar el branding");
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveLogo = () => {
    if (!canEdit) {
      toast.error("No tienes permisos para editar el branding");
      return;
    }
    setLogoUrl("");
    toast.success("Logo eliminado (se usará el fallback)");
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[hsl(var(--text-primary))]">Logo & Branding</h1>
          <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">
            Gestiona el logo y nombre que aparece en navbar, sidebar y footer del sitio público.
          </p>
          {!canEdit && (
            <p className="mt-2 text-[10px] font-semibold uppercase tracking-wide text-amber-600">
              Solo lectura: este rol no puede guardar branding.
            </p>
          )}
        </div>
        <button
          onClick={handleSave}
          disabled={saving || !canEdit}
          className="inline-flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] text-white px-4 py-2 text-xs font-semibold uppercase tracking-wide hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          Guardar
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Logo Preview */}
        <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] overflow-hidden">
          <div className="px-4 py-3 border-b border-[hsl(var(--border))]">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
              Logo Actual
            </h2>
          </div>
          <div className="p-6 flex flex-col items-center gap-4">
            {/* Logo preview */}
            <div className="w-32 h-32 rounded-2xl border-2 border-dashed border-[hsl(var(--border))] flex items-center justify-center overflow-hidden bg-[hsl(var(--surface-2))]">
              {logoUrl ? (
                <OptimizedImage
                  src={logoUrl}
                  alt={logoName || "Logo"}
                  width={128}
                  height={128}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="flex flex-col items-center gap-2 text-[hsl(var(--text-secondary))]">
                  <Church size={32} />
                  <span className="text-[10px] font-medium">Sin logo</span>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading || !canEdit}
                className="inline-flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-xs font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] transition-colors disabled:opacity-50"
              >
                {uploading ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />}
                Subir imagen
              </button>
              <button
                onClick={() => setShowMediaPicker(true)}
                disabled={!canEdit}
                className="inline-flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-xs font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
              >
                <ImageIcon size={12} />
                Media Library
              </button>
              {logoUrl && (
                <button
                  onClick={handleRemoveLogo}
                  disabled={!canEdit}
                  className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 transition-colors"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Right: Configuration */}
        <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] overflow-hidden">
          <div className="px-4 py-3 border-b border-[hsl(var(--border))]">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
              Configuración
            </h2>
          </div>
          <div className="p-6 space-y-4">
            {/* Logo URL */}
            <div>
              <label className="block text-xs font-semibold text-[hsl(var(--text-primary))] mb-1.5">
                URL del Logo
              </label>
              <input
                type="text"
                value={logoUrl}
                onChange={(e) => setLogoUrl(e.target.value)}
                placeholder="/api/static/cms/site_logo/..."
                disabled={!canEdit}
                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-xs text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/50"
              />
              <p className="mt-1 text-[10px] text-[hsl(var(--text-secondary))]">
                URL relativa (/api/...) o absoluta (https://...)
              </p>
            </div>

            {/* Logo Name */}
            <div>
              <label className="block text-xs font-semibold text-[hsl(var(--text-primary))] mb-1.5">
                Nombre del Logo
              </label>
              <input
                type="text"
                value={logoName}
                onChange={(e) => setLogoName(e.target.value)}
                placeholder="El Faro"
                disabled={!canEdit}
                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-xs text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/50"
              />
              <p className="mt-1 text-[10px] text-[hsl(var(--text-secondary))]">
                Texto que acompaña al logo en la navegación
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Context Preview */}
      <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] overflow-hidden">
        <div className="px-4 py-3 border-b border-[hsl(var(--border))]">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
            Preview en Contexto
          </h2>
        </div>
        <div className="p-6 space-y-4">
          {/* Navbar preview */}
          <div className="rounded-lg border border-[hsl(var(--border))] bg-white overflow-hidden">
            <div className="flex items-center gap-3 px-4 py-3">
              {logoUrl ? (
                <OptimizedImage src={logoUrl} alt={logoName || "Logo"} width={32} height={32} className="size-8 rounded-lg object-contain" />
              ) : (
                <div className="size-8 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center text-white text-[10px] font-bold">CCF</div>
              )}
              <div>
                <p className="text-[10px] font-black uppercase tracking-[0.25em] text-gray-900">
                  {logoName || "Comunidad Cristiana El Faro"}
                </p>
                <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-gray-500">
                  Plataforma
                </p>
              </div>
            </div>
          </div>

          {/* Sidebar preview */}
          <div className="flex gap-4">
            <div className="w-16 rounded-lg border border-[hsl(var(--border))] bg-white p-2 flex flex-col items-center gap-2">
              <div className="size-10 rounded-lg bg-[hsl(var(--primary))]/10 flex items-center justify-center">
                {logoUrl ? (
                  <OptimizedImage src={logoUrl} alt={logoName || "Logo"} width={24} height={24} className="size-6 rounded object-contain" />
                ) : (
                  <span className="text-[10px] font-bold text-[hsl(var(--primary))]">CCF</span>
                )}
              </div>
            </div>
            <div className="flex-1 rounded-lg border border-[hsl(var(--border))] bg-white p-3">
              <div className="flex items-center gap-2">
                {logoUrl ? (
                  <OptimizedImage src={logoUrl} alt={logoName || "Logo"} width={28} height={28} className="size-7 rounded object-contain" />
                ) : (
                  <div className="size-7 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center text-white text-[10px] font-bold">CCF</div>
                )}
                <div>
                  <p className="text-[10px] font-black uppercase tracking-[0.25em] text-gray-900">
                    {logoName || "El Faro"}
                  </p>
                  <p className="text-[9px] text-gray-500">Plataforma</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Media Picker Modal */}
      {showMediaPicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-2xl max-h-[80vh] bg-white rounded-xl border border-[hsl(var(--border))] shadow-2xl overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border))]">
              <h3 className="text-sm font-bold text-gray-900">Elegir imagen de Media Library</h3>
              <button onClick={() => setShowMediaPicker(false)} className="p-1 rounded hover:bg-gray-100">
                <span className="text-gray-400 text-lg">&times;</span>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {mediaItems.length === 0 ? (
                <p className="text-center text-sm text-gray-400 py-8">No hay imágenes en la media library</p>
              ) : (
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                  {mediaItems.filter((item) => item.mime_type?.startsWith("image/")).map((item) => (
                    <button
                      key={item.id}
                      onClick={() => {
                        setLogoUrl(item.url);
                        setShowMediaPicker(false);
                        toast.success("Logo seleccionado");
                      }}
                      className={`relative aspect-square rounded-lg border-2 overflow-hidden hover:border-[hsl(var(--primary))] transition-colors ${
                        logoUrl === item.url ? "border-[hsl(var(--primary))]" : "border-transparent"
                      }`}
                    >
                      <OptimizedImage
                        src={item.url}
                        alt={item.alt_text || item.filename || "Imagen"}
                        fill
                        sizes="120px"
                        className="object-cover"
                      />
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
