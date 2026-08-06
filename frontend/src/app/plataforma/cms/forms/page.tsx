"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { SITE_KEY } from "@/lib/site-config";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import {
  ClipboardList,
  Plus,
  Search,
  Edit2,
  Trash2,
  Globe,
  Loader2,
  Inbox,
  X,
  ChevronLeft,
  ChevronRight,
  Mail,
  ListFilter,
  CheckCircle2,
  Eye,
  GripVertical,
  ShieldCheck,
} from "lucide-react";
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  KeyboardSensor,
} from "@dnd-kit/core";
import { useAuth } from "@/context/AuthContext";
import SidePanel from "@/components/ui/SidePanel";
import clsx from "clsx";
import {
  createCmsForm,
  deleteCmsForm,
  listCmsForms,
  listCmsFormSubmissions,
  listCmsSites,
  putCmsForm,
} from "@/lib/cms/v2";
import {
  CmsForm,
  CmsFormField,
  CmsFormFieldType,
  CmsFormPublicRead,
  CmsFormSubmissionPaginated,
  CmsSite,
} from "@/types/cms-v2";
import { canEditCms } from "@/lib/cms/permissions";
import { FieldEditor, FIELD_TYPES, makeDefaultField } from "@/components/cms/forms/FieldEditor";
import CmsFormRenderer from "@/components/public/cms/CmsFormRenderer";

function SortableField({
  field,
  index,
  total,
  siblings,
  onChange,
  onRemove,
  onMove,
}: {
  field: CmsFormField;
  index: number;
  total: number;
  siblings: CmsFormField[];
  onChange: (field: CmsFormField) => void;
  onRemove: (id: string) => void;
  onMove: (index: number, direction: "up" | "down") => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: field.id,
  });

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.4 : 1,
        position: "relative",
        zIndex: isDragging ? 10 : 0,
      }}
    >
      <FieldEditor
        field={field}
        index={index}
        total={total}
        siblings={siblings}
        onChange={onChange}
        onRemove={() => onRemove(field.id)}
        onMove={(dir) => onMove(index, dir)}
        dragHandle={
          <button
            type="button"
            className="p-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 cursor-grab active:cursor-grabbing touch-none"
            title="Arrastrar para reordenar"
            {...attributes}
            {...listeners}
          >
            <GripVertical className="w-3.5 h-3.5" />
          </button>
        }
      />
    </div>
  );
}

export default function CmsFormsManagement() {
  const { token, user } = useAuth();
  const [activeTab, setActiveTab] = useState<"forms" | "submissions">("forms");
  const [siteKey, setSiteKey] = useState(SITE_KEY);
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [forms, setForms] = useState<CmsForm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  // Form Editor Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [editingForm, setEditingForm] = useState<CmsForm | null>(null);
  const [saving, setSaving] = useState(false);

  // Form Editor Fields state
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formSubmitButtonText, setFormSubmitButtonText] = useState("Enviar");
  const [formSuccessMessage, setFormSuccessMessage] = useState("¡Gracias por tu mensaje!");
  const [formIsActive, setFormIsActive] = useState(true);
  const [formFields, setFormFields] = useState<CmsFormField[]>([]);
  const [formNotifyEmails, setFormNotifyEmails] = useState<string[]>([]);
  const [emailInput, setEmailInput] = useState("");
  // plan_de_form_builder: protección anti-spam a nivel de formulario.
  const [formCaptchaEnabled, setFormCaptchaEnabled] = useState(false);
  const [formHoneypotEnabled, setFormHoneypotEnabled] = useState(true);
  const [drawerView, setDrawerView] = useState<"edit" | "preview">("edit");

  // DnD (@dnd-kit) para reordenar campos del constructor.
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  // Submissions Tab / View State
  const [selectedFormId, setSelectedFormId] = useState<string | null>(null);
  const [submissionsData, setSubmissionsData] = useState<CmsFormSubmissionPaginated | null>(null);
  const [submissionsLoading, setSubmissionsLoading] = useState(false);
  const [submissionsPage, setSubmissionsPage] = useState(1);

  // Delete modal state
  const [pendingDelete, setPendingDelete] = useState<CmsForm | null>(null);
  const [deleting, setDeleting] = useState(false);

  const canEdit = canEditCms(user?.role);

  // Vista previa en vivo: el renderer público consume un objeto ``CmsFormPublicRead``.
  const previewForm: CmsFormPublicRead = useMemo(
    () => ({
      id: editingForm?.id ?? "preview",
      name: formName || "Formulario sin nombre",
      description: formDescription || null,
      fields: formFields,
      submit_button_text: formSubmitButtonText || "Enviar",
      success_message: formSuccessMessage || "¡Gracias por tu mensaje!",
      captcha_enabled: formCaptchaEnabled,
      captcha_provider: "hcaptcha",
      captcha_site_key: null,
      honeypot_enabled: formHoneypotEnabled,
      settings_json: {},
      is_active: true,
    }),
    [editingForm, formName, formDescription, formFields, formSubmitButtonText, formSuccessMessage, formCaptchaEnabled, formHoneypotEnabled]
  );

  const fetchData = useCallback(async (targetSite: string) => {
    if (!token) {
      setLoading(false);
      setForms([]);
      setError("Debes iniciar sesión para gestionar formularios.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [nextSites, nextForms] = await Promise.all([
        listCmsSites(token),
        listCmsForms(targetSite, token),
      ]);
      setSites(nextSites || []);
      const loadedForms = nextForms || [];
      setForms(loadedForms);
      if (loadedForms.length > 0 && !selectedFormId) {
        setSelectedFormId(loadedForms[0].id);
      }
    } catch (err) {
      toast.error("Error al cargar formularios");
      setForms([]);
      setError("No se pudieron cargar los formularios de contacto.");
    } finally {
      setLoading(false);
    }
  }, [token, selectedFormId]);

  useEffect(() => {
    fetchData(siteKey);
  }, [fetchData, siteKey]);

  const fetchSubmissions = useCallback(
    async (formId: string, page: number) => {
      if (!token) return;
      setSubmissionsLoading(true);
      try {
        const res = await listCmsFormSubmissions(siteKey, formId, page, 20, token);
        setSubmissionsData(res);
      } catch (err) {
        toast.error("Error al cargar respuestas del formulario");
      } finally {
        setSubmissionsLoading(false);
      }
    },
    [siteKey, token]
  );

  useEffect(() => {
    if (activeTab === "submissions" && selectedFormId) {
      fetchSubmissions(selectedFormId, submissionsPage);
    }
  }, [activeTab, selectedFormId, submissionsPage, fetchSubmissions]);

  const visibleForms = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return forms;
    return forms.filter(
      (f) =>
        f.name.toLowerCase().includes(term) ||
        (f.description && f.description.toLowerCase().includes(term))
    );
  }, [forms, search]);

  const selectedForm = useMemo(() => {
    return forms.find((f) => f.id === selectedFormId) || null;
  }, [forms, selectedFormId]);

  const handleOpenCreate = () => {
    setEditingForm(null);
    setFormName("");
    setFormDescription("");
    setFormSubmitButtonText("Enviar");
    setFormSuccessMessage("¡Gracias por tu mensaje!");
    setFormIsActive(true);
    setFormFields([
      { id: "f_1", type: "text", label: "Nombre completo", placeholder: "Ej. Juan Pérez", required: true },
      { id: "f_2", type: "email", label: "Correo electrónico", placeholder: "ejemplo@correo.com", required: true },
      { id: "f_3", type: "textarea", label: "Mensaje", placeholder: "Escribe tu consulta...", required: true },
    ]);
    setFormNotifyEmails([]);
    setEmailInput("");
    setFormCaptchaEnabled(false);
    setFormHoneypotEnabled(true);
    setDrawerView("edit");
    setIsDrawerOpen(true);
  };

  const handleOpenEdit = (form: CmsForm) => {
    setEditingForm(form);
    setFormName(form.name);
    setFormDescription(form.description || "");
    setFormSubmitButtonText(form.submit_button_text || "Enviar");
    setFormSuccessMessage(form.success_message || "¡Gracias por tu mensaje!");
    setFormIsActive(form.is_active);
    setFormFields(form.fields || []);
    setFormNotifyEmails(form.notify_emails || []);
    setEmailInput("");
    setFormCaptchaEnabled(form.captcha_enabled ?? false);
    setFormHoneypotEnabled(form.honeypot_enabled ?? true);
    setDrawerView("edit");
    setIsDrawerOpen(true);
  };

  const handleAddField = (type: CmsFormFieldType) => {
    setFormFields((prev) => [...prev, makeDefaultField(type, prev.length)]);
  };

  const handleUpdateField = (id: string, updates: Partial<CmsFormField>) => {
    setFormFields((prev) =>
      prev.map((f) => (f.id === id ? { ...f, ...updates } : f))
    );
  };

  const handleRemoveField = (id: string) => {
    setFormFields((prev) => prev.filter((f) => f.id !== id));
  };

  const handleMoveField = (index: number, direction: "up" | "down") => {
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= formFields.length) return;
    const nextFields = [...formFields];
    const temp = nextFields[index];
    nextFields[index] = nextFields[targetIndex];
    nextFields[targetIndex] = temp;
    setFormFields(nextFields);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setFormFields((prev) => {
      const oldIndex = prev.findIndex((f) => f.id === active.id);
      const newIndex = prev.findIndex((f) => f.id === over.id);
      if (oldIndex < 0 || newIndex < 0) return prev;
      return arrayMove(prev, oldIndex, newIndex);
    });
  };

  const handleAddEmail = () => {
    const clean = emailInput.trim().toLowerCase();
    if (!clean) return;
    if (!clean.includes("@") || !clean.includes(".")) {
      toast.error("Ingresa un correo electrónico válido");
      return;
    }
    if (formNotifyEmails.includes(clean)) {
      toast.error("El correo ya está en la lista de notificaciones");
      return;
    }
    setFormNotifyEmails((prev) => [...prev, clean]);
    setEmailInput("");
  };

  const handleRemoveEmail = (email: string) => {
    setFormNotifyEmails((prev) => prev.filter((e) => e !== email));
  };

  const handleToggleActive = async (form: CmsForm) => {
    if (!token || !canEdit) return;
    const nextState = !form.is_active;
    setForms((prev) =>
      prev.map((f) => (f.id === form.id ? { ...f, is_active: nextState } : f))
    );
    try {
      await putCmsForm(siteKey, form.id, { ...form, is_active: nextState }, token);
      toast.success(`Formulario "${form.name}" ${nextState ? "activado" : "desactivado"}`);
    } catch (err) {
      toast.error("Error al cambiar estado del formulario");
      fetchData(siteKey);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !canEdit) return;
    const trimmedName = formName.trim();
    if (!trimmedName) {
      toast.error("Ingresa un nombre para el formulario");
      return;
    }
    if (formFields.length === 0) {
      toast.error("El formulario debe tener al menos un campo");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: trimmedName,
        description: formDescription.trim() || null,
        fields: formFields,
        submit_button_text: formSubmitButtonText.trim() || "Enviar",
        success_message: formSuccessMessage.trim() || "¡Gracias por tu mensaje!",
        notify_emails: formNotifyEmails,
        is_active: formIsActive,
        captcha_enabled: formCaptchaEnabled,
        captcha_provider: formCaptchaEnabled ? "hcaptcha" : "hcaptcha",
        honeypot_enabled: formHoneypotEnabled,
        settings_json: {},
      };

      if (editingForm) {
        await putCmsForm(siteKey, editingForm.id, payload, token);
        toast.success(`Formulario "${trimmedName}" actualizado`);
      } else {
        await createCmsForm(siteKey, payload, token);
        toast.success(`Formulario "${trimmedName}" creado`);
      }
      setIsDrawerOpen(false);
      await fetchData(siteKey);
    } catch (err) {
      toast.error("Error al guardar el formulario");
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!token || !canEdit || !pendingDelete) return;
    setDeleting(true);
    try {
      await deleteCmsForm(siteKey, pendingDelete.id, token);
      toast.success("Formulario eliminado correctamente");
      if (selectedFormId === pendingDelete.id) {
        setSelectedFormId(null);
      }
      await fetchData(siteKey);
    } catch (err) {
      toast.error("Error al eliminar el formulario");
    } finally {
      setDeleting(false);
      setPendingDelete(null);
    }
  };

  const handleViewSubmissions = (form: CmsForm) => {
    setSelectedFormId(form.id);
    setSubmissionsPage(1);
    setActiveTab("submissions");
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <ClipboardList className="w-7 h-7 text-blue-600 dark:text-blue-400" />
            Módulo de Formularios de Contacto
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
            Diseña formularios de contacto dinámicos, gestiona notificaciones por email y visualiza respuestas.
          </p>
        </div>

        {canEdit && (
          <button
            onClick={handleOpenCreate}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm transition-colors shrink-0"
          >
            <Plus className="w-4 h-4" /> Nuevo Formulario
          </button>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-xl text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-zinc-200 dark:border-zinc-800">
        <button
          onClick={() => setActiveTab("forms")}
          className={clsx(
            "flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors",
            activeTab === "forms"
              ? "border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400"
              : "border-transparent text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200"
          )}
        >
          <ClipboardList className="w-4 h-4" />
          Formularios ({forms.length})
        </button>
        <button
          onClick={() => setActiveTab("submissions")}
          className={clsx(
            "flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors",
            activeTab === "submissions"
              ? "border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400"
              : "border-transparent text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200"
          )}
        >
          <Inbox className="w-4 h-4" />
          Respuestas
        </button>
      </div>

      {/* Tab 1: Formularios */}
      {activeTab === "forms" && (
        <div className="space-y-6">
          {/* Filter and Site Selector */}
          <div className="flex flex-col sm:flex-row items-center gap-3 bg-white dark:bg-zinc-900 p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm">
            <div className="relative flex-1 w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
              <input
                type="text"
                placeholder="Buscar por nombre o descripción..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {sites.length > 1 && (
              <div className="flex items-center gap-2 shrink-0">
                <Globe className="w-4 h-4 text-zinc-400" />
                <select
                  value={siteKey}
                  onChange={(e) => setSiteKey(e.target.value)}
                  className="bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {sites.map((s) => (
                    <option key={s.site_key} value={s.site_key}>
                      {s.name} ({s.site_key})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Content State: Skeleton Loaders, Empty State or Cards */}
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-48 bg-zinc-100 dark:bg-zinc-800 animate-pulse rounded-xl border border-zinc-200 dark:border-zinc-700 p-5 space-y-3">
                  <div className="h-5 bg-zinc-200 dark:bg-zinc-700 rounded w-1/2" />
                  <div className="h-4 bg-zinc-200 dark:bg-zinc-700 rounded w-3/4" />
                  <div className="h-10 bg-zinc-200 dark:bg-zinc-700 rounded w-full mt-4" />
                </div>
              ))}
            </div>
          ) : visibleForms.length === 0 ? (
            <div className="bg-white dark:bg-zinc-900 border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-2xl p-12 text-center flex flex-col items-center justify-center space-y-4">
              <div className="w-16 h-16 rounded-full bg-blue-50 dark:bg-blue-950/50 flex items-center justify-center text-blue-600 dark:text-blue-400">
                <ClipboardList className="w-8 h-8" />
              </div>
              <div className="max-w-md">
                <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">No hay formularios registrados</h3>
                <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                  Crea un nuevo formulario de contacto para recibir consultas de los visitantes de tu sitio web.
                </p>
              </div>
              {canEdit && (
                <button
                  onClick={handleOpenCreate}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg shadow hover:bg-blue-700 transition-colors"
                >
                  <Plus className="w-4 h-4" /> Crear Primer Formulario
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence>
                {visibleForms.map((form) => (
                  <motion.div
                    key={form.id}
                    layout
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 text-base truncate">
                          {form.name}
                        </h3>
                        <button
                          onClick={() => handleToggleActive(form)}
                          title={form.is_active ? "Desactivar" : "Activar"}
                          className={clsx(
                            "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none",
                            form.is_active ? "bg-blue-600" : "bg-zinc-300 dark:bg-zinc-700"
                          )}
                        >
                          <span
                            className={clsx(
                              "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                              form.is_active ? "translate-x-5" : "translate-x-0"
                            )}
                          />
                        </button>
                      </div>

                      {form.description && (
                        <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 line-clamp-2">
                          {form.description}
                        </p>
                      )}

                      <div className="mt-4 flex items-center gap-3 flex-wrap">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
                          <ListFilter className="w-3.5 h-3.5" /> {form.fields?.length || 0} campos
                        </span>
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                          <Inbox className="w-3.5 h-3.5" /> {form.submission_count ?? 0} respuestas
                        </span>
                      </div>
                    </div>

                    <div className="mt-5 pt-3 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                      <button
                        onClick={() => handleViewSubmissions(form)}
                        className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        <Inbox className="w-3.5 h-3.5" /> Ver respuestas
                      </button>

                      <div className="flex items-center gap-1">
                        {canEdit && (
                          <>
                            <button
                              onClick={() => handleOpenEdit(form)}
                              className="p-1.5 text-zinc-600 dark:text-zinc-400 hover:text-blue-600 dark:hover:text-blue-400 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                              title="Editar formulario"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setPendingDelete(form)}
                              className="p-1.5 text-zinc-600 dark:text-zinc-400 hover:text-red-600 dark:hover:text-red-400 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                              title="Eliminar formulario"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Respuestas */}
      {activeTab === "submissions" && (
        <div className="space-y-6">
          {/* Form Selector Header */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white dark:bg-zinc-900 p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm">
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <label className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 shrink-0">
                Formulario:
              </label>
              <select
                value={selectedFormId || ""}
                onChange={(e) => {
                  setSelectedFormId(e.target.value);
                  setSubmissionsPage(1);
                }}
                className="w-full sm:w-80 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {forms.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name} ({f.submission_count ?? 0} respuestas)
                  </option>
                ))}
              </select>
            </div>

            {selectedForm && (
              <div className="flex items-center gap-2 text-xs font-medium text-zinc-500 dark:text-zinc-400">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>Estado: {selectedForm.is_active ? "Activo" : "Inactivo"}</span>
                <span className="mx-1">•</span>
                <span>{selectedForm.notify_emails?.length || 0} emails notificados</span>
              </div>
            )}
          </div>

          {/* Submissions Table / Skeletons / Empty State */}
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm space-y-4">
            {submissionsLoading ? (
              <div className="space-y-3 py-6">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 bg-zinc-100 dark:bg-zinc-800 animate-pulse rounded-lg" />
                ))}
              </div>
            ) : !submissionsData || submissionsData.items.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center space-y-3">
                <div className="w-16 h-16 rounded-full bg-blue-50 dark:bg-blue-950/50 flex items-center justify-center text-blue-600 dark:text-blue-400">
                  <Inbox className="w-8 h-8" />
                </div>
                <div className="max-w-md">
                  <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
                    Aún no hay respuestas para este formulario
                  </h3>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                    Las respuestas enviadas por los usuarios desde la página pública se registrarán aquí en tiempo real.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-zinc-700 dark:text-zinc-300">
                    <thead className="bg-zinc-50 dark:bg-zinc-800 text-zinc-500 uppercase tracking-wider font-semibold">
                      <tr>
                        <th className="px-4 py-3 rounded-l-lg">Fecha</th>
                        <th className="px-4 py-3">Dirección IP</th>
                        <th className="px-4 py-3 rounded-r-lg">Respuestas del Usuario</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                      {submissionsData.items.map((sub) => (
                        <tr key={sub.id} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/40 transition-colors">
                          <td className="px-4 py-3 font-medium whitespace-nowrap text-zinc-900 dark:text-zinc-100">
                            {new Date(sub.submitted_at).toLocaleString("es-ES")}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-zinc-500">
                            {sub.ip_address || "N/A"}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-col gap-1">
                              {Object.entries(sub.data || {}).map(([key, val]) => (
                                <div key={key} className="text-xs">
                                  <span className="font-semibold text-zinc-900 dark:text-zinc-200">{key}: </span>
                                  <span className="text-zinc-600 dark:text-zinc-400">{String(val)}</span>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {submissionsData.total > 0 && (
                  <div className="flex items-center justify-between border-t border-zinc-200 dark:border-zinc-800 pt-3 text-xs">
                    <span className="text-zinc-500">
                      Página {submissionsData.page} de {Math.ceil(submissionsData.total / submissionsData.page_size)} ({submissionsData.total} respuestas)
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSubmissionsPage((prev) => Math.max(prev - 1, 1))}
                        disabled={submissionsPage <= 1}
                        className="p-1.5 border border-zinc-200 dark:border-zinc-700 rounded-lg disabled:opacity-30 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setSubmissionsPage((prev) => prev + 1)}
                        disabled={submissionsPage * submissionsData.page_size >= submissionsData.total}
                        className="p-1.5 border border-zinc-200 dark:border-zinc-700 rounded-lg disabled:opacity-30 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Form Constructor SidePanel / Drawer */}
      <SidePanel
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={editingForm ? "Editar Formulario" : "Nuevo Formulario"}
        subtitle="Construye los campos y configura mensajes"
        width="w-[720px]"
      >
        <div className="px-6 pt-5">
          <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-800 rounded-lg p-1 text-xs font-semibold w-fit">
            <button
              type="button"
              onClick={() => setDrawerView("edit")}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors",
                drawerView === "edit"
                  ? "bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-sm"
                  : "text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200"
              )}
            >
              <ClipboardList className="w-3.5 h-3.5" /> Editar
            </button>
            <button
              type="button"
              onClick={() => setDrawerView("preview")}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors",
                drawerView === "preview"
                  ? "bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-sm"
                  : "text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200"
              )}
            >
              <Eye className="w-3.5 h-3.5" /> Vista previa
            </button>
          </div>
        </div>

        {drawerView === "preview" ? (
          <div className="p-6">
            {formFields.length === 0 ? (
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                Aún no hay campos. Agrega campos para ver la vista previa.
              </p>
            ) : (
              <div className="p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900">
                <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 mb-1">{previewForm.name}</h3>
                <CmsFormRenderer form={previewForm} preview />
              </div>
            )}
          </div>
        ) : (
        <form onSubmit={handleSave} className="p-6 space-y-6">
          {/* General Config */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Información General
            </h3>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                Nombre del Formulario *
              </label>
              <input
                type="text"
                required
                placeholder="ej. Formulario de Contacto Principal"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                Descripción (opcional)
              </label>
              <textarea
                rows={2}
                placeholder="Breve explicación para uso interno o instrucciones"
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none resize-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  Texto del Botón Enviar *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Enviar"
                  value={formSubmitButtonText}
                  onChange={(e) => setFormSubmitButtonText(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  Estado Inicial
                </label>
                <div className="flex items-center h-10 px-3 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg">
                  <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formIsActive}
                      onChange={(e) => setFormIsActive(e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                    Activo y visible en API pública
                  </label>
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                Mensaje de Éxito *
              </label>
              <input
                type="text"
                required
                placeholder="¡Gracias por tu mensaje!"
                value={formSuccessMessage}
                onChange={(e) => setFormSuccessMessage(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Anti-spam: captcha + honeypot (plan_de_form_builder) */}
          <div className="space-y-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4" /> Protección Anti-Spam
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="flex items-center justify-between gap-3 p-3 bg-zinc-50 dark:bg-zinc-800/40 rounded-lg border border-zinc-200 dark:border-zinc-700">
                <div>
                  <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Captcha (hCaptcha)</div>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                    Requiere verificación humana antes de enviar.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setFormCaptchaEnabled((v) => !v)}
                  className={clsx(
                    "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors",
                    formCaptchaEnabled ? "bg-blue-600" : "bg-zinc-300 dark:bg-zinc-700"
                  )}
                  aria-pressed={formCaptchaEnabled}
                >
                  <span
                    className={clsx(
                      "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform",
                      formCaptchaEnabled ? "translate-x-5" : "translate-x-0"
                    )}
                  />
                </button>
              </div>
              <div className="flex items-center justify-between gap-3 p-3 bg-zinc-50 dark:bg-zinc-800/40 rounded-lg border border-zinc-200 dark:border-zinc-700">
                <div>
                  <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Campo trampa (Honeypot)</div>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                    Atrapa bots que rellenan campos ocultos.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setFormHoneypotEnabled((v) => !v)}
                  className={clsx(
                    "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors",
                    formHoneypotEnabled ? "bg-blue-600" : "bg-zinc-300 dark:bg-zinc-700"
                  )}
                  aria-pressed={formHoneypotEnabled}
                >
                  <span
                    className={clsx(
                      "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform",
                      formHoneypotEnabled ? "translate-x-5" : "translate-x-0"
                    )}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* Email Notifications Chips */}
          <div className="space-y-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Notificaciones por Correo
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Agrega las direcciones que recibirán una notificación por cada nueva respuesta enviada.
            </p>

            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                <input
                  type="email"
                  placeholder="ejemplo@ccf.org"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddEmail();
                    }
                  }}
                  className="w-full pl-9 pr-4 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
              <button
                type="button"
                onClick={handleAddEmail}
                className="px-3 py-2 bg-zinc-800 dark:bg-zinc-700 hover:bg-zinc-900 text-white rounded-lg text-sm font-medium transition-colors"
              >
                + Agregar
              </button>
            </div>

            {formNotifyEmails.length > 0 && (
              <div className="flex flex-wrap gap-2 pt-1">
                {formNotifyEmails.map((email) => (
                  <span
                    key={email}
                    className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800 rounded-full text-xs font-medium"
                  >
                    {email}
                    <button
                      type="button"
                      onClick={() => handleRemoveEmail(email)}
                      className="hover:text-blue-900 dark:hover:text-white"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Field Builder */}
          <div className="space-y-4 pt-4 border-t border-zinc-200 dark:border-zinc-800">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                  Constructor de Campos ({formFields.length})
                </h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">Define los campos que llenará el usuario.</p>
              </div>
            </div>

            {/* Field Types Selector */}
            <div className="p-3 bg-zinc-50 dark:bg-zinc-800/40 rounded-xl border border-zinc-200 dark:border-zinc-700 space-y-2">
              <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">+ Agregar campo:</span>
              <div className="flex flex-wrap gap-2">
                {FIELD_TYPES.map((t) => (
                  <button
                    key={t.type}
                    type="button"
                    onClick={() => handleAddField(t.type)}
                    className="px-2.5 py-1.5 bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 hover:border-blue-500 hover:text-blue-600 rounded-lg text-xs font-medium shadow-sm transition-colors"
                  >
                    + {t.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Field List */}
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={formFields.map((f) => f.id)} strategy={verticalListSortingStrategy}>
                <div className="space-y-3">
                  {formFields.map((field, idx) => (
                    <SortableField
                      key={field.id}
                      field={field}
                      index={idx}
                      total={formFields.length}
                      siblings={formFields}
                      onChange={(field) => handleUpdateField(field.id, field)}
                      onRemove={handleRemoveField}
                      onMove={handleMoveField}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          </div>

          {/* Form Drawer Footer Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
            <button
              type="button"
              onClick={() => setIsDrawerOpen(false)}
              className="px-4 py-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow transition-colors disabled:opacity-50"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {editingForm ? "Guardar Cambios" : "Crear Formulario"}
            </button>
          </div>
        </form>
        )}
      </SidePanel>

      {/* Delete Confirmation Modal */}
      {pendingDelete && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">Eliminar Formulario</h3>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              ¿Estás seguro de eliminar el formulario <strong className="text-zinc-900 dark:text-zinc-100">&quot;{pendingDelete.name}&quot;</strong>? Esta acción no se puede deshacer y borrará todas sus respuestas registradas.
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setPendingDelete(null)}
                className="px-4 py-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={confirmDelete}
                disabled={deleting}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {deleting && <Loader2 className="w-4 h-4 animate-spin" />}
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
