"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronLeft, ChevronRight, Loader2, Star } from "lucide-react";
import { ApiError, extractErrorMessage } from "@/lib/http";
import type { CmsFormField, CmsFormPublicRead } from "@/types/cms-v2";

/* eslint-disable react/no-unescaped-entities */

// ── Reglas de validación (espejo de backend.services.form_validation) ───────

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const URL_RE = /^https?:\/\/[^\s/$.?#].[^\s]*$/i;
const PHONE_RE = /^[+]?[\d\s\-().]{6,20}$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const DATETIME_RE = /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?)?$/;

const META_TYPES: ReadonlySet<string> = new Set(["section", "page", "divider", "captcha"]);

export function isEmptyValue(v: unknown): boolean {
  if (v === null || v === undefined) return true;
  if (typeof v === "string" && !v.trim()) return true;
  if (Array.isArray(v) && v.length === 0) return true;
  if (typeof v === "object" && v !== null && Object.keys(v).length === 0) return true;
  return false;
}

export function isFieldVisible(field: CmsFormField, values: Record<string, unknown>): boolean {
  const cond = field.visible_if;
  if (!cond) return true;
  const target = values[cond.field_id];
  const ref = cond.value;
  switch (cond.operator) {
    case "eq":
      return target === ref;
    case "neq":
      return target !== ref;
    case "in":
      return Array.isArray(ref) && ref.includes(target);
    case "not_in":
      return !(Array.isArray(ref) && ref.includes(target));
    case "contains":
      return typeof target === "string" && typeof ref === "string" && target.includes(ref);
    case "gt":
      return toNum(target) > toNum(ref);
    case "lt":
      return toNum(target) < toNum(ref);
    case "gte":
      return toNum(target) >= toNum(ref);
    case "lte":
      return toNum(target) <= toNum(ref);
    case "checked":
      return target === true;
    case "not_checked":
      return target === false || target === undefined || target === null;
    case "empty":
      return isEmptyValue(target);
    case "not_empty":
      return !isEmptyValue(target);
    default:
      return true;
  }
}

function toNum(v: unknown): number {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isNaN(n) ? Number.NEGATIVE_INFINITY : n;
}

/** Valida el valor de un campo visible. Devuelve mensaje de error o null. */
export function validateFieldValue(field: CmsFormField, value: unknown): string | null {
  const ftype = field.type;
  if (isEmptyValue(value)) return null;

  if (ftype === "text" || ftype === "textarea") {
    const v = String(value).trim();
    if (field.min_length !== undefined && v.length < field.min_length) {
      return `Debe tener al menos ${field.min_length} caracteres`;
    }
    if (field.max_length !== undefined && v.length > field.max_length) {
      return `No puede exceder ${field.max_length} caracteres`;
    }
    if (field.regex_pattern) {
      try {
        if (!new RegExp(field.regex_pattern).test(v)) {
          return field.regex_message || "El valor no cumple el patrón esperado";
        }
      } catch {
        /* patrón roto — se ignora en cliente */
      }
    }
    return null;
  }
  if (ftype === "email") {
    const v = String(value).trim();
    if (!EMAIL_RE.test(v)) return "Ingresa un correo electrónico válido";
    return null;
  }
  if (ftype === "phone") {
    const v = String(value).trim();
    if (!PHONE_RE.test(v)) return "Ingresa un teléfono válido";
    return null;
  }
  if (ftype === "url") {
    const v = String(value).trim();
    if (!URL_RE.test(v)) return "Ingresa una URL válida (http:// o https://)";
    return null;
  }
  if (ftype === "number") {
    const n = typeof value === "boolean" ? NaN : Number(value);
    if (Number.isNaN(n)) return "Ingresa un número válido";
    if (field.min_value !== undefined && n < field.min_value) return `Debe ser ≥ ${field.min_value}`;
    if (field.max_value !== undefined && n > field.max_value) return `Debe ser ≤ ${field.max_value}`;
    return null;
  }
  if (ftype === "date" || ftype === "datetime") {
    const v = String(value).trim();
    const pattern = ftype === "datetime" ? DATETIME_RE : DATE_RE;
    if (!pattern.test(v)) return "Fecha inválida (usa AAAA-MM-DD)";
    return null;
  }
  if (ftype === "checkbox") {
    return null;
  }
  if (ftype === "select" || ftype === "radio") {
    const v = String(value).trim();
    const options = field.options || [];
    if (!options.includes(v) && !(field.allow_other && v)) return "Selecciona una opción válida";
    return null;
  }
  if (ftype === "select_multiple") {
    const values = Array.isArray(value) ? value : String(value).split(",").map((s) => s.trim()).filter(Boolean);
    const options = field.options || [];
    for (const v of values) {
      if (!options.includes(String(v).trim()) && !(field.allow_other && String(v).trim())) {
        return `"${String(v).trim()}" no es una opción válida`;
      }
    }
    return null;
  }
  if (ftype === "rating" || ftype === "slider") {
    const n = Number(value);
    if (Number.isNaN(n)) return ftype === "rating" ? "Ingresa una calificación válida" : "Ingresa un valor válido";
    if (field.min_value !== undefined && n < field.min_value) return `Debe ser ≥ ${field.min_value}`;
    if (field.max_value !== undefined && n > field.max_value) return `Debe ser ≤ ${field.max_value}`;
    return null;
  }
  if (ftype === "file") {
    if (typeof value !== "object" || value === null) return "Archivo inválido";
    const file = value as { name?: string; mime?: string; size?: number };
    if (field.max_file_mb !== undefined && typeof file.size === "number" && file.size > field.max_file_mb * 1024 * 1024) {
      return `El archivo excede ${field.max_file_mb} MB`;
    }
    return null;
  }
  return null;
}

/**
 * Valida los campos visibles de un conjunto de campos.
 * Devuelve un mapa field_id → mensaje de error.
 */
export function validateFields(fields: CmsFormField[], values: Record<string, unknown>): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of fields) {
    if (META_TYPES.has(field.type)) continue;
    if (!isFieldVisible(field, values)) continue;
    const value = values[field.id];
    if (isEmptyValue(value)) {
      if (field.required) errors[field.id] = `El campo "${field.label}" es obligatorio`;
      continue;
    }
    const err = validateFieldValue(field, value);
    if (err) errors[field.id] = err;
  }
  return errors;
}

/** Divide los campos en pasos separados por campos tipo "page". */
export function buildSteps(fields: CmsFormField[]): CmsFormField[][] {
  const steps: CmsFormField[][] = [];
  let current: CmsFormField[] = [];
  for (const field of fields) {
    if (field.type === "page") {
      if (current.length) {
        steps.push(current);
        current = [];
      }
      continue;
    }
    current.push(field);
  }
  if (current.length) steps.push(current);
  return steps.length ? steps : [[]];
}

/** Datos limpios para submit: solo campos visibles con valor (sin meta). */
export function collectVisibleData(
  fields: CmsFormField[],
  values: Record<string, unknown>,
): Record<string, unknown> {
  const data: Record<string, unknown> = {};
  for (const field of fields) {
    if (META_TYPES.has(field.type)) continue;
    if (!isFieldVisible(field, values)) continue;
    const value = values[field.id];
    if (!isEmptyValue(value)) data[field.id] = value;
  }
  return data;
}

export interface CmsFormRendererApi {
  validateAll: () => boolean;
  getData: () => { data: Record<string, unknown>; captchaToken: string | null; hp: string | null };
}

type SubmitPayload = {
  data: Record<string, unknown>;
  captchaToken: string | null;
  hp: string | null;
};

interface CmsFormRendererProps {
  form: CmsFormPublicRead;
  /** Modo completo: el renderer gestiona el submit y muestra el mensaje de éxito. */
  onSubmit?: (payload: SubmitPayload) => Promise<void>;
  /** false para modo embebido (el padre controla el submit vía onReady). */
  showSubmit?: boolean;
  /** API imperativa para validación + recolección de datos (modo embebido). */
  onReady?: (api: CmsFormRendererApi) => void;
  /** Modo preview (admin): campos deshabilitados, sin captcha ni honeypot. */
  preview?: boolean;
  className?: string;
}

const INPUT_CLASS =
  "w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] focus:bg-[hsl(var(--bg-primary))] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-[hsl(var(--info)/100%)] outline-none font-medium text-[hsl(var(--text-primary))] transition-all placeholder:text-[hsl(var(--text-secondary))] placeholder:font-normal";

/** Representación legible de un valor para el resumen de revisión. */
function summarizeValue(field: CmsFormField, value: unknown): string {
  if (isEmptyValue(value)) return "—";
  if (field.type === "checkbox") return value === true ? "Sí" : "No";
  if (field.type === "select_multiple") {
    if (!Array.isArray(value)) return String(value);
    return (value as string[]).filter((v) => !String(v).startsWith("__other__")).join(", ");
  }
  if (field.type === "file") {
    const f = value as { name?: string };
    return f?.name || "Archivo";
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function SectionHeading({ field }: { field: CmsFormField }) {
  return (
    <div className="pt-2">
      <div className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{field.label}</div>
      {field.helper_text && (
        <p className="text-xs font-medium text-[hsl(var(--text-secondary))] mt-1">{field.helper_text}</p>
      )}
    </div>
  );
}

function Divider() {
  return <hr className="border-t border-[hsl(var(--border))]" />;
}

function FieldInput({
  field,
  value,
  onChange,
  onBlur,
  error,
  preview,
}: {
  field: CmsFormField;
  value: unknown;
  onChange: (value: unknown) => void;
  onBlur: () => void;
  error?: string;
  preview?: boolean;
}) {
  const disabled = preview;
  const hasError = !!error;
  const inputClass = `${INPUT_CLASS} ${hasError ? "!border-[hsl(var(--destructive))]" : ""}`;
  const labelId = `cms-form-${field.id}`;
  const helperId = `${labelId}-helper`;
  const errorId = `${labelId}-error`;
  const describedBy = `${field.helper_text ? helperId : ""} ${hasError ? errorId : ""}`.trim() || undefined;

  const commonA11y = {
    "aria-invalid": hasError || undefined,
    "aria-describedby": describedBy,
    "aria-required": field.required || undefined,
  };

  const renderInput = () => {
    switch (field.type) {
      case "text":
      case "email":
      case "phone":
      case "url":
        return (
          <input
            id={labelId}
            type={field.type === "phone" ? "tel" : field.type === "url" ? "url" : field.type}
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            placeholder={field.placeholder || ""}
            disabled={disabled}
            autoComplete={field.type === "email" ? "email" : field.type === "phone" ? "tel" : undefined}
            className={inputClass}
            {...commonA11y}
          />
        );
      case "textarea":
        return (
          <textarea
            id={labelId}
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            placeholder={field.placeholder || ""}
            disabled={disabled}
            rows={4}
            className={`${inputClass} resize-none`}
            {...commonA11y}
          />
        );
      case "number":
      case "slider":
        if (field.type === "slider") {
          const min = field.min_value ?? 0;
          const max = field.max_value ?? 100;
          const step = field.step ?? 1;
          const num = typeof value === "number" ? value : Number(value);
          return (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm font-semibold">
                <input
                  id={labelId}
                  type="range"
                  min={min}
                  max={max}
                  step={step}
                  value={Number.isNaN(num) ? min : num}
                  onChange={(e) => onChange(Number(e.target.value))}
                  onBlur={onBlur}
                  disabled={disabled}
                  className="w-full accent-[hsl(var(--primary))]"
                  {...commonA11y}
                />
                <span className="ml-3 tabular-nums text-[hsl(var(--text-primary))]">
                  {Number.isNaN(num) ? min : num}
                </span>
              </div>
            </div>
          );
        }
        return (
          <input
            id={labelId}
            type="number"
            min={field.min_value}
            max={field.max_value}
            step={field.step ?? "any"}
            value={typeof value === "number" ? value : (value as string) ?? ""}
            onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
            onBlur={onBlur}
            placeholder={field.placeholder || ""}
            disabled={disabled}
            className={inputClass}
            {...commonA11y}
          />
        );
      case "date":
      case "datetime":
        return (
          <input
            id={labelId}
            type={field.type === "datetime" ? "datetime-local" : "date"}
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            disabled={disabled}
            className={inputClass}
            {...commonA11y}
          />
        );
      case "checkbox":
        return (
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              id={labelId}
              type="checkbox"
              checked={value === true}
              onChange={(e) => onChange(e.target.checked)}
              onBlur={onBlur}
              disabled={disabled}
              className="mt-1 w-4 h-4 text-[hsl(var(--primary))] rounded focus:ring-[hsl(var(--primary))]"
              {...commonA11y}
            />
            <span className="text-sm font-medium text-[hsl(var(--text-secondary))] leading-relaxed">
              {field.label}
              {field.required && <span className="text-[hsl(var(--destructive))]"> *</span>}
            </span>
          </label>
        );
      case "select":
        return (
          <select
            id={labelId}
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            disabled={disabled}
            className={inputClass}
            {...commonA11y}
          >
            <option value="">{field.placeholder || "Selecciona una opción…"}</option>
            {(field.options || []).map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
            {field.allow_other && (
              <option value="__other__">Otra…</option>
            )}
          </select>
        );
      case "radio":
        return (
          <div className="space-y-2" role="radiogroup" aria-label={field.label} {...commonA11y}>
            {(field.options || []).map((opt) => (
              <label key={opt} className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  name={field.id}
                  value={opt}
                  checked={value === opt}
                  onChange={() => onChange(opt)}
                  onBlur={onBlur}
                  disabled={disabled}
                  className="w-4 h-4 text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))]"
                />
                <span className="text-sm font-medium text-[hsl(var(--text-secondary))]">{opt}</span>
              </label>
            ))}
            {field.allow_other && (
              <div className="flex items-center gap-3">
                <input
                  type="radio"
                  name={field.id}
                  value="__other__"
                  checked={typeof value === "string" && value.startsWith("__other__")}
                  onChange={() => onChange("__other__")}
                  onBlur={onBlur}
                  disabled={disabled}
                  className="w-4 h-4 text-[hsl(var(--primary))]"
                />
                <input
                  type="text"
                  placeholder="Otra…"
                  value={typeof value === "string" && value.startsWith("__other__") ? value.replace("__other__:", "") : ""}
                  onChange={(e) => onChange(`__other__:${e.target.value}`)}
                  onBlur={onBlur}
                  disabled={disabled}
                  className={inputClass}
                />
              </div>
            )}
          </div>
        );
      case "select_multiple":
        return (
          <div className="space-y-2" role="group" aria-label={field.label} {...commonA11y}>
            {(field.options || []).map((opt) => {
              const selected = Array.isArray(value) && value.includes(opt);
              return (
                <label key={opt} className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={(e) => {
                      const current = Array.isArray(value) ? [...(value as string[])] : [];
                      onChange(e.target.checked ? [...current, opt] : current.filter((v) => v !== opt));
                    }}
                    onBlur={onBlur}
                    disabled={disabled}
                    className="w-4 h-4 text-[hsl(var(--primary))] rounded focus:ring-[hsl(var(--primary))]"
                  />
                  <span className="text-sm font-medium text-[hsl(var(--text-secondary))]">{opt}</span>
                </label>
              );
            })}
            {field.allow_other && (
              <input
                type="text"
                placeholder="Otra opción…"
                value={
                  Array.isArray(value)
                    ? (value.filter((v) => v.startsWith("__other__")).join(",").replaceAll("__other__:", ""))
                    : ""
                }
                onChange={(e) => {
                  const others = e.target.value
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean)
                    .map((s) => `__other__:${s}`);
                  const current = Array.isArray(value) ? (value as string[]).filter((v) => !v.startsWith("__other__")) : [];
                  onChange([...current, ...others]);
                }}
                onBlur={onBlur}
                disabled={disabled}
                className={inputClass}
              />
            )}
          </div>
        );
      case "rating": {
        const max = field.max_value ?? 5;
        const num = typeof value === "number" ? value : 0;
        return (
          <div className="flex items-center gap-1.5" role="radiogroup" aria-label={field.label} {...commonA11y}>
            {Array.from({ length: max }, (_, i) => i + 1).map((n) => (
              <button
                key={n}
                type="button"
                disabled={disabled}
                onClick={() => onChange(n)}
                aria-label={`${n} de ${max}`}
                aria-checked={n === num}
                role="radio"
                className="focus:outline-none"
              >
                <Star
                  size={28}
                  className={`transition-colors ${n <= num ? "text-[hsl(var(--primary))] fill-[hsl(var(--primary))]" : "text-[hsl(var(--border))] fill-transparent"}`}
                />
              </button>
            ))}
            {num > 0 && <span className="ml-2 text-sm font-bold text-[hsl(var(--text-primary))]">{num}</span>}
          </div>
        );
      }
      case "file": {
        const fileName =
          typeof value === "object" && value !== null ? (value as { name?: string }).name : undefined;
        return (
          <label className={`flex items-center gap-3 cursor-pointer border border-dashed rounded-lg px-3 py-3 ${hasError ? "border-[hsl(var(--destructive))]" : "border-[hsl(var(--border))]"}`}>
            <input
              id={labelId}
              type="file"
              accept={field.accept}
              disabled={disabled}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (!f) {
                  onChange(null);
                  return;
                }
                onChange({ name: f.name, mime: f.type, size: f.size, url: "" });
              }}
              className="hidden"
              {...commonA11y}
            />
            <span className="text-sm font-medium text-[hsl(var(--text-secondary))]">
              {fileName || (field.placeholder || "Elige un archivo…")}
              {field.max_file_mb && ` (máx ${field.max_file_mb} MB)`}
            </span>
          </label>
        );
      }
      case "section":
        return <SectionHeading field={field} />;
      case "divider":
        return <Divider />;
      case "page":
      case "captcha":
      default:
        return null;
    }
  };

  if (field.type === "checkbox") return renderInput() as React.ReactElement;

  if (META_TYPES.has(field.type)) return renderInput() as React.ReactElement;

  return (
    <div className="space-y-1.5">
      <label htmlFor={labelId} className="block font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide text-xs">
        {field.label}
        {field.required && <span className="text-[hsl(var(--destructive))]"> *</span>}
      </label>
      {renderInput()}
      {hasError ? (
        <p id={errorId} role="alert" className="text-xs font-semibold text-[hsl(var(--destructive))]">{error}</p>
      ) : field.helper_text ? (
        <p id={helperId} className="text-xs font-medium text-[hsl(var(--text-secondary))]">{field.helper_text}</p>
      ) : null}
    </div>
  );
}

// ── hCaptcha widget (explicit render) ────────────────────────────────────────

let hcaptchaPromise: Promise<void> | null = null;

function loadHcaptchaScript(): Promise<void> {
  if (hcaptchaPromise) return hcaptchaPromise;
  hcaptchaPromise = new Promise((resolve, reject) => {
    const w = window as unknown as Record<string, unknown>;
    if (typeof w.hcaptcha === "object") {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = "https://js.hcaptcha.com/1/api.js?render=explicit";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      hcaptchaPromise = null;
      reject(new Error("No se pudo cargar el captcha"));
    };
    document.head.appendChild(script);
  });
  return hcaptchaPromise;
}

function HcaptchaWidget({
  siteKey,
  onToken,
  onReset,
  disabled,
}: {
  siteKey: string;
  onToken: (token: string | null) => void;
  onReset: () => void;
  disabled?: boolean;
}) {
  const widgetRef = useRef<HTMLDivElement>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const rendered = useRef(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await loadHcaptchaScript();
        if (cancelled || !widgetRef.current) return;
        const w = window as unknown as { hcaptcha: { render: (el: HTMLElement, opts: Record<string, unknown>) => string | number; reset: (id: string | number) => void } };
        if (rendered.current) return;
        w.hcaptcha.render(widgetRef.current, {
          sitekey: siteKey,
          callback: (token: string) => onToken(token),
          "expired-callback": () => {
            onToken(null);
            onReset();
          },
          "error-callback": () => setLoadError("Error al verificar el captcha. Inténtalo de nuevo."),
        });
        rendered.current = true;
      } catch {
        if (!cancelled) setLoadError("No se pudo cargar el captcha. Inténtalo de nuevo.");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteKey]);

  return (
    <div>
      <div
        ref={widgetRef}
        className={disabled ? "opacity-50 pointer-events-none" : ""}
        aria-hidden="true"
      />
      {loadError && <p className="text-xs font-semibold text-[hsl(var(--destructive))] mt-1">{loadError}</p>}
    </div>
  );
}

// ── Renderer ─────────────────────────────────────────────────────────────────

export default function CmsFormRenderer({
  form,
  onSubmit,
  showSubmit = true,
  onReady,
  preview = false,
  className,
}: CmsFormRendererProps) {
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [step, setStep] = useState(0);
  const [reviewMode, setReviewMode] = useState(false);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);

  const steps = useMemo(() => buildSteps(form.fields || []), [form.fields]);
  const currentFields = useMemo(() => steps[Math.min(step, steps.length - 1)] ?? [], [steps, step]);
  const isMultiStep = steps.length > 1;
  const isLastStep = step >= steps.length - 1;

  const handleChange = useCallback((fieldId: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [fieldId]: value }));
    setErrors((prev) => {
      if (!(fieldId in prev)) return prev;
      const next = { ...prev };
      delete next[fieldId];
      return next;
    });
  }, []);

  // Valida un solo campo al salir de él (feedback inline temprano).
  const handleBlur = useCallback(
    (fieldId: string) => {
      const field = (form.fields || []).find((f) => f.id === fieldId);
      if (!field || META_TYPES.has(field.type)) return;
      if (!isFieldVisible(field, values)) return;
      const value = values[fieldId];
      let err: string | null = null;
      if (isEmptyValue(value)) {
        if (field.required) err = `El campo "${field.label}" es obligatorio`;
      } else {
        err = validateFieldValue(field, value);
      }
      setErrors((prev) => {
        if (err) return { ...prev, [fieldId]: err };
        if (!(fieldId in prev)) return prev;
        const next = { ...prev };
        delete next[fieldId];
        return next;
      });
    },
    [form.fields, values]
  );

  const validateCurrent = useCallback(() => {
    const errs = validateFields(currentFields, values);
    setErrors((prev) => {
      const next = { ...prev };
      for (const k of Object.keys(next)) {
        if (currentFields.some((f) => f.id === k)) delete next[k];
      }
      return { ...next, ...errs };
    });
    return Object.keys(errs).length === 0;
  }, [currentFields, values]);

  const validateAll = useCallback(() => {
    const allFields = form.fields || [];
    const errs = validateFields(allFields, values);
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }, [form.fields, values]);

  const getData = useCallback(
    (): { data: Record<string, unknown>; captchaToken: string | null; hp: string | null } => {
      // El honeypot es un campo oculto que no pertenece a ``fields``; se
      // expone aparte (no dentro de ``data``, que valida estrictamente el
      // backend) solo si está rellenado (los bots lo llenan, los humanos no).
      const hpValue = form.honeypot_enabled && !isEmptyValue(values._hp) ? String(values._hp) : null;
      return { data: collectVisibleData(form.fields || [], values), captchaToken, hp: hpValue };
    },
    [form.fields, values, captchaToken, form.honeypot_enabled]
  );

  // Exponer la API imperativa (modo embebido).
  useEffect(() => {
    if (!onReady) return;
    onReady({ validateAll, getData });
  }, [onReady, validateAll, getData]);

  // Focus al primer campo con error tras validar / cambiar de paso.
  const containerRef = useRef<HTMLDivElement>(null);
  const focusFirstError = useCallback(() => {
    if (typeof document === "undefined") return;
    requestAnimationFrame(() => {
      const root = containerRef.current;
      if (!root) return;
      const firstInvalid = root.querySelector<HTMLElement>('[aria-invalid="true"]');
      firstInvalid?.focus();
    });
  }, []);

  const goToReview = () => {
    if (!validateCurrent()) {
      focusFirstError();
      return;
    }
    setReviewMode(true);
  };

  const handleNext = () => {
    if (!validateCurrent()) {
      focusFirstError();
      return;
    }
    setReviewMode(false);
    setStep((s) => Math.min(s + 1, steps.length - 1));
  };

  const handlePrev = () => {
    setReviewMode(false);
    setStep((s) => Math.max(s - 1, 0));
  };

  const goToStep = (target: number) => {
    if (target === step && !reviewMode) return;
    // Solo se permite navegar hacia atrás o al paso ya validado actual.
    if (target > step) return;
    setReviewMode(false);
    setStep(target);
  };

  const submitForm = async () => {
    if (preview) return;
    // Re-valida TODO antes de enviar (incluso pasos ya visitados).
    if (!validateAll()) {
      setReviewMode(false);
      // Vuelve al primer paso que tenga error.
      const firstErrField = form.fields?.find((f) => errors[f.id]);
      if (firstErrField) {
        const stepIdx = steps.findIndex((s) => s.some((f) => f.id === firstErrField.id));
        if (stepIdx >= 0) setStep(stepIdx);
      }
      focusFirstError();
      return;
    }
    if (form.captcha_enabled && !captchaToken) {
      setErrorMessage("Debes completar el captcha para continuar.");
      return;
    }
    if (!onSubmit) return;
    setStatus("loading");
    setErrorMessage(null);
    try {
      await onSubmit(getData());
      setStatus("success");
    } catch (err) {
      setStatus("error");
      if (err instanceof ApiError) {
        const detail = err.detail as { code?: string; detail?: string; field_id?: string } | undefined;
        if (detail?.code === "HONEYPOT_TRIGGERED" || detail?.code === "HONEYPOT") {
          setStatus("success");
          return;
        }
        // Error específico de un campo: mápalo a inline y vuelve al paso.
        if (detail?.field_id) {
          setErrors((prev) => ({ ...prev, [detail.field_id as string]: detail?.detail || "Valor inválido" }));
          setReviewMode(false);
          const field = form.fields?.find((f) => f.id === detail.field_id);
          if (field) {
            const stepIdx = steps.findIndex((s) => s.some((f) => f.id === field.id));
            if (stepIdx >= 0) setStep(stepIdx);
          }
          focusFirstError();
          return;
        }
        setErrorMessage(detail?.detail || extractErrorMessage(err, "Ocurrió un error al enviar el formulario."));
      } else {
        setErrorMessage(extractErrorMessage(err, "Ocurrió un error al enviar el formulario."));
      }
    }
  };

  const resetForm = () => {
    setValues({});
    setErrors({});
    setStep(0);
    setReviewMode(false);
    setStatus("idle");
    setCaptchaToken(null);
  };

  const reviewFields = useMemo(() => {
    return (form.fields || []).filter(
      (f) => !META_TYPES.has(f.type) && f.type !== "page" && isFieldVisible(f, values),
    );
  }, [form.fields, values]);

  if (status === "success") {
    return (
      <div className="flex flex-col items-center justify-center text-center space-y-3 py-8">
        <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
          <Check size={32} strokeWidth={3} />
        </div>
        <p className="text-base font-bold text-[hsl(var(--text-primary))]" role="status" aria-live="polite">
          {form.success_message || "¡Gracias! Tu respuesta fue enviada."}
        </p>
        {!preview && onSubmit && (
          <button
            type="button"
            onClick={resetForm}
            className="text-xs font-semibold text-[hsl(var(--primary))] hover:underline"
          >
            Enviar otra respuesta
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={className} ref={containerRef}>
      {form.description && (
        <p className="text-sm font-medium text-[hsl(var(--text-secondary))] mb-4">{form.description}</p>
      )}

      {/* Honeypot invisible */}
      <input
        type="text"
        name="_hp"
        value={preview ? "" : (values._hp as string) ?? ""}
        onChange={(e) => handleChange("_hp", e.target.value)}
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        className="hidden"
      />

      {reviewMode ? (
        // ── Vista de revisión final ──────────────────────────────────────────
        <div className="space-y-4">
          <div className="text-center pb-2 border-b border-[hsl(var(--border))]">
            <h3 className="text-base font-bold text-[hsl(var(--text-primary))]">Revisa tus respuestas</h3>
            <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">
              {isMultiStep ? `Paso ${steps.length} de ${steps.length} · ` : ""}Confirma antes de enviar.
            </p>
          </div>
          <dl className="space-y-2.5">
            {reviewFields.length === 0 ? (
              <p className="text-sm text-[hsl(var(--text-secondary))]">No hay campos completados.</p>
            ) : (
              reviewFields.map((f) => (
                <div key={f.id} className="flex items-start justify-between gap-3 text-sm">
                  <dt className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide text-xs pt-0.5 shrink-0 max-w-[40%]">
                    {f.label}
                  </dt>
                  <dd className="text-[hsl(var(--text-primary))] font-medium text-right break-words min-w-0 flex-1">
                    {summarizeValue(f, values[f.id])}
                  </dd>
                </div>
              ))
            )}
          </dl>

          {form.captcha_enabled && !preview && (
            <div className="pt-1">
              <HcaptchaWidget
                siteKey={form.captcha_site_key || ""}
                onToken={setCaptchaToken}
                onReset={() => setCaptchaToken(null)}
                disabled={status === "loading"}
              />
              {form.captcha_enabled && !captchaToken && errorMessage === "Debes completar el captcha para continuar." && (
                <p role="alert" className="text-xs font-semibold text-[hsl(var(--destructive))] mt-1">{errorMessage}</p>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {isMultiStep && (
            <div className="text-center text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1">
              Paso {step + 1} de {steps.length}
            </div>
          )}
          {currentFields.map((field) => {
            if (!isFieldVisible(field, values)) return null;
            const error = errors[field.id];
            return (
              <FieldInput
                key={field.id}
                field={field}
                value={values[field.id]}
                onChange={(v) => handleChange(field.id, v)}
                onBlur={() => handleBlur(field.id)}
                error={error}
                preview={preview}
              />
            );
          })}

          {form.captcha_enabled && !preview && !isMultiStep && (
            <div className="pt-1">
              <HcaptchaWidget
                siteKey={form.captcha_site_key || ""}
                onToken={setCaptchaToken}
                onReset={() => setCaptchaToken(null)}
                disabled={status === "loading"}
              />
              {form.captcha_enabled && !captchaToken && errorMessage === "Debes completar el captcha para continuar." && (
                <p role="alert" className="text-xs font-semibold text-[hsl(var(--destructive))] mt-1">{errorMessage}</p>
              )}
            </div>
          )}
        </div>
      )}

      {status === "error" && errorMessage && errorMessage !== "Debes completar el captcha para continuar." && (
        <div className="mt-4 p-4 bg-[hsl(var(--destructive)/10%)] text-[hsl(var(--destructive))] rounded-lg text-sm font-semibold flex items-start gap-3" role="alert" aria-live="assertive">
          <span>⚠</span> {errorMessage}
        </div>
      )}

      <div className="mt-5 flex items-center justify-between gap-3">
        {isMultiStep || reviewMode ? (
          <button
            type="button"
            onClick={handlePrev}
            disabled={step === 0 && !reviewMode}
            className="inline-flex items-center gap-1 px-4 py-2.5 rounded-lg border border-[hsl(var(--border))] text-sm font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] transition-colors disabled:opacity-40"
          >
            <ChevronLeft size={16} /> Anterior
          </button>
        ) : (
          <span />
        )}

        {showSubmit && !reviewMode && (
          <button
            type="button"
            onClick={isLastStep ? (isMultiStep ? goToReview : submitForm) : handleNext}
            disabled={status === "loading" || preview}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-white rounded-lg text-sm font-semibold uppercase tracking-wide shadow-lg shadow-black/10 transition-all disabled:opacity-60 flex-1 sm:flex-none justify-center"
          >
            {status === "loading" && <Loader2 size={16} className="animate-spin" />}
            {isLastStep
              ? (isMultiStep ? (<>Revisar <ChevronRight size={16} /></>) : (form.submit_button_text || "Enviar"))
              : (
                <>
                  Continuar <ChevronRight size={16} />
                </>
              )}
          </button>
        )}

        {showSubmit && reviewMode && (
          <button
            type="button"
            onClick={submitForm}
            disabled={status === "loading" || preview}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-white rounded-lg text-sm font-semibold uppercase tracking-wide shadow-lg shadow-black/10 transition-all disabled:opacity-60 flex-1 sm:flex-none justify-center"
          >
            {status === "loading" && <Loader2 size={16} className="animate-spin" />}
            {form.submit_button_text || "Enviar"}
          </button>
        )}
      </div>

      {isMultiStep && !reviewMode && (
        <div className="mt-4 flex items-center justify-center gap-1.5" role="group" aria-label="Indicador de pasos">
          {steps.map((_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => goToStep(i)}
              disabled={i > step}
              aria-label={`Ir al paso ${i + 1}`}
              aria-current={i === step ? "step" : undefined}
              title={`Paso ${i + 1}`}
              className={`h-1.5 rounded-full transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] disabled:cursor-not-allowed ${i === step ? "w-6 bg-[hsl(var(--primary))]" : i < step ? "w-1.5 bg-[hsl(var(--primary))]/60 hover:bg-[hsl(var(--primary))]" : "w-1.5 bg-[hsl(var(--border))]"}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
