"use client";

import React from "react";
import { ArrowDown, ArrowUp, Copy, Plus, Trash2, X } from "lucide-react";
import type { CmsFormConditionOperator, CmsFormField, CmsFormFieldType } from "@/types/cms-v2";

export const FIELD_TYPES: { type: CmsFormFieldType; label: string; description: string }[] = [
  { type: "text", label: "Texto corto", description: "Campo de texto de una sola línea" },
  { type: "email", label: "Correo electrónico", description: "Campo validado para e-mail" },
  { type: "phone", label: "Teléfono", description: "Campo para número de contacto" },
  { type: "textarea", label: "Texto largo", description: "Área de texto multilínea" },
  { type: "select", label: "Lista desplegable", description: "Selección única de opciones" },
  { type: "radio", label: "Botones de opción", description: "Opción única en grupo" },
  { type: "select_multiple", label: "Selección múltiple", description: "Varias opciones en casillas" },
  { type: "checkbox", label: "Casilla de verificación", description: "Casilla de aceptación / confirmación" },
  { type: "number", label: "Número", description: "Campo numérico con rango opcional" },
  { type: "rating", label: "Calificación (estrellas)", description: "Escala visual de 1 a N estrellas" },
  { type: "slider", label: "Deslizador", description: "Barra de rango numérico" },
  { type: "date", label: "Fecha", description: "Selector de fecha" },
  { type: "datetime", label: "Fecha y hora", description: "Selector de fecha con hora" },
  { type: "url", label: "Enlace URL", description: "Campo validado para http(s)" },
  { type: "file", label: "Archivo adjunto", description: "Carga de archivo (metadatos)" },
  { type: "section", label: "Encabezado de sección", description: "Título que agrupa campos" },
  { type: "divider", label: "Separador", description: "Línea divisoria visual" },
  { type: "page", label: "Salto de página", description: "Inicia un nuevo paso (formulario multi-paso)" },
  { type: "captcha", label: "Captcha (placeholder)", description: "Marcador de posición para el captcha" },
];

const OPTION_TYPES: ReadonlySet<string> = new Set(["select", "radio", "select_multiple"]);
const TEXT_TYPES: ReadonlySet<string> = new Set(["text", "textarea", "email"]);
const NUMERIC_TYPES: ReadonlySet<string> = new Set(["number", "rating", "slider"]);
const META_TYPES: ReadonlySet<string> = new Set(["section", "divider", "page", "captcha"]);

const CONDITION_OPERATORS: { value: CmsFormConditionOperator; label: string; needsValue?: boolean }[] = [
  { value: "eq", label: "es igual a", needsValue: true },
  { value: "neq", label: "no es igual a", needsValue: true },
  { value: "in", label: "está en (lista)", needsValue: true },
  { value: "not_in", label: "no está en (lista)", needsValue: true },
  { value: "contains", label: "contiene", needsValue: true },
  { value: "gt", label: "mayor que", needsValue: true },
  { value: "lt", label: "menor que", needsValue: true },
  { value: "gte", label: "mayor o igual que", needsValue: true },
  { value: "lte", label: "menor o igual que", needsValue: true },
  { value: "checked", label: "está marcado" },
  { value: "not_checked", label: "no está marcado" },
  { value: "empty", label: "está vacío" },
  { value: "not_empty", label: "no está vacío" },
];

function defaultLabelFor(type: CmsFormFieldType): string {
  switch (type) {
    case "email":
      return "Correo electrónico";
    case "phone":
      return "Teléfono de contacto";
    case "textarea":
      return "Mensaje";
    case "checkbox":
      return "Acepto los términos y condiciones";
    case "select":
      return "Selecciona una opción";
    case "radio":
      return "Selecciona una opción";
    case "select_multiple":
      return "Selecciona las opciones";
    case "number":
      return "Cantidad";
    case "date":
      return "Fecha";
    case "datetime":
      return "Fecha y hora";
    case "url":
      return "Sitio web";
    case "rating":
      return "Tu calificación";
    case "slider":
      return "Nivel de satisfacción";
    case "file":
      return "Adjunta un archivo";
    case "section":
      return "Encabezado de sección";
    case "divider":
      return "";
    case "page":
      return "Paso siguiente";
    case "captcha":
      return "Verificación de seguridad";
    default:
      return "Nuevo campo";
  }
}

export function makeDefaultField(type: CmsFormFieldType, seq: number): CmsFormField {
  const base: CmsFormField = {
    id: `f_${Date.now()}_${seq}`,
    type,
    label: defaultLabelFor(type),
    placeholder: "",
    required: type !== "divider" && type !== "section" && type !== "page" && type !== "captcha",
  };
  if (type === "divider" && !base.label) {
    base.label = "Separador";
  }
  if (OPTION_TYPES.has(type)) {
    base.options = ["Opción 1", "Opción 2"];
  }
  if (type === "rating") {
    base.max_value = 5;
  }
  if (type === "slider") {
    base.min_value = 0;
    base.max_value = 100;
    base.step = 1;
  }
  if (type === "file") {
    base.max_file_mb = 10;
  }
  return base;
}

const inputCls =
  "w-full px-2.5 py-1.5 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none";

interface FieldEditorProps {
  field: CmsFormField;
  index: number;
  total: number;
  siblings: CmsFormField[];
  onChange: (field: CmsFormField) => void;
  onRemove: () => void;
  onMove: (direction: "up" | "down") => void;
  onDuplicate?: () => void;
  dragHandle?: React.ReactNode;
}

export function FieldEditor({
  field,
  index,
  total,
  siblings,
  onChange,
  onRemove,
  onMove,
  onDuplicate,
  dragHandle,
}: FieldEditorProps) {
  const typeLabel = FIELD_TYPES.find((t) => t.type === field.type)?.label || field.type;
  const update = (patch: Partial<CmsFormField>) => onChange({ ...field, ...patch });

  // Campo condicionable: los "meta" (section/divider/page/captcha) no pueden
  // ser destino de una condición.
  const conditionTargets = siblings.filter(
    (f) => f.id !== field.id && !META_TYPES.has(f.type) && f.type !== "file",
  );

  const hasCondition = !!field.visible_if;
  const needsConditionValue = !!(
    field.visible_if &&
    ["eq", "neq", "gt", "lt", "gte", "lte", "contains"].includes(field.visible_if.operator)
  );
  const needsConditionList = !!field.visible_if && (field.visible_if.operator === "in" || field.visible_if.operator === "not_in");

  return (
    <div className="p-4 bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm space-y-3 relative group">
      <div className="flex items-center justify-between gap-2 border-b border-zinc-100 dark:border-zinc-800 pb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
          Campo #{index + 1} — {typeLabel}
        </span>

        <div className="flex items-center gap-1">
          {dragHandle}
          {onDuplicate && (
            <button
              type="button"
              onClick={onDuplicate}
              className="p-1 text-zinc-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
              title="Duplicar campo"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            type="button"
            onClick={() => onMove("up")}
            disabled={index === 0}
            className="p-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 disabled:opacity-30"
            title="Mover arriba"
          >
            <ArrowUp className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => onMove("down")}
            disabled={index === total - 1}
            className="p-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 disabled:opacity-30"
            title="Mover abajo"
          >
            <ArrowDown className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={onRemove}
            className="p-1 text-zinc-400 hover:text-red-600 transition-colors ml-1"
            title="Eliminar campo"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {field.type === "divider" ? (
        <p className="text-xs text-zinc-400 italic">Separador visual — sin configuración adicional.</p>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                {META_TYPES.has(field.type) ? "Título" : "Etiqueta / Título"} *
              </label>
              <input
                type="text"
                required
                value={field.label}
                onChange={(e) => update({ label: e.target.value })}
                className={inputCls}
              />
            </div>

            {!META_TYPES.has(field.type) && field.type !== "checkbox" && field.type !== "page" && (
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                  Texto de marca de agua (Placeholder)
                </label>
                <input
                  type="text"
                  value={field.placeholder || ""}
                  onChange={(e) => update({ placeholder: e.target.value })}
                  className={inputCls}
                />
              </div>
            )}
          </div>

          {field.type === "checkbox" && (
            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Texto de la casilla</label>
              <input
                type="text"
                value={field.label}
                onChange={(e) => update({ label: e.target.value })}
                className={inputCls}
              />
            </div>
          )}

          {OPTION_TYPES.has(field.type) && (
            <div className="space-y-2 pt-1">
              <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Opciones *</label>
              <div className="space-y-1.5">
                {(field.options || []).map((opt, optIdx) => (
                  <div key={optIdx} className="flex items-center gap-2">
                    <input
                      type="text"
                      value={opt}
                      onChange={(e) => {
                        const options = [...(field.options || [])];
                        options[optIdx] = e.target.value;
                        update({ options: options.filter((o) => o !== undefined) });
                      }}
                      className={inputCls}
                      aria-label={`Opción ${optIdx + 1}`}
                    />
                    <button
                      type="button"
                      onClick={() =>
                        update({ options: (field.options || []).filter((_, i) => i !== optIdx) })
                      }
                      className="p-1 text-zinc-400 hover:text-red-600 transition-colors shrink-0"
                      title="Eliminar opción"
                      aria-label={`Eliminar opción ${optIdx + 1}`}
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={() => update({ options: [...(field.options || []), "Nueva opción"] })}
                className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/40 rounded-lg transition-colors"
              >
                <Plus className="w-3.5 h-3.5" /> Agregar opción
              </button>
              <label className="flex items-center gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={!!field.allow_other}
                  onChange={(e) => update({ allow_other: e.target.checked })}
                  className="w-3.5 h-3.5 text-blue-600 rounded focus:ring-blue-500"
                />
                Permitir respuesta libre (&ldquo;Otra opción&rdquo;)
              </label>
            </div>
          )}

          {TEXT_TYPES.has(field.type) && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Mín. caracteres</label>
                <input
                  type="number"
                  min={0}
                  value={field.min_length ?? ""}
                  onChange={(e) =>
                    update({ min_length: e.target.value === "" ? undefined : Number(e.target.value) })
                  }
                  className={inputCls}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Máx. caracteres</label>
                <input
                  type="number"
                  min={0}
                  value={field.max_length ?? ""}
                  onChange={(e) =>
                    update({ max_length: e.target.value === "" ? undefined : Number(e.target.value) })
                  }
                  className={inputCls}
                />
              </div>
              <div className="space-y-1 sm:col-span-1">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Patrón (regex)</label>
                <input
                  type="text"
                  placeholder="^[A-Za-z]+$"
                  value={field.regex_pattern || ""}
                  onChange={(e) => update({ regex_pattern: e.target.value || undefined })}
                  className={inputCls}
                />
              </div>
              {field.regex_pattern && (
                <div className="space-y-1 sm:col-span-3">
                  <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                    Mensaje de error del patrón
                  </label>
                  <input
                    type="text"
                    value={field.regex_message || ""}
                    onChange={(e) => update({ regex_message: e.target.value || undefined })}
                    className={inputCls}
                  />
                </div>
              )}
            </div>
          )}

          {NUMERIC_TYPES.has(field.type) && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Valor mín.</label>
                <input
                  type="number"
                  value={field.min_value ?? ""}
                  onChange={(e) =>
                    update({ min_value: e.target.value === "" ? undefined : Number(e.target.value) })
                  }
                  className={inputCls}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Valor máx.</label>
                <input
                  type="number"
                  value={field.max_value ?? ""}
                  onChange={(e) =>
                    update({ max_value: e.target.value === "" ? undefined : Number(e.target.value) })
                  }
                  className={inputCls}
                />
              </div>
              {field.type === "slider" && (
                <div className="space-y-1">
                  <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Paso</label>
                  <input
                    type="number"
                    min={1}
                    value={field.step ?? ""}
                    onChange={(e) =>
                      update({ step: e.target.value === "" ? undefined : Number(e.target.value) })
                    }
                    className={inputCls}
                  />
                </div>
              )}
            </div>
          )}

          {field.type === "file" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                  Máx. tamaño (MB)
                </label>
                <input
                  type="number"
                  min={1}
                  value={field.max_file_mb ?? ""}
                  onChange={(e) =>
                    update({ max_file_mb: e.target.value === "" ? undefined : Number(e.target.value) })
                  }
                  className={inputCls}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                  Tipos permitidos (MIME)
                </label>
                <input
                  type="text"
                  placeholder="image/*, application/pdf"
                  value={field.accept || ""}
                  onChange={(e) => update({ accept: e.target.value || undefined })}
                  className={inputCls}
                />
              </div>
            </div>
          )}

          {field.type === "section" && (
            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Descripción</label>
              <input
                type="text"
                value={field.helper_text || ""}
                onChange={(e) => update({ helper_text: e.target.value || undefined })}
                className={inputCls}
              />
            </div>
          )}

          {!META_TYPES.has(field.type) && (
            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Texto de ayuda</label>
              <input
                type="text"
                value={field.helper_text || ""}
                onChange={(e) => update({ helper_text: e.target.value || undefined })}
                className={inputCls}
              />
            </div>
          )}

          {/* Visible if (condicionales) */}
          {!META_TYPES.has(field.type) && field.type !== "page" && conditionTargets.length > 0 && (
            <div className="space-y-2 pt-1 border-t border-zinc-100 dark:border-zinc-800">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Mostrar solo si…
                </label>
                <label className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={hasCondition}
                    onChange={(e) => update({ visible_if: e.target.checked ? { field_id: conditionTargets[0].id, operator: "eq", value: "" } : undefined })}
                    className="w-3.5 h-3.5 text-blue-600 rounded focus:ring-blue-500"
                  />
                  Activar condición
                </label>
              </div>

              {hasCondition && field.visible_if && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <select
                    value={field.visible_if.field_id}
                    onChange={(e) => update({ visible_if: { ...field.visible_if!, field_id: e.target.value } })}
                    className={inputCls}
                  >
                    {conditionTargets.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.label || f.id}
                      </option>
                    ))}
                  </select>
                  <select
                    value={field.visible_if.operator}
                    onChange={(e) =>
                      update({
                        visible_if: {
                          ...field.visible_if!,
                          operator: e.target.value as CmsFormConditionOperator,
                          value: ["checked", "not_checked", "empty", "not_empty"].includes(e.target.value)
                            ? undefined
                            : field.visible_if!.value ?? "",
                        },
                      })
                    }
                    className={inputCls}
                  >
                    {CONDITION_OPERATORS.map((op) => (
                      <option key={op.value} value={op.value}>
                        {op.label}
                      </option>
                    ))}
                  </select>
                  {needsConditionValue && (
                    <input
                      type="text"
                      value={String(field.visible_if.value ?? "")}
                      onChange={(e) => update({ visible_if: { ...field.visible_if!, value: e.target.value } })}
                      className={inputCls}
                      placeholder="Valor"
                    />
                  )}
                  {needsConditionList && (
                    <input
                      type="text"
                      value={Array.isArray(field.visible_if.value) ? field.visible_if.value.join(", ") : ""}
                      onChange={(e) =>
                        update({
                          visible_if: {
                            ...field.visible_if!,
                            value: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                          },
                        })
                      }
                      className={`${inputCls} sm:col-span-3`}
                      placeholder="Valores separados por coma"
                    />
                  )}
                </div>
              )}
            </div>
          )}

          {!META_TYPES.has(field.type) && (
            <div className="flex items-center pt-1">
              <label className="flex items-center gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={field.required}
                  onChange={(e) => update({ required: e.target.checked })}
                  className="w-3.5 h-3.5 text-blue-600 rounded focus:ring-blue-500"
                />
                Campo obligatorio
              </label>
            </div>
          )}
        </>
      )}
    </div>
  );
}
