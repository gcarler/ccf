'use client';

import React, { useEffect, useState, useId } from 'react';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import ErrorBoundary from '@/components/ErrorBoundary';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import {
  Plus,
  Trash2,
  ArrowUp,
  ArrowDown,
  Eye,
  Settings,
  Sparkles,
  Save,
  Check,
  AlertCircle,
  FileText,
  User,
  Phone,
  Mail,
  HelpCircle,
  Users,
  Heart,
  Calendar,
  Type,
  AlignLeft,
  List,
  CheckSquare,
} from 'lucide-react';
import { DSButton, DSInput } from '@/design';
import clsx from 'clsx';

export interface FormStudioField {
  id: string;
  type: 'text' | 'textarea' | 'select' | 'checkbox' | 'date' | 'email' | 'phone';
  label: string;
  placeholder?: string;
  required: boolean;
  options?: string[];
  help_text?: string;
}

interface EventFormStudioDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  eventId: string;
  eventName: string;
  token?: string | null;
  onSaved?: () => void;
}

const PRESET_BLOCKS: Array<{
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  field: FormStudioField;
}> = [
  {
    id: 'full_name',
    title: 'Nombres y Apellidos',
    description: 'Nombre completo del participante',
    icon: User,
    field: {
      id: 'full_name',
      type: 'text',
      label: 'Nombres y Apellidos Completos',
      placeholder: 'Ej. Juan David Pérez',
      required: true,
    },
  },
  {
    id: 'phone',
    title: 'Teléfono / WhatsApp',
    description: 'Móvil para confirmación y recordatorios',
    icon: Phone,
    field: {
      id: 'phone',
      type: 'phone',
      label: 'Teléfono / WhatsApp',
      placeholder: 'Ej. 3001234567',
      required: true,
    },
  },
  {
    id: 'email',
    title: 'Correo Electrónico',
    description: 'Envío automático del Pase Digital QR',
    icon: Mail,
    field: {
      id: 'email',
      type: 'email',
      label: 'Correo Electrónico',
      placeholder: 'ejemplo@correo.com',
      required: true,
    },
  },
  {
    id: 'id_document',
    title: 'Documento de Identidad',
    description: 'Cédula de ciudadanía, extranjería o pasaporte',
    icon: FileText,
    field: {
      id: 'id_document',
      type: 'text',
      label: 'Número de Identificación (CC/TI/Pasaporte)',
      placeholder: 'Ej. 1020304050',
      required: true,
    },
  },
  {
    id: 'invited_by',
    title: '¿Quién te invitó?',
    description: 'Persona o líder que extendió la invitación',
    icon: HelpCircle,
    field: {
      id: 'invited_by',
      type: 'text',
      label: '¿Quién te invitó a este evento?',
      placeholder: 'Nombre del anfitrión o amigo',
      required: false,
    },
  },
  {
    id: 'life_group',
    title: 'Grupo de Vida / Célula',
    description: 'Grupo al que asiste regularmente',
    icon: Users,
    field: {
      id: 'life_group',
      type: 'text',
      label: '¿Perteneces a un Grupo de Vida? (Nombre / Líder)',
      placeholder: 'Ej. Grupo Betel - Pastor Carlos',
      required: false,
    },
  },
  {
    id: 'prayer_request',
    title: 'Petición de Oración',
    description: 'Motivo por el cual nuestro equipo orará',
    icon: Heart,
    field: {
      id: 'prayer_request',
      type: 'textarea',
      label: '¿Tienes una petición especial de oración?',
      placeholder: 'Escribe aquí tu motivo de oración...',
      required: false,
    },
  },
];

const CUSTOM_TYPES: Array<{
  type: FormStudioField['type'];
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  defaultLabel: string;
}> = [
  { type: 'text', label: 'Texto Corto', icon: Type, defaultLabel: 'Texto' },
  { type: 'textarea', label: 'Párrafo', icon: AlignLeft, defaultLabel: 'Comentarios o Detalles' },
  { type: 'select', label: 'Selección Desplegable', icon: List, defaultLabel: 'Selecciona una opción' },
  { type: 'checkbox', label: 'Casilla de Verificación', icon: CheckSquare, defaultLabel: 'Acepto participar' },
  { type: 'date', label: 'Fecha', icon: Calendar, defaultLabel: 'Fecha de Nacimiento o Aniversario' },
];

export default function EventFormStudioDrawer({
  isOpen,
  onClose,
  eventId,
  eventName,
  token,
  onSaved,
}: EventFormStudioDrawerProps) {
  const [activeTab, setActiveTab] = useState<'editor' | 'preview'>('editor');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [submitButtonText, setSubmitButtonText] = useState('Confirmar Pre-registro');
  const [successMessage, setSuccessMessage] = useState('¡Tu pre-registro ha sido confirmado exitosamente!');
  const [fields, setFields] = useState<FormStudioField[]>([]);
  const [selectedFieldIndex, setSelectedFieldIndex] = useState<number | null>(null);

  // Cargar formulario al abrir el drawer
  useEffect(() => {
    if (!isOpen || !eventId) return;
    setLoading(true);
    apiFetch<{
      id?: string | null;
      name?: string;
      description?: string;
      fields?: FormStudioField[];
      submit_button_text?: string;
      success_message?: string;
    }>(`/evangelism/events/${eventId}/form`, { token, silent: true })
      .then((data) => {
        setFormName(data.name || `Pre-registro: ${eventName}`);
        setFormDescription(data.description || 'Por favor completa la información para generar tu pase de ingreso.');
        setSubmitButtonText(data.submit_button_text || 'Confirmar Pre-registro');
        setSuccessMessage(data.success_message || '¡Tu pre-registro ha sido confirmado exitosamente!');
        if (Array.isArray(data.fields) && data.fields.length > 0) {
          setFields(data.fields);
          setSelectedFieldIndex(0);
        } else {
          // Si está vacío, precargar los 4 campos básicos del protocolo
          setFields([
            PRESET_BLOCKS[0].field,
            PRESET_BLOCKS[1].field,
            PRESET_BLOCKS[2].field,
            PRESET_BLOCKS[3].field,
          ]);
          setSelectedFieldIndex(0);
        }
      })
      .catch(() => {
        setFormName(`Pre-registro: ${eventName}`);
        setFields([
          PRESET_BLOCKS[0].field,
          PRESET_BLOCKS[1].field,
          PRESET_BLOCKS[2].field,
        ]);
        setSelectedFieldIndex(0);
      })
      .finally(() => setLoading(false));
  }, [isOpen, eventId, eventName, token]);

  const addPresetBlock = (preset: typeof PRESET_BLOCKS[0]) => {
    const exists = fields.some((f) => f.id === preset.field.id);
    const newId = exists ? `${preset.field.id}_${Date.now().toString().slice(-4)}` : preset.field.id;
    const newField: FormStudioField = { ...preset.field, id: newId };
    setFields((prev) => [...prev, newField]);
    setSelectedFieldIndex(fields.length);
    toast.success(`Bloque "${preset.title}" añadido`);
  };

  const addCustomField = (custom: typeof CUSTOM_TYPES[0]) => {
    const fieldId = `field_${Date.now().toString().slice(-6)}`;
    const newField: FormStudioField = {
      id: fieldId,
      type: custom.type,
      label: custom.defaultLabel,
      placeholder: custom.type === 'text' || custom.type === 'textarea' ? 'Escribe aquí...' : undefined,
      required: false,
      options: custom.type === 'select' ? ['Opción 1', 'Opción 2', 'Opción 3'] : undefined,
    };
    setFields((prev) => [...prev, newField]);
    setSelectedFieldIndex(fields.length);
    toast.success(`Campo "${custom.label}" añadido`);
  };

  const updateField = (index: number, updates: Partial<FormStudioField>) => {
    setFields((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], ...updates };
      return copy;
    });
  };

  const removeField = (index: number) => {
    setFields((prev) => prev.filter((_, i) => i !== index));
    if (selectedFieldIndex === index) {
      setSelectedFieldIndex(null);
    } else if (selectedFieldIndex !== null && selectedFieldIndex > index) {
      setSelectedFieldIndex(selectedFieldIndex - 1);
    }
  };

  const moveField = (index: number, direction: 'up' | 'down') => {
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= fields.length) return;
    setFields((prev) => {
      const copy = [...prev];
      const temp = copy[index];
      copy[index] = copy[targetIndex];
      copy[targetIndex] = temp;
      return copy;
    });
    setSelectedFieldIndex(targetIndex);
  };

  const handleSave = async () => {
    if (fields.length === 0) {
      toast.error('El formulario debe contener al menos un campo');
      return;
    }

    setSaving(true);
    try {
      await apiFetch(`/evangelism/events/${eventId}/form`, {
        method: 'PUT',
        token,
        body: {
          name: formName || `Pre-registro: ${eventName}`,
          description: formDescription,
          fields,
          submit_button_text: submitButtonText,
          success_message: successMessage,
          is_active: true,
        },
      });
      toast.success('Formulario guardado exitosamente en Form Studio');
      if (onSaved) onSaved();
    } catch {
      toast.error('No se pudo guardar el formulario. Verifica la configuración.');
    } finally {
      setSaving(false);
    }
  };

  const activeField = selectedFieldIndex !== null ? fields[selectedFieldIndex] : null;

  return (
    <ErrorBoundary moduleName="Event Form Studio">
      <WorkspaceDrawer
        isOpen={isOpen}
        onClose={onClose}
        title="Event Form Studio"
        subtitle={`Diseñador de formulario para: ${eventName}`}
        actions={
          <div className="flex items-center gap-2">
            <DSButton variant="ghost" onClick={onClose} disabled={saving} className="text-xs">
              Cerrar
            </DSButton>
            <DSButton
              variant="primary"
              onClick={handleSave}
              disabled={saving}
              className="bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center gap-1.5 text-xs font-bold"
            >
              {saving ? 'Guardando...' : 'Guardar Formulario'} <Save size={14} />
            </DSButton>
          </div>
        }
      >
        <div className="space-y-4">
          {/* Navegación de pestañas: Diseñador vs Live Preview */}
          <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-2">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setActiveTab('editor')}
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wide flex items-center gap-1.5 transition-all',
                  activeTab === 'editor'
                    ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-md'
                    : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                )}
              >
                <Settings size={14} /> Diseñador ({fields.length} campos)
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('preview')}
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wide flex items-center gap-1.5 transition-all',
                  activeTab === 'preview'
                    ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-md'
                    : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                )}
              >
                <Eye size={14} /> Vista Previa en Vivo
              </button>
            </div>
            <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
              100% RightPanel Super-PRO
            </span>
          </div>

          {loading ? (
            <div className="p-12 text-center text-sm font-semibold text-[hsl(var(--text-secondary))] animate-pulse">
              Cargando estructura del formulario...
            </div>
          ) : activeTab === 'editor' ? (
            <div className="space-y-4">
              {/* Bloques preconfigurados rápidos (1 click) */}
              <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3 space-y-2">
                <div className="flex items-center gap-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary))]">
                  <Sparkles size={14} /> Bloques Canónicos Preconfigurados (1 Clic)
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {PRESET_BLOCKS.map((preset) => {
                    const IconComponent = preset.icon;
                    return (
                      <button
                        key={preset.id}
                        type="button"
                        onClick={() => addPresetBlock(preset)}
                        className="flex items-center gap-2 p-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.05)] text-left transition-all group"
                      >
                        <div className="w-6 h-6 rounded bg-[hsl(var(--surface-2))] group-hover:bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] flex items-center justify-center shrink-0">
                          <IconComponent size={13} />
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-[hsl(var(--text-primary))] truncate">
                            {preset.title}
                          </p>
                          <p className="text-3xs text-[hsl(var(--text-secondary))] truncate">
                            {preset.field.required ? 'Obligatorio' : 'Opcional'}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Añadir campos personalizados */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mr-1">
                  Añadir Campo:
                </span>
                {CUSTOM_TYPES.map((custom) => {
                  const Icon = custom.icon;
                  return (
                    <button
                      key={custom.type}
                      type="button"
                      onClick={() => addCustomField(custom)}
                      className="px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary))] text-xs font-semibold text-[hsl(var(--text-primary))] flex items-center gap-1.5 transition-all shadow-sm"
                    >
                      <Icon size={13} className="text-[hsl(var(--primary))]" /> {custom.label}
                    </button>
                  );
                })}
              </div>

              {/* Lista de Campos y Editor Lateral */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                {/* Columna Izquierda: Estructura de campos ordenable */}
                <div className="lg:col-span-6 space-y-2">
                  <div className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center justify-between">
                    <span>Campos del Formulario ({fields.length})</span>
                    <span>Orden</span>
                  </div>

                  {fields.length === 0 ? (
                    <div className="p-8 border border-dashed border-[hsl(var(--border))] rounded-lg text-center text-xs text-[hsl(var(--text-secondary))]">
                      No hay campos añadidos. Haz clic en un bloque de arriba para empezar.
                    </div>
                  ) : (
                    fields.map((field, idx) => {
                      const isSelected = selectedFieldIndex === idx;
                      return (
                        <div
                          key={field.id + idx}
                          onClick={() => setSelectedFieldIndex(idx)}
                          className={clsx(
                            'p-3 rounded-lg border flex items-center justify-between gap-3 cursor-pointer transition-all',
                            isSelected
                              ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.04)] shadow-sm'
                              : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--border-strong))]'
                          )}
                        >
                          <div className="min-w-0 flex items-center gap-2">
                            <span className="w-5 h-5 rounded-full bg-[hsl(var(--surface-2))] text-2xs font-bold flex items-center justify-center text-[hsl(var(--text-secondary))] shrink-0">
                              {idx + 1}
                            </span>
                            <div className="min-w-0">
                              <p className="text-xs font-bold text-[hsl(var(--text-primary))] truncate">
                                {field.label}
                              </p>
                              <div className="flex items-center gap-2 text-3xs text-[hsl(var(--text-secondary))]">
                                <span className="uppercase font-semibold">{field.type}</span>
                                <span>•</span>
                                <span className={field.required ? 'text-[hsl(var(--primary))] font-bold' : ''}>
                                  {field.required ? 'Requerido' : 'Opcional'}
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                            <button
                              type="button"
                              disabled={idx === 0}
                              onClick={() => moveField(idx, 'up')}
                              className="p-1 rounded hover:bg-[hsl(var(--surface-2))] disabled:opacity-30 text-[hsl(var(--text-secondary))]"
                              title="Mover arriba"
                            >
                              <ArrowUp size={13} />
                            </button>
                            <button
                              type="button"
                              disabled={idx === fields.length - 1}
                              onClick={() => moveField(idx, 'down')}
                              className="p-1 rounded hover:bg-[hsl(var(--surface-2))] disabled:opacity-30 text-[hsl(var(--text-secondary))]"
                              title="Mover abajo"
                            >
                              <ArrowDown size={13} />
                            </button>
                            <button
                              type="button"
                              onClick={() => removeField(idx)}
                              className="p-1 rounded hover:bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))] ml-1"
                              title="Eliminar campo"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

                {/* Columna Derecha: Inspector / Editor de propiedades del campo seleccionado */}
                <div className="lg:col-span-6 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 space-y-3">
                  <div className="border-b border-[hsl(var(--border))] pb-2 flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--text-primary))]">
                      Propiedades del Campo
                    </span>
                    {activeField && (
                      <span className="text-3xs uppercase px-2 py-0.5 rounded bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] font-bold">
                        Tipo: {activeField.type}
                      </span>
                    )}
                  </div>

                  {activeField && selectedFieldIndex !== null ? (
                    <div className="space-y-3 animate-in fade-in duration-200">
                      <div className="space-y-1">
                        <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                          Etiqueta (Pregunta / Título) *
                        </label>
                        <DSInput
                          value={activeField.label}
                          onChange={(e) => updateField(selectedFieldIndex, { label: e.target.value })}
                          className="w-full text-xs font-bold"
                          placeholder="Ej. ¿En qué ciudad resides?"
                        />
                      </div>

                      {activeField.type !== 'checkbox' && (
                        <div className="space-y-1">
                          <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            Texto de Ayuda / Placeholder
                          </label>
                          <DSInput
                            value={activeField.placeholder || ''}
                            onChange={(e) => updateField(selectedFieldIndex, { placeholder: e.target.value })}
                            className="w-full text-xs"
                            placeholder="Ej. Ingresa tu respuesta aquí..."
                          />
                        </div>
                      )}

                      {/* Switch de Obligatoriedad */}
                      <div className="flex items-center justify-between p-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]">
                        <div>
                          <p className="text-xs font-bold text-[hsl(var(--text-primary))]">Respuesta Obligatoria</p>
                          <p className="text-2xs text-[hsl(var(--text-secondary))]">
                            El usuario no podrá inscribirse sin responder este campo
                          </p>
                        </div>
                        <input
                          type="checkbox"
                          checked={Boolean(activeField.required)}
                          onChange={(e) => updateField(selectedFieldIndex, { required: e.target.checked })}
                          className="rounded border-[hsl(var(--border))] text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))]"
                        />
                      </div>

                      {/* Opciones para Select */}
                      {activeField.type === 'select' && (
                        <div className="space-y-1.5 pt-2 border-t border-[hsl(var(--border))]">
                          <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            Opciones del Menú Desplegable (una por línea)
                          </label>
                          <textarea
                            rows={4}
                            value={(activeField.options || []).join('\n')}
                            onChange={(e) =>
                              updateField(selectedFieldIndex, {
                                options: e.target.value.split('\n').filter((opt) => opt.trim().length > 0),
                              })
                            }
                            className="w-full p-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] font-mono"
                            placeholder="Opción 1&#10;Opción 2&#10;Opción 3"
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-8 text-center text-xs text-[hsl(var(--text-secondary))]">
                      Selecciona un campo a la izquierda para editar sus propiedades.
                    </div>
                  )}
                </div>
              </div>

              {/* Configuración global del formulario */}
              <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3 space-y-2">
                <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-primary))]">
                  Textos y Mensajes de Confirmación
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-3xs uppercase font-semibold text-[hsl(var(--text-secondary))]">
                      Texto del Botón de Envío
                    </label>
                    <DSInput
                      value={submitButtonText}
                      onChange={(e) => setSubmitButtonText(e.target.value)}
                      className="w-full text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-3xs uppercase font-semibold text-[hsl(var(--text-secondary))]">
                      Mensaje de Éxito al Finalizar
                    </label>
                    <DSInput
                      value={successMessage}
                      onChange={(e) => setSuccessMessage(e.target.value)}
                      className="w-full text-xs"
                    />
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* Vista Previa en Vivo Interactiva */
            <div className="max-w-md mx-auto rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-xl p-6 space-y-5 animate-in fade-in duration-300">
              <div className="text-center space-y-1 border-b border-[hsl(var(--border))] pb-4">
                <span className="px-2.5 py-0.5 rounded-full text-3xs font-bold uppercase bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
                  Vista Previa en Vivo
                </span>
                <h3 className="text-base font-bold text-[hsl(var(--text-primary))]">{formName}</h3>
                <p className="text-xs text-[hsl(var(--text-secondary))]">{formDescription}</p>
              </div>

              <div className="space-y-4">
                {fields.map((field) => (
                  <div key={field.id} className="space-y-1">
                    <label className="block text-xs font-semibold text-[hsl(var(--text-primary))]">
                      {field.label} {field.required && <span className="text-[hsl(var(--destructive))]">*</span>}
                    </label>

                    {field.type === 'textarea' ? (
                      <textarea
                        rows={3}
                        placeholder={field.placeholder || ''}
                        disabled
                        className="w-full p-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--text-secondary))] resize-none"
                      />
                    ) : field.type === 'select' ? (
                      <select
                        disabled
                        className="w-full p-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--text-secondary))]"
                      >
                        <option value="">Selecciona una opción...</option>
                        {(field.options || []).map((opt, i) => (
                          <option key={i} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    ) : field.type === 'checkbox' ? (
                      <div className="flex items-center gap-2 pt-1">
                        <input type="checkbox" disabled className="rounded border-[hsl(var(--border))]" />
                        <span className="text-xs text-[hsl(var(--text-secondary))]">{field.label}</span>
                      </div>
                    ) : (
                      <input
                        type={field.type === 'date' ? 'date' : field.type === 'email' ? 'email' : 'text'}
                        placeholder={field.placeholder || ''}
                        disabled
                        className="w-full p-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--text-secondary))]"
                      />
                    )}
                  </div>
                ))}
              </div>

              <button
                type="button"
                disabled
                className="w-full py-2.5 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] font-bold text-xs uppercase tracking-wide opacity-80 cursor-not-allowed shadow-md"
              >
                {submitButtonText}
              </button>
            </div>
          )}
        </div>
      </WorkspaceDrawer>
    </ErrorBoundary>
  );
}
