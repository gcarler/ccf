"use client";

import React, { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Contact,
  Phone,
  Mail,
  MapPin,
  Clock,
  Save,
  Edit2,
  Plus,
  Trash2,
  Loader2,
  X,
  ChevronDown,
  MessageCircle,
} from "lucide-react";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { useRouter } from "next/navigation";
import clsx from "clsx";

interface ContactItem {
  id: string;
  label: string;
  value: string;
  type: "phone" | "whatsapp" | "email" | "address";
  active: boolean;
}

interface ScheduleItem {
  day: string;
  hours: string;
}

const TYPE_OPTIONS: { value: ContactItem["type"]; label: string; icon: React.ElementType; color: string }[] = [
  { value: "phone", label: "Teléfono", icon: Phone, color: "text-emerald-500 bg-emerald-50 dark:bg-emerald-500/10" },
  { value: "whatsapp", label: "WhatsApp", icon: MessageCircle, color: "text-green-600 bg-green-50 dark:bg-green-500/10" },
  { value: "email", label: "Correo", icon: Mail, color: "text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-500/10" },
  { value: "address", label: "Dirección", icon: MapPin, color: "text-amber-500 bg-amber-50 dark:bg-amber-500/10" },
];

const DEFAULT_CONTACTS: ContactItem[] = [
  { id: "1", label: "Línea Principal", value: "+57 (8) 420 0000", type: "phone", active: true },
  { id: "2", label: "WhatsApp Pastoral", value: "+57 300 000 0001", type: "whatsapp", active: true },
  { id: "3", label: "Correo General", value: "info@ccf.org", type: "email", active: true },
  { id: "4", label: "Correo de Soporte", value: "soporte@ccf.org", type: "email", active: false },
  { id: "5", label: "Dirección Sede Central", value: "Calle 10 #5-20, Mocoa, Putumayo", type: "address", active: true },
];

const DEFAULT_SCHEDULE: ScheduleItem[] = [
  { day: "Lunes – Viernes", hours: "8:00 AM – 12:00 PM / 2:00 PM – 6:00 PM" },
  { day: "Sábados", hours: "9:00 AM – 1:00 PM" },
  { day: "Domingos", hours: "Actividades pastorales" },
];

const CONTACTS_KEY = "site_contact_info";
const SCHEDULE_KEY = "site_office_hours";

export default function AdminSettingsContactPage() {
  const { token, isAuthenticated } = useAuth();
  const { addToast } = useToast();
  const router = useRouter();

  const [contacts, setContacts] = useState<ContactItem[]>(DEFAULT_CONTACTS);
  const [schedule, setSchedule] = useState<ScheduleItem[]>(DEFAULT_SCHEDULE);
  const [draftContacts, setDraftContacts] = useState<ContactItem[]>([]);
  const [draftSchedule, setDraftSchedule] = useState<ScheduleItem[]>([]);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deleteConfirmScheduleIdx, setDeleteConfirmScheduleIdx] = useState<number | null>(null);
  const [openTypeMenu, setOpenTypeMenu] = useState<string | null>(null);

  const fetchConfig = useCallback(async (signal?: AbortSignal) => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await apiFetch<Record<string, string>>("/admin/variables", { token, signal });
      if (data[CONTACTS_KEY]) {
        try {
          const parsed = JSON.parse(data[CONTACTS_KEY]);
          if (Array.isArray(parsed) && parsed.length > 0) setContacts(parsed);
        } catch { /* ignore malformed JSON */ }
      }
      if (data[SCHEDULE_KEY]) {
        try {
          const parsed = JSON.parse(data[SCHEDULE_KEY]);
          if (Array.isArray(parsed) && parsed.length > 0) setSchedule(parsed);
        } catch { /* ignore malformed JSON */ }
      }
    } catch (err) {
      addToast("Error al cargar configuración de contacto", "error");
    } finally {
      setLoading(false);
    }
  }, [token, addToast]);

  useEffect(() => {
    if (!isAuthenticated) return;
    const controller = new AbortController();
    fetchConfig(controller.signal);
    return () => controller.abort();
  }, [isAuthenticated, fetchConfig]);

  const startEditing = () => {
    setDraftContacts(contacts.map((c) => ({ ...c })));
    setDraftSchedule(schedule.map((s) => ({ ...s })));
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
    setDeleteConfirmId(null);
    setDeleteConfirmScheduleIdx(null);
    setOpenTypeMenu(null);
  };

  const handleSave = async () => {
    if (!token) return;
    const hasEmpty = draftContacts.some((c) => !c.value.trim() || !c.label.trim());
    if (hasEmpty) {
      addToast("Completa el label y valor de todos los contactos", "error");
      return;
    }
    setSaving(true);
    try {
      await Promise.all([
        apiFetch("/admin/variables", {
          method: "POST",
          token,
          body: { key: CONTACTS_KEY, value: JSON.stringify(draftContacts) },
        }),
        apiFetch("/admin/variables", {
          method: "POST",
          token,
          body: { key: SCHEDULE_KEY, value: JSON.stringify(draftSchedule) },
        }),
      ]);
      setContacts(draftContacts);
      setSchedule(draftSchedule);
      setEditing(false);
      addToast("Configuración de contacto guardada", "success");
    } catch (err) {
      addToast("Error al guardar configuración", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleAddContact = () => {
    const newContact: ContactItem = {
      id: crypto.randomUUID(),
      label: "Nuevo contacto",
      value: "",
      type: "phone",
      active: true,
    };
    setDraftContacts((prev) => [...prev, newContact]);
  };

  const handleAddSchedule = () => {
    setDraftSchedule((prev) => [...prev, { day: "Nuevo día", hours: "9:00 AM – 5:00 PM" }]);
  };

  const handleDeleteContact = (id: string) => {
    setDraftContacts((prev) => prev.filter((c) => c.id !== id));
    setDeleteConfirmId(null);
    addToast("Contacto eliminado", "success");
  };

  const handleDeleteSchedule = (idx: number) => {
    setDraftSchedule((prev) => prev.filter((_, i) => i !== idx));
    setDeleteConfirmScheduleIdx(null);
    addToast("Horario eliminado", "success");
  };

  const updateContact = (id: string, field: keyof ContactItem, value: any) => {
    setDraftContacts((prev) => prev.map((c) => (c.id === id ? { ...c, [field]: value } : c)));
  };

  const updateSchedule = (idx: number, field: keyof ScheduleItem, value: string) => {
    setDraftSchedule((prev) => prev.map((s, i) => (i === idx ? { ...s, [field]: value } : s)));
  };

  const toggleContactActive = (id: string) => {
    if (editing) {
      setDraftContacts((prev) => prev.map((c) => (c.id === id ? { ...c, active: !c.active } : c)));
    } else {
      setContacts((prev) => prev.map((c) => (c.id === id ? { ...c, active: !c.active } : c)));
    }
  };

  if (loading) {
    return (
      <div className="min-h-full bg-[hsl(var(--bg-muted))]/20 font-display flex items-center justify-center">
        <Loader2 size={24} className="animate-spin text-[hsl(var(--primary))]" />
      </div>
    );
  }

  const displayContacts = editing ? draftContacts : contacts;
  const displaySchedule = editing ? draftSchedule : schedule;

  return (
    <div className="min-h-full bg-[hsl(var(--bg-muted))]/20 font-display">
      {/* Header */}
      <div className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-20">
        <div className="px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.back()}
              className="p-2 rounded-lg bg-white/5 border border-white/10 text-[hsl(var(--text-secondary))] hover:text-white transition-all"
            >
              <ArrowLeft size={16} />
            </button>
            <Contact size={18} className="text-[hsl(var(--primary))]" />
            <h1 className="text-[13px] font-semibold uppercase tracking-wide text-white">
              Información de Contacto
            </h1>
          </div>
          <div className="flex items-center gap-2">
            {editing && (
              <button
                onClick={cancelEditing}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 text-white border border-white/10 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all"
              >
                <X size={12} /> Cancelar
              </button>
            )}
            {!editing ? (
              <button
                onClick={startEditing}
                className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/15 text-white border border-white/10 rounded-md text-[11px] font-semibold uppercase tracking-wide transition-all"
              >
                <Edit2 size={14} /> Editar
              </button>
            ) : (
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/80 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-[hsl(var(--primary))]/20 transition-all disabled:opacity-60"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                Guardar
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-3 space-y-3">
        {/* Contact Points */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border border-white/5 rounded-lg p-4"
        >
          <div className="flex items-center justify-between mb-4">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
              Medios de Contacto
            </p>
            {editing && (
              <button
                onClick={handleAddContact}
                className="flex items-center gap-1 text-[hsl(var(--primary))] text-[10px] font-semibold uppercase tracking-wide hover:opacity-70 transition-opacity"
              >
                <Plus size={12} /> Agregar
              </button>
            )}
          </div>
          <div className="space-y-2">
            <AnimatePresence mode="popLayout">
              {displayContacts.map((c) => {
                const typeDef = TYPE_OPTIONS.find((t) => t.value === c.type) ?? TYPE_OPTIONS[0];
                const Icon = typeDef.icon;
                return (
                  <motion.div
                    key={c.id}
                    layout
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95, height: 0 }}
                    className={clsx(
                      "flex items-center gap-3 p-3 rounded-lg border transition-all",
                      c.active
                        ? "bg-white/5 border-white/5 hover:bg-white/8"
                        : "bg-white/[0.02] border-white/[0.03] opacity-60"
                    )}
                  >
                    {/* Type selector or icon */}
                    {editing ? (
                      <div className="relative">
                        <button
                          onClick={() => setOpenTypeMenu(openTypeMenu === c.id ? null : c.id)}
                          className={clsx(
                            "size-9 rounded-md flex items-center justify-center shrink-0 transition-all",
                            typeDef.color
                          )}
                        >
                          <Icon size={14} />
                          <ChevronDown size={8} className="absolute -bottom-0.5 -right-0.5" />
                        </button>
                        <AnimatePresence>
                          {openTypeMenu === c.id && (
                            <motion.div
                              initial={{ opacity: 0, y: -5, scale: 0.95 }}
                              animate={{ opacity: 1, y: 0, scale: 1 }}
                              exit={{ opacity: 0, y: -5, scale: 0.95 }}
                              className="absolute top-full left-0 mt-1 bg-[hsl(var(--bg-primary))] border border-white/10 rounded-lg shadow-xl z-30 overflow-hidden min-w-[140px]"
                            >
                              {TYPE_OPTIONS.map((opt) => {
                                const OptIcon = opt.icon;
                                return (
                                  <button
                                    key={opt.value}
                                    onClick={() => {
                                      updateContact(c.id, "type", opt.value);
                                      setOpenTypeMenu(null);
                                    }}
                                    className={clsx(
                                      "w-full flex items-center gap-2 px-3 py-2 text-[11px] font-medium transition-all",
                                      c.type === opt.value
                                        ? "bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]"
                                        : "text-[hsl(var(--text-secondary))] hover:bg-white/5"
                                    )}
                                  >
                                    <OptIcon size={12} /> {opt.label}
                                  </button>
                                );
                              })}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    ) : (
                      <div className={clsx("size-9 rounded-md flex items-center justify-center shrink-0", typeDef.color)}>
                        <Icon size={14} />
                      </div>
                    )}

                    {/* Label + Value */}
                    <div className="flex-1 min-w-0 space-y-1">
                      {editing ? (
                        <input
                          value={c.label}
                          onChange={(e) => updateContact(c.id, "label", e.target.value)}
                          placeholder="Etiqueta"
                          className="bg-transparent border-b border-white/20 text-[11px] font-semibold text-white uppercase tracking-wide w-full outline-none focus:border-[hsl(var(--primary))] transition-colors py-0.5"
                        />
                      ) : (
                        <p className="text-[11px] font-semibold text-white uppercase tracking-wide">
                          {c.label}
                        </p>
                      )}
                      {editing ? (
                        <input
                          value={c.value}
                          onChange={(e) => updateContact(c.id, "value", e.target.value)}
                          placeholder="Valor"
                          className="bg-transparent border-b border-white/15 text-sm text-[hsl(var(--text-secondary))] font-medium w-full outline-none focus:border-[hsl(var(--primary))] transition-colors py-0.5"
                        />
                      ) : (
                        <p className="text-sm text-[hsl(var(--text-secondary))] font-medium truncate">
                          {c.value || <span className="italic opacity-40">Sin valor</span>}
                        </p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => toggleContactActive(c.id)}
                        className={clsx(
                          "w-9 h-5 rounded-full transition-all relative shrink-0",
                          c.active ? "bg-[hsl(var(--primary))]" : "bg-white/10"
                        )}
                      >
                        <div
                          className={clsx(
                            "absolute top-0.5 size-4 rounded-full bg-white transition-all",
                            c.active ? "left-[18px]" : "left-0.5"
                          )}
                        />
                      </button>
                      {editing && (
                        <>
                          {deleteConfirmId === c.id ? (
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => handleDeleteContact(c.id)}
                                className="px-2 py-1 bg-rose-500 text-white text-[9px] font-bold uppercase rounded transition-all"
                              >
                                Sí
                              </button>
                              <button
                                onClick={() => setDeleteConfirmId(null)}
                                className="px-2 py-1 bg-white/10 text-[hsl(var(--text-secondary))] text-[9px] font-bold uppercase rounded transition-all"
                              >
                                No
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setDeleteConfirmId(c.id)}
                              className="p-1.5 text-rose-500/50 hover:text-rose-500 transition-colors rounded-lg hover:bg-rose-500/10"
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
            {displayContacts.length === 0 && (
              <p className="text-center text-[11px] text-[hsl(var(--text-secondary))] py-6 opacity-60">
                No hay contactos configurados
              </p>
            )}
          </div>
        </motion.div>

        {/* Office Hours */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border border-white/5 rounded-lg p-4"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Clock size={14} className="text-[hsl(var(--primary))]" />
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Horarios de Atención
              </p>
            </div>
            {editing && (
              <button
                onClick={handleAddSchedule}
                className="flex items-center gap-1 text-[hsl(var(--primary))] text-[10px] font-semibold uppercase tracking-wide hover:opacity-70 transition-opacity"
              >
                <Plus size={12} /> Agregar
              </button>
            )}
          </div>
          <div className="space-y-2">
            <AnimatePresence mode="popLayout">
              {displaySchedule.map((s, i) => (
                <motion.div
                  key={i}
                  layout
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95, height: 0 }}
                  className="flex items-center gap-3 p-3 rounded-lg bg-white/5"
                >
                  {editing ? (
                    <input
                      value={s.day}
                      onChange={(e) => updateSchedule(i, "day", e.target.value)}
                      placeholder="Día"
                      className="bg-transparent border-b border-white/20 text-sm font-bold text-white outline-none focus:border-[hsl(var(--primary))] transition-colors w-40"
                    />
                  ) : (
                    <p className="text-sm font-bold text-white w-40">{s.day}</p>
                  )}
                  {editing ? (
                    <input
                      value={s.hours}
                      onChange={(e) => updateSchedule(i, "hours", e.target.value)}
                      placeholder="Horario"
                      className="bg-transparent border-b border-white/15 text-[11px] text-[hsl(var(--text-secondary))] font-medium outline-none focus:border-[hsl(var(--primary))] transition-colors flex-1 text-right"
                    />
                  ) : (
                    <p className="text-[11px] text-[hsl(var(--text-secondary))] font-medium flex-1 text-right">
                      {s.hours}
                    </p>
                  )}
                  {editing && (
                    <>
                      {deleteConfirmScheduleIdx === i ? (
                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            onClick={() => handleDeleteSchedule(i)}
                            className="px-2 py-1 bg-rose-500 text-white text-[9px] font-bold uppercase rounded transition-all"
                          >
                            Sí
                          </button>
                          <button
                            onClick={() => setDeleteConfirmScheduleIdx(null)}
                            className="px-2 py-1 bg-white/10 text-[hsl(var(--text-secondary))] text-[9px] font-bold uppercase rounded transition-all"
                          >
                            No
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirmScheduleIdx(i)}
                          className="p-1.5 text-rose-500/50 hover:text-rose-500 transition-colors rounded-lg hover:bg-rose-500/10 shrink-0"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
            {displaySchedule.length === 0 && (
              <p className="text-center text-[11px] text-[hsl(var(--text-secondary))] py-6 opacity-60">
                No hay horarios configurados
              </p>
            )}
          </div>
        </motion.div>

        {/* Preview Card */}
        {!editing && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border border-white/5 rounded-lg p-4"
          >
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">
              Vista Previa — Contacto Público
            </p>
            <div className="p-4 bg-white/[0.03] rounded-lg border border-white/5 space-y-3">
              {contacts.filter((c) => c.active).map((c) => {
                const typeDef = TYPE_OPTIONS.find((t) => t.value === c.type) ?? TYPE_OPTIONS[0];
                const Icon = typeDef.icon;
                return (
                  <div key={c.id} className="flex items-center gap-3">
                    <div className={clsx("size-8 rounded-md flex items-center justify-center shrink-0", typeDef.color)}>
                      <Icon size={12} />
                    </div>
                    <div className="min-w-0">
                      <p className="text-[9px] font-bold text-white/50 uppercase tracking-wide">{c.label}</p>
                      <p className="text-[11px] text-[hsl(var(--text-secondary))] font-medium truncate">{c.value}</p>
                    </div>
                  </div>
                );
              })}
              {schedule.length > 0 && (
                <div className="pt-2 mt-2 border-t border-white/5">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Clock size={10} className="text-[hsl(var(--primary))]" />
                    <p className="text-[9px] font-bold text-white/50 uppercase tracking-wide">Horarios</p>
                  </div>
                  {schedule.map((s, i) => (
                    <div key={i} className="flex justify-between text-[10px] py-0.5">
                      <span className="font-bold text-white/70">{s.day}</span>
                      <span className="text-[hsl(var(--text-secondary))]">{s.hours}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
