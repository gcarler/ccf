"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { SITE_KEY } from "@/lib/site-config";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mail,
  Plus,
  Search,
  Edit2,
  Trash2,
  Globe,
  Loader2,
  Send,
  Users,
  Upload,
  Calendar,
  CheckCircle2,
  XCircle,
  FileText,
  AlertTriangle,
  X,
  UserPlus,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import SidePanel from "@/components/ui/SidePanel";
import RichEditor from "@/components/cms/RichEditor";
import clsx from "clsx";
import {
  createCmsNewsletter,
  createCmsSubscriber,
  deleteCmsNewsletter,
  deleteCmsSubscriber,
  importCmsSubscribers,
  listCmsNewsletters,
  listCmsSites,
  listCmsSubscribers,
  patchCmsNewsletter,
  patchCmsSubscriber,
  sendCmsNewsletter,
} from "@/lib/cms/v2";
import { CmsNewsletter, CmsSite, CmsSubscriber } from "@/types/cms-v2";
import { canEditCms } from "@/lib/cms/permissions";

type ActiveTab = "campaigns" | "subscribers";

export default function CmsNewsletterManagement() {
  const { token, user } = useAuth();
  const [activeTab, setActiveTab] = useState<ActiveTab>("campaigns");
  const [siteKey, setSiteKey] = useState(SITE_KEY);
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [newsletters, setNewsletters] = useState<CmsNewsletter[]>([]);
  const [subscribers, setSubscribers] = useState<CmsSubscriber[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  // Campaign Drawer / SidePanel State
  const [isCampaignDrawerOpen, setIsCampaignDrawerOpen] = useState(false);
  const [editingNewsletter, setEditingNewsletter] = useState<CmsNewsletter | null>(null);
  const [savingCampaign, setSavingCampaign] = useState(false);

  // Campaign Form State
  const [campaignName, setCampaignName] = useState("");
  const [campaignSubject, setCampaignSubject] = useState("");
  const [campaignContentHtml, setCampaignContentHtml] = useState("");
  const [campaignStatus, setCampaignStatus] = useState<"draft" | "scheduled" | "sent">("draft");
  const [campaignScheduledAt, setCampaignScheduledAt] = useState("");

  // Send Confirmation Modal State
  const [sendingNewsletter, setSendingNewsletter] = useState<CmsNewsletter | null>(null);
  const [isSending, setIsSending] = useState(false);

  // Delete Campaign Modal State
  const [pendingDeleteNewsletter, setPendingDeleteNewsletter] = useState<CmsNewsletter | null>(null);
  const [deletingNewsletter, setDeletingNewsletter] = useState(false);

  // Add Subscriber Modal State
  const [isSubscriberModalOpen, setIsSubscriberModalOpen] = useState(false);
  const [subscriberEmail, setSubscriberEmail] = useState("");
  const [subscriberName, setSubscriberName] = useState("");
  const [savingSubscriber, setSavingSubscriber] = useState(false);

  // Import CSV Modal State
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [csvContent, setCsvContent] = useState("");
  const [importing, setImporting] = useState(false);

  // Delete Subscriber Modal State
  const [pendingDeleteSubscriber, setPendingDeleteSubscriber] = useState<CmsSubscriber | null>(null);
  const [deletingSubscriber, setDeletingSubscriber] = useState(false);

  const canEdit = canEditCms(user?.role);

  const fetchData = useCallback(async (targetSite: string) => {
    if (!token) {
      setLoading(false);
      setNewsletters([]);
      setSubscribers([]);
      setError("Debes iniciar sesión para gestionar boletines.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [sitesData, newslettersData, subscribersData] = await Promise.all([
        listCmsSites(token).catch(() => []),
        listCmsNewsletters(targetSite, token).catch(() => []),
        listCmsSubscribers(targetSite, token).catch(() => []),
      ]);
      setSites(sitesData);
      setNewsletters(newslettersData);
      setSubscribers(subscribersData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al cargar datos de boletines";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData(siteKey);
  }, [fetchData, siteKey]);

  // Active Subscribers Count
  const activeSubscribersCount = useMemo(() => {
    return subscribers.filter((s) => s.is_active).length;
  }, [subscribers]);

  // Filtered Lists
  const filteredNewsletters = useMemo(() => {
    if (!search.trim()) return newsletters;
    const term = search.toLowerCase();
    return newsletters.filter(
      (n) => n.name.toLowerCase().includes(term) || n.subject.toLowerCase().includes(term)
    );
  }, [newsletters, search]);

  const filteredSubscribers = useMemo(() => {
    if (!search.trim()) return subscribers;
    const term = search.toLowerCase();
    return subscribers.filter(
      (s) => s.email.toLowerCase().includes(term) || (s.name && s.name.toLowerCase().includes(term))
    );
  }, [subscribers, search]);

  // Reset Campaign Form
  const openNewCampaign = () => {
    setEditingNewsletter(null);
    setCampaignName("");
    setCampaignSubject("");
    setCampaignContentHtml("");
    setCampaignStatus("draft");
    setCampaignScheduledAt("");
    setIsCampaignDrawerOpen(true);
  };

  const openEditCampaign = (newsletter: CmsNewsletter) => {
    setEditingNewsletter(newsletter);
    setCampaignName(newsletter.name);
    setCampaignSubject(newsletter.subject);
    setCampaignContentHtml(newsletter.content_html);
    setCampaignStatus((newsletter.status as "draft" | "scheduled" | "sent") || "draft");
    setCampaignScheduledAt(
      newsletter.scheduled_at ? new Date(newsletter.scheduled_at).toISOString().slice(0, 16) : ""
    );
    setIsCampaignDrawerOpen(true);
  };

  // Save Campaign
  const handleSaveCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!campaignName.trim() || !campaignSubject.trim() || !campaignContentHtml.trim()) {
      toast.error("Por favor completa el nombre, asunto y contenido HTML de la campaña.");
      return;
    }
    setSavingCampaign(true);
    try {
      const payload = {
        name: campaignName.trim(),
        subject: campaignSubject.trim(),
        content_html: campaignContentHtml,
        status: campaignStatus,
        scheduled_at: campaignScheduledAt ? new Date(campaignScheduledAt).toISOString() : null,
      };

      if (editingNewsletter) {
        const updated = await patchCmsNewsletter(siteKey, editingNewsletter.id, payload, token);
        setNewsletters((prev) => prev.map((n) => (n.id === updated.id ? updated : n)));
        toast.success("Boletín actualizado exitosamente.");
      } else {
        const created = await createCmsNewsletter(siteKey, payload, token);
        setNewsletters((prev) => [created, ...prev]);
        toast.success("Boletín creado exitosamente.");
      }
      setIsCampaignDrawerOpen(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al guardar la campaña";
      toast.error(msg);
    } finally {
      setSavingCampaign(false);
    }
  };

  // Send Now Handler
  const handleConfirmSend = async () => {
    if (!sendingNewsletter) return;
    setIsSending(true);
    try {
      const updated = await sendCmsNewsletter(siteKey, sendingNewsletter.id, token);
      setNewsletters((prev) => prev.map((n) => (n.id === updated.id ? updated : n)));
      toast.success(`Boletín "${updated.name}" enviado a ${updated.recipient_count} suscriptores.`);
      setSendingNewsletter(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al enviar el boletín";
      toast.error(msg);
    } finally {
      setIsSending(false);
    }
  };

  // Delete Campaign Handler
  const handleConfirmDeleteNewsletter = async () => {
    if (!pendingDeleteNewsletter) return;
    setDeletingNewsletter(true);
    try {
      await deleteCmsNewsletter(siteKey, pendingDeleteNewsletter.id, token);
      setNewsletters((prev) => prev.filter((n) => n.id !== pendingDeleteNewsletter.id));
      toast.success("Boletín eliminado correctamente.");
      setPendingDeleteNewsletter(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al eliminar el boletín";
      toast.error(msg);
    } finally {
      setDeletingNewsletter(false);
    }
  };

  // Add Manual Subscriber Handler
  const handleAddSubscriber = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subscriberEmail.trim() || !subscriberEmail.includes("@")) {
      toast.error("Ingresa una dirección de correo electrónico válida.");
      return;
    }
    setSavingSubscriber(true);
    try {
      const created = await createCmsSubscriber(
        siteKey,
        { email: subscriberEmail.trim().toLowerCase(), name: subscriberName.trim() || null, is_active: true, source: "manual" },
        token
      );
      setSubscribers((prev) => {
        const idx = prev.findIndex((s) => s.id === created.id);
        if (idx >= 0) {
          const updated = [...prev];
          updated[idx] = created;
          return updated;
        }
        return [created, ...prev];
      });
      toast.success("Suscriptor agregado correctamente.");
      setIsSubscriberModalOpen(false);
      setSubscriberEmail("");
      setSubscriberName("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al agregar suscriptor";
      toast.error(msg);
    } finally {
      setSavingSubscriber(false);
    }
  };

  // Toggle Subscriber Active State
  const handleToggleSubscriberActive = async (subscriber: CmsSubscriber) => {
    const newActiveState = !subscriber.is_active;
    try {
      const updated = await patchCmsSubscriber(
        siteKey,
        subscriber.id,
        { is_active: newActiveState },
        token
      );
      setSubscribers((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
      toast.success(newActiveState ? "Suscriptor activado." : "Suscriptor desactivado.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al cambiar estado del suscriptor";
      toast.error(msg);
    }
  };

  // Delete Subscriber Handler
  const handleConfirmDeleteSubscriber = async () => {
    if (!pendingDeleteSubscriber) return;
    setDeletingSubscriber(true);
    try {
      await deleteCmsSubscriber(siteKey, pendingDeleteSubscriber.id, token);
      setSubscribers((prev) => prev.filter((s) => s.id !== pendingDeleteSubscriber.id));
      toast.success("Suscriptor eliminado correctamente.");
      setPendingDeleteSubscriber(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al eliminar el suscriptor";
      toast.error(msg);
    } finally {
      setDeletingSubscriber(false);
    }
  };

  // Bulk Import Handler
  const handleImportCsv = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvContent.trim()) {
      toast.error("Por favor proporciona el contenido CSV o la lista de correos.");
      return;
    }
    setImporting(true);
    try {
      const result = await importCmsSubscribers(siteKey, { csv_content: csvContent }, token);
      toast.success(`Importación completada: ${result.imported_count} suscriptores procesados.`);
      setIsImportModalOpen(false);
      setCsvContent("");
      // Refresh subscribers list
      const freshSubscribers = await listCmsSubscribers(siteKey, token);
      setSubscribers(freshSubscribers);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error durante la importación CSV";
      toast.error(msg);
    } finally {
      setImporting(false);
    }
  };

  // CSV File Reader Helper
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      if (text) setCsvContent(text);
    };
    reader.readAsText(file);
  };

  const getStatusBadge = (statusStr: string) => {
    switch (statusStr) {
      case "sent":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 size={12} /> Enviado
          </span>
        );
      case "scheduled":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
            <Calendar size={12} /> Programado
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20">
            <FileText size={12} /> Borrador
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] p-4 md:p-6 space-y-6">
      {/* Top Header & Context Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[hsl(var(--border))] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Mail className="w-6 h-6 text-[hsl(var(--primary))]" />
            <h1 className="text-2xl font-bold tracking-tight">Newsletter & Email Marketing</h1>
          </div>
          <p className="text-sm text-[hsl(var(--text-secondary))] mt-1">
            Gestiona campañas de correo electrónico y listas de suscriptores para la iglesia.
          </p>
        </div>

        {/* Site Selector & Tabs */}
        <div className="flex items-center gap-3">
          {sites.length > 1 && (
            <div className="flex items-center gap-2 bg-[hsl(var(--surface-1))] px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] text-sm">
              <Globe size={14} className="text-[hsl(var(--text-secondary))]" />
              <select
                value={siteKey}
                onChange={(e) => setSiteKey(e.target.value)}
                className="bg-transparent border-none text-sm font-medium focus:outline-none cursor-pointer"
              >
                {sites.map((s) => (
                  <option key={s.id} value={s.site_key}>
                    {s.name} ({s.site_key})
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={() => fetchData(siteKey)}
            disabled={loading}
            className="p-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] rounded-lg hover:bg-[hsl(var(--surface-1))] transition-colors"
            title="Recargar datos"
          >
            <RefreshCw size={16} className={clsx(loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Tabs Navigation Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 bg-[hsl(var(--surface-1))] p-1 rounded-xl border border-[hsl(var(--border))]">
          <button
            onClick={() => setActiveTab("campaigns")}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all",
              activeTab === "campaigns"
                ? "bg-[hsl(var(--bg-primary))] text-[hsl(var(--primary))] shadow-sm"
                : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
            )}
          >
            <Mail size={16} />
            <span>Campañas</span>
            <span className="ml-1 rounded-full bg-[hsl(var(--surface-2))] px-2 py-0.5 text-xs font-semibold">
              {newsletters.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("subscribers")}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all",
              activeTab === "subscribers"
                ? "bg-[hsl(var(--bg-primary))] text-[hsl(var(--primary))] shadow-sm"
                : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
            )}
          >
            <Users size={16} />
            <span>Suscriptores</span>
            <span className="ml-1 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-2 py-0.5 text-xs font-semibold">
              {activeSubscribersCount} activos
            </span>
          </button>
        </div>

        {/* Action Buttons Toolbar */}
        <div className="flex items-center gap-3">
          <div className="relative min-w-[220px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--text-secondary))]" />
            <input
              type="text"
              placeholder={activeTab === "campaigns" ? "Buscar campañas..." : "Buscar por correo o nombre..."}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-sm rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            />
          </div>

          {canEdit && activeTab === "campaigns" && (
            <button
              onClick={openNewCampaign}
              className="flex items-center gap-2 bg-[hsl(var(--primary))] text-white px-4 py-2 rounded-lg text-sm font-medium hover:opacity-90 transition-all shadow-sm"
            >
              <Plus size={16} />
              <span>Crear Campaña</span>
            </button>
          )}

          {canEdit && activeTab === "subscribers" && (
            <>
              <button
                onClick={() => setIsSubscriberModalOpen(true)}
                className="flex items-center gap-2 bg-[hsl(var(--primary))] text-white px-3.5 py-2 rounded-lg text-sm font-medium hover:opacity-90 transition-all shadow-sm"
              >
                <UserPlus size={16} />
                <span>+ Agregar</span>
              </button>
              <button
                onClick={() => setIsImportModalOpen(true)}
                className="flex items-center gap-2 bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] border border-[hsl(var(--border))] px-3.5 py-2 rounded-lg text-sm font-medium hover:bg-[hsl(var(--surface-2))] transition-all"
              >
                <Upload size={16} />
                <span>Importar CSV</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="h-44 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] animate-pulse p-4 flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="h-5 w-2/3 bg-[hsl(var(--surface-2))] rounded" />
                <div className="h-4 w-full bg-[hsl(var(--surface-2))] rounded" />
              </div>
              <div className="h-8 w-1/3 bg-[hsl(var(--surface-2))] rounded" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="p-8 text-center bg-red-500/10 border border-red-500/20 rounded-xl text-red-600 dark:text-red-400 space-y-2">
          <AlertTriangle size={32} className="mx-auto" />
          <p className="font-semibold">{error}</p>
          <button
            onClick={() => fetchData(siteKey)}
            className="text-xs underline hover:opacity-80"
          >
            Reintentar
          </button>
        </div>
      ) : activeTab === "campaigns" ? (
        /* Tab Campañas Content */
        filteredNewsletters.length === 0 ? (
          <div className="p-12 text-center bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-2xl space-y-3">
            <Mail size={40} className="mx-auto text-[hsl(var(--text-secondary))] opacity-60" />
            <h3 className="text-lg font-semibold">No se encontraron campañas</h3>
            <p className="text-sm text-[hsl(var(--text-secondary))] max-w-md mx-auto">
              {search
                ? "No hay boletines que coincidan con el término de búsqueda."
                : "Crea tu primera campaña de correo para comunicarte con la comunidad."}
            </p>
            {canEdit && !search && (
              <button
                onClick={openNewCampaign}
                className="mt-2 inline-flex items-center gap-2 bg-[hsl(var(--primary))] text-white px-4 py-2 rounded-lg text-sm font-medium hover:opacity-90 transition-all"
              >
                <Plus size={16} /> Crear Campaña
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredNewsletters.map((newsletter) => (
              <div
                key={newsletter.id}
                className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-xl p-5 flex flex-col justify-between hover:border-[hsl(var(--primary))] transition-all shadow-sm group"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-bold text-base line-clamp-1 group-hover:text-[hsl(var(--primary))] transition-colors">
                      {newsletter.name}
                    </h3>
                    {getStatusBadge(newsletter.status)}
                  </div>

                  <p className="text-sm text-[hsl(var(--text-secondary))] font-medium line-clamp-1">
                    <span className="text-[hsl(var(--text-primary))] font-semibold">Asunto:</span>{" "}
                    {newsletter.subject}
                  </p>

                  <div className="text-xs text-[hsl(var(--text-secondary))] space-y-1 bg-[hsl(var(--surface-2))] p-2.5 rounded-lg border border-[hsl(var(--border))]">
                    <div className="flex items-center justify-between">
                      <span>Destinatarios:</span>
                      <span className="font-semibold text-[hsl(var(--text-primary))]">
                        {newsletter.recipient_count} suscriptores
                      </span>
                    </div>
                    {newsletter.sent_at ? (
                      <div className="flex items-center justify-between">
                        <span>Enviado el:</span>
                        <span>{new Date(newsletter.sent_at).toLocaleDateString()}</span>
                      </div>
                    ) : newsletter.scheduled_at ? (
                      <div className="flex items-center justify-between">
                        <span>Programado:</span>
                        <span>{new Date(newsletter.scheduled_at).toLocaleString()}</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <span>Creado el:</span>
                        <span>{new Date(newsletter.created_at).toLocaleDateString()}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-4 border-t border-[hsl(var(--border))] mt-4 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1">
                    {canEdit && (
                      <button
                        onClick={() => openEditCampaign(newsletter)}
                        className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] rounded-lg transition-colors"
                        title="Editar campaña"
                      >
                        <Edit2 size={16} />
                      </button>
                    )}
                    {canEdit && (
                      <button
                        onClick={() => setPendingDeleteNewsletter(newsletter)}
                        className="p-1.5 text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                        title="Eliminar campaña"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>

                  {canEdit && (
                    <button
                      onClick={() => setSendingNewsletter(newsletter)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[hsl(var(--primary))] text-white hover:opacity-90 transition-all"
                    >
                      <Send size={14} />
                      <span>Enviar ahora</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        /* Tab Suscriptores Content */
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-[hsl(var(--surface-1))] p-4 rounded-xl border border-[hsl(var(--border))]">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-lg">
                <Users size={20} />
              </div>
              <div>
                <p className="text-xs text-[hsl(var(--text-secondary))] font-medium uppercase tracking-wider">
                  Total Suscriptores Activos
                </p>
                <p className="text-xl font-bold text-[hsl(var(--text-primary))]">
                  {activeSubscribersCount} de {subscribers.length} totales
                </p>
              </div>
            </div>
          </div>

          {filteredSubscribers.length === 0 ? (
            <div className="p-12 text-center bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-2xl space-y-3">
              <Users size={40} className="mx-auto text-[hsl(var(--text-secondary))] opacity-60" />
              <h3 className="text-lg font-semibold">No se encontraron suscriptores</h3>
              <p className="text-sm text-[hsl(var(--text-secondary))] max-w-md mx-auto">
                {search
                  ? "No hay suscriptores que coincidan con la búsqueda."
                  : "Agrega o importa la lista de correos de miembros de la congregación."}
              </p>
              {canEdit && !search && (
                <div className="pt-2 flex justify-center gap-3">
                  <button
                    onClick={() => setIsSubscriberModalOpen(true)}
                    className="inline-flex items-center gap-2 bg-[hsl(var(--primary))] text-white px-4 py-2 rounded-lg text-sm font-medium hover:opacity-90 transition-all"
                  >
                    <UserPlus size={16} /> + Agregar
                  </button>
                  <button
                    onClick={() => setIsImportModalOpen(true)}
                    className="inline-flex items-center gap-2 bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] px-4 py-2 rounded-lg text-sm font-medium border border-[hsl(var(--border))]"
                  >
                    <Upload size={16} /> Importar CSV
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] text-xs font-semibold uppercase tracking-wider">
                      <th className="py-3 px-4">Correo Electrónico</th>
                      <th className="py-3 px-4">Nombre</th>
                      <th className="py-3 px-4">Fecha Suscripción</th>
                      <th className="py-3 px-4">Origen</th>
                      <th className="py-3 px-4 text-center">Estado</th>
                      {canEdit && <th className="py-3 px-4 text-right">Acciones</th>}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[hsl(var(--border))]">
                    {filteredSubscribers.map((sub) => (
                      <tr
                        key={sub.id}
                        className="hover:bg-[hsl(var(--surface-2))/50] transition-colors"
                      >
                        <td className="py-3.5 px-4 font-medium text-[hsl(var(--text-primary))]">
                          {sub.email}
                        </td>
                        <td className="py-3.5 px-4 text-[hsl(var(--text-secondary))]">
                          {sub.name || "—"}
                        </td>
                        <td className="py-3.5 px-4 text-xs text-[hsl(var(--text-secondary))]">
                          {new Date(sub.subscribed_at).toLocaleDateString()}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="inline-block px-2 py-0.5 text-2xs font-semibold rounded bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] uppercase">
                            {sub.source}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <button
                            onClick={() => canEdit && handleToggleSubscriberActive(sub)}
                            disabled={!canEdit}
                            className={clsx(
                              "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer",
                              sub.is_active
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                                : "bg-slate-500/10 text-slate-500 border border-slate-500/20"
                            )}
                          >
                            {sub.is_active ? (
                              <>
                                <CheckCircle2 size={12} /> Activo
                              </>
                            ) : (
                              <>
                                <XCircle size={12} /> Inactivo
                              </>
                            )}
                          </button>
                        </td>
                        {canEdit && (
                          <td className="py-3.5 px-4 text-right">
                            <button
                              onClick={() => setPendingDeleteSubscriber(sub)}
                              className="p-1.5 text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                              title="Eliminar suscriptor"
                            >
                              <Trash2 size={16} />
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SidePanel: Campaign Editor Drawer */}
      <SidePanel
        isOpen={isCampaignDrawerOpen}
        onClose={() => setIsCampaignDrawerOpen(false)}
        title={editingNewsletter ? "Editar Campaña" : "Nueva Campaña"}
        width="w-[650px]"
      >
        <form onSubmit={handleSaveCampaign} className="space-y-5 p-1">
          <div>
            <label className="block text-sm font-semibold mb-1">Nombre Interno</label>
            <input
              type="text"
              required
              placeholder="Ej. Boletín Semanal - Julio 2026"
              value={campaignName}
              onChange={(e) => setCampaignName(e.target.value)}
              className="w-full px-3.5 py-2 text-sm rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold mb-1">Asunto del Correo</label>
            <input
              type="text"
              required
              placeholder="Ej. Novedades y eventos de esta semana en CCF"
              value={campaignSubject}
              onChange={(e) => setCampaignSubject(e.target.value)}
              className="w-full px-3.5 py-2 text-sm rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold mb-1">Estado</label>
              <select
                value={campaignStatus}
                onChange={(e) =>
                  setCampaignStatus(e.target.value as "draft" | "scheduled" | "sent")
                }
                className="w-full px-3.5 py-2 text-sm rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
              >
                <option value="draft">Borrador</option>
                <option value="scheduled">Programado</option>
                <option value="sent">Enviado</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold mb-1">Fecha Programada (Opcional)</label>
              <input
                type="datetime-local"
                value={campaignScheduledAt}
                onChange={(e) => setCampaignScheduledAt(e.target.value)}
                className="w-full px-3.5 py-2 text-sm rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold mb-1">Contenido HTML del Boletín</label>
            <RichEditor
              content={campaignContentHtml}
              onChange={(html) => setCampaignContentHtml(html)}
              placeholder="Diseña tu mensaje o boletín aquí..."
              minHeight="280px"
              token={token || undefined}
            />
          </div>

          <div className="pt-4 border-t border-[hsl(var(--border))] flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={() => setIsCampaignDrawerOpen(false)}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))]"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={savingCampaign}
              className="flex items-center gap-2 bg-[hsl(var(--primary))] text-white px-5 py-2 rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50"
            >
              {savingCampaign && <Loader2 size={16} className="animate-spin" />}
              <span>{editingNewsletter ? "Guardar Cambios" : "Crear Campaña"}</span>
            </button>
          </div>
        </form>
      </SidePanel>

      {/* Modal: Send Confirmation */}
      <AnimatePresence>
        {sendingNewsletter && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl"
            >
              <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-3">
                <div className="flex items-center gap-2 text-[hsl(var(--primary))] font-bold text-lg">
                  <Send size={20} /> Confirmar Envío Directo
                </div>
                <button
                  onClick={() => setSendingNewsletter(null)}
                  className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-3">
                <p className="text-sm text-[hsl(var(--text-primary))]">
                  ¿Estás seguro de que deseas enviar inmediatamente el boletín{" "}
                  <strong className="text-[hsl(var(--primary))]">&quot;<span>{sendingNewsletter.name}</span>&quot;</strong>?
                </p>
                <div className="p-3 bg-[hsl(var(--surface-1))] rounded-xl border border-[hsl(var(--border))] space-y-1.5 text-xs text-[hsl(var(--text-secondary))]">
                  <div className="flex justify-between">
                    <span>Asunto:</span>
                    <span className="font-semibold text-[hsl(var(--text-primary))]">
                      {sendingNewsletter.subject}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Suscriptores activos a enviar:</span>
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">
                      {activeSubscribersCount} correos
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setSendingNewsletter(null)}
                  disabled={isSending}
                  className="px-4 py-2 text-sm font-medium rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))]"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleConfirmSend}
                  disabled={isSending}
                  className="flex items-center gap-2 bg-[hsl(var(--primary))] text-white px-5 py-2 rounded-lg text-sm font-semibold hover:opacity-90 disabled:opacity-50"
                >
                  {isSending && <Loader2 size={16} className="animate-spin" />}
                  <span>Enviar Ahora</span>
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modal: Delete Campaign Confirmation */}
      <AnimatePresence>
        {pendingDeleteNewsletter && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl"
            >
              <h3 className="text-lg font-bold text-red-600 dark:text-red-400 flex items-center gap-2">
                <AlertTriangle size={20} /> Eliminar Campaña
              </h3>
              <p className="text-sm text-[hsl(var(--text-secondary))]">
                ¿Estás seguro de que deseas eliminar la campaña{" "}
                <strong>&quot;{pendingDeleteNewsletter.name}&quot;</strong>? Esta acción no se puede deshacer.
              </p>
              <div className="pt-2 flex justify-end gap-3">
                <button
                  onClick={() => setPendingDeleteNewsletter(null)}
                  disabled={deletingNewsletter}
                  className="px-4 py-2 text-sm font-medium rounded-lg border border-[hsl(var(--border))]"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleConfirmDeleteNewsletter}
                  disabled={deletingNewsletter}
                  className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-700 disabled:opacity-50"
                >
                  {deletingNewsletter && <Loader2 size={16} className="animate-spin" />}
                  <span>Eliminar</span>
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modal: Single Manual Subscriber */}
      <AnimatePresence>
        {isSubscriberModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl"
            >
              <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-3">
                <div className="flex items-center gap-2 font-bold text-lg">
                  <UserPlus size={20} className="text-[hsl(var(--primary))]" /> Agregar Suscriptor
                </div>
                <button
                  onClick={() => setIsSubscriberModalOpen(false)}
                  className="text-[hsl(var(--text-secondary))]"
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleAddSubscriber} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold mb-1">Correo Electrónico *</label>
                  <input
                    type="email"
                    required
                    placeholder="usuario@ejemplo.com"
                    value={subscriberEmail}
                    onChange={(e) => setSubscriberEmail(e.target.value)}
                    className="w-full px-3.5 py-2 text-sm rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold mb-1">Nombre Completo (Opcional)</label>
                  <input
                    type="text"
                    placeholder="Juan Pérez"
                    value={subscriberName}
                    onChange={(e) => setSubscriberName(e.target.value)}
                    className="w-full px-3.5 py-2 text-sm rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
                  />
                </div>

                <div className="pt-2 flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setIsSubscriberModalOpen(false)}
                    className="px-4 py-2 text-sm font-medium rounded-lg border border-[hsl(var(--border))]"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={savingSubscriber}
                    className="flex items-center gap-2 bg-[hsl(var(--primary))] text-white px-5 py-2 rounded-lg text-sm font-semibold hover:opacity-90 disabled:opacity-50"
                  >
                    {savingSubscriber && <Loader2 size={16} className="animate-spin" />}
                    <span>Agregar</span>
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modal: Bulk CSV Import */}
      <AnimatePresence>
        {isImportModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl"
            >
              <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-3">
                <div className="flex items-center gap-2 font-bold text-lg">
                  <Upload size={20} className="text-[hsl(var(--primary))]" /> Importación Masiva de Suscriptores (CSV)
                </div>
                <button
                  onClick={() => setIsImportModalOpen(false)}
                  className="text-[hsl(var(--text-secondary))]"
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleImportCsv} className="space-y-4">
                <div className="space-y-2">
                  <label className="block text-xs font-semibold">Seleccionar archivo CSV / TXT</label>
                  <input
                    type="file"
                    accept=".csv,.txt"
                    onChange={handleFileUpload}
                    className="w-full text-sm text-[hsl(var(--text-secondary))] file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-[hsl(var(--surface-2))] file:text-[hsl(var(--text-primary))] hover:file:bg-[hsl(var(--border))]"
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-semibold">O pegar contenido CSV manualmente</label>
                  <p className="text-2xs text-[hsl(var(--text-secondary))]">
                    Formato: <code>correo@ejemplo.com, Nombre</code> (un registro por línea).
                  </p>
                  <textarea
                    rows={6}
                    placeholder={`juan@ejemplo.com, Juan Pérez\nmaria@ejemplo.com, María Gómez\npedro@ejemplo.com`}
                    value={csvContent}
                    onChange={(e) => setCsvContent(e.target.value)}
                    className="w-full p-3 text-xs font-mono rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
                  />
                </div>

                <div className="pt-2 flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setIsImportModalOpen(false)}
                    className="px-4 py-2 text-sm font-medium rounded-lg border border-[hsl(var(--border))]"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={importing || !csvContent.trim()}
                    className="flex items-center gap-2 bg-[hsl(var(--primary))] text-white px-5 py-2 rounded-lg text-sm font-semibold hover:opacity-90 disabled:opacity-50"
                  >
                    {importing && <Loader2 size={16} className="animate-spin" />}
                    <span>Procesar Importación</span>
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modal: Delete Subscriber Confirmation */}
      <AnimatePresence>
        {pendingDeleteSubscriber && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl"
            >
              <h3 className="text-lg font-bold text-red-600 dark:text-red-400 flex items-center gap-2">
                <AlertTriangle size={20} /> Eliminar Suscriptor
              </h3>
              <p className="text-sm text-[hsl(var(--text-secondary))]">
                ¿Estás seguro de que deseas eliminar a <strong>{pendingDeleteSubscriber.email}</strong>?
              </p>
              <div className="pt-2 flex justify-end gap-3">
                <button
                  onClick={() => setPendingDeleteSubscriber(null)}
                  disabled={deletingSubscriber}
                  className="px-4 py-2 text-sm font-medium rounded-lg border border-[hsl(var(--border))]"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleConfirmDeleteSubscriber}
                  disabled={deletingSubscriber}
                  className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-700 disabled:opacity-50"
                >
                  {deletingSubscriber && <Loader2 size={16} className="animate-spin" />}
                  <span>Eliminar</span>
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
