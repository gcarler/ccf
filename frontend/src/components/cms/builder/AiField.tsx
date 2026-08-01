"use client";

import React, { useState } from "react";
import { Sparkles, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export type FieldType = "title" | "description" | "cta" | "body" | "general";

export interface AiFieldProps {
  label?: string;
  value?: string;
  onChange: (value: string) => void;
  isTextArea?: boolean;
  fieldType?: FieldType;
  suggestions?: string[];
  placeholder?: string;
  rows?: number;
  readOnly?: boolean;
  token?: string | null;
}

export const DEFAULT_PROMPT_SUGGESTIONS: Record<FieldType, string[]> = {
  title: [
    "Título atractivo",
    "Bienvenida inspiradora",
    "Encabezado claro",
    "Lema institucional",
  ],
  description: [
    "Descripción institucional",
    "Resumen de actividades",
    "Misión y visión",
    "Mensaje de bienvenida",
  ],
  cta: [
    "Llamado a la acción",
    "Invitación a conectar",
    "Únete a nuestra comunidad",
    "Inscríbete hoy",
  ],
  body: [
    "Explicación del ministerio",
    "Historia y visión",
    "Instrucciones de participación",
    "Mensaje inspirador",
  ],
  general: [
    "Redacción profesional",
    "Tono invitador",
    "Resumen claro",
  ],
};

export function cleanAiResponse(response: string): string {
  if (!response) return "";

  let cleaned = response.trim();
  let previous = "";

  for (let pass = 0; pass < 3 && cleaned !== previous; pass++) {
    previous = cleaned;
    cleaned = cleaned
      .replace(/^["'“”`«»]+|["'“”`«»]+$/g, "")
      .replace(/^#+\s*/gm, "")
      .replace(/(?:\*\*|\*)?(?:Título|Texto|Cuerpo|Respuesta|Title|Body|Response):\s*(?:\*\*|\*)?/gi, "")
      .replace(/^[*-+•]\s*/gm, "")
      .replace(/^["'“”`«»]+|["'“”`«»]+$/g, "")
      .trim();
  }

  return cleaned;
}

export default function AiField({
  label,
  value = "",
  onChange,
  isTextArea = false,
  fieldType = "general",
  suggestions,
  placeholder,
  rows = 4,
  readOnly = false,
  token: explicitToken,
}: AiFieldProps) {
  let authToken: string | null = null;
  try {
    const auth = useAuth();
    authToken = auth?.token ?? null;
  } catch {
    // Safe fallback when rendered outside AuthProvider
  }

  let activeToken = explicitToken !== undefined ? explicitToken : authToken;
  if (!activeToken && typeof window !== "undefined") {
    activeToken = sessionStorage.getItem("ccf_token");
  }

  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);

  const activeSuggestions =
    suggestions || DEFAULT_PROMPT_SUGGESTIONS[fieldType] || DEFAULT_PROMPT_SUGGESTIONS.general;

  const handleAi = async (customPrompt?: string) => {
    const targetPrompt = (customPrompt || prompt).trim();
    if (!targetPrompt) return;

    if (!activeToken) {
      toast.error("Error al conectar con la IA de la plataforma");
      return;
    }

    setLoading(true);
    try {
      const promptText = `Genera un ${
        isTextArea ? "texto corto de 2 o 3 párrafos" : "título llamativo"
      } sobre el siguiente tema: "${targetPrompt}". Devuelve directamente el texto sugerido sin saludos ni explicaciones.`;

      const res = await apiFetch<{ response: string }>("/system/ai/generate", {
        method: "POST",
        token: activeToken,
        body: {
          prompt: promptText,
          context: `Sección de página web. Rol: Redactor Creativo. Campo: ${label || fieldType}.`,
        },
      });

      if (res?.response) {
        const cleanText = cleanAiResponse(res.response);
        onChange(cleanText);
        toast.success("Contenido generado por la IA");
      } else {
        toast.error("Error al conectar con la IA de la plataforma");
      }
    } catch {
      toast.error("Error al conectar con la IA de la plataforma");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-1.5 my-2">
      {label && (
        <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
          {label}
        </label>
      )}

      {isTextArea ? (
        <textarea
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder || "Escribe el contenido..."}
          disabled={readOnly || loading}
          rows={rows}
          className="w-full p-2 text-xs border rounded bg-white dark:bg-black/20 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-white/10 focus:outline-none focus:border-primary disabled:opacity-50"
        />
      ) : (
        <input
          type="text"
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder || "Escribe aquí..."}
          disabled={readOnly || loading}
          className="w-full p-2 text-xs border rounded bg-white dark:bg-black/20 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-white/10 focus:outline-none focus:border-primary disabled:opacity-50"
        />
      )}

      <div className="flex flex-col gap-1.5 mt-1.5 p-2 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded">
        <div className="flex items-center justify-between">
          <span className="text-3xs font-semibold text-gray-600 dark:text-gray-400 flex items-center gap-1">
            <Sparkles size={10} className="text-amber-500" /> Redactar con IA
          </span>
        </div>

        {/* Quick-suggestion chips */}
        <div className="flex flex-wrap gap-1">
          {activeSuggestions.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setPrompt(chip);
                handleAi(chip);
              }}
              disabled={loading || readOnly}
              className="text-3xs px-2 py-0.5 bg-white dark:bg-black/30 hover:bg-primary/10 hover:text-primary border border-gray-200 dark:border-white/10 rounded transition-colors text-left truncate max-w-full disabled:opacity-50"
            >
              + {chip}
            </button>
          ))}
        </div>

        {/* Prompt input and action button */}
        <div className="flex gap-1 items-center mt-1">
          <input
            type="text"
            placeholder="Tema para la IA..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleAi();
              }
            }}
            disabled={loading || readOnly}
            className="flex-1 px-2 py-1 text-3xs border rounded bg-white dark:bg-black/20 border-gray-300 dark:border-white/10 text-gray-900 dark:text-gray-100 focus:outline-none disabled:opacity-50"
          />
          <button
            type="button"
            onClick={() => handleAi()}
            disabled={loading || !prompt.trim() || readOnly}
            className="px-2.5 py-1 bg-primary hover:bg-primary-hover text-white text-3xs font-semibold rounded disabled:opacity-50 transition-colors flex items-center gap-1 shrink-0"
          >
            {loading ? (
              <>
                <Loader2 size={10} className="animate-spin" />
                <span>Redactando...</span>
              </>
            ) : (
              <>
                <Sparkles size={10} className={loading ? "animate-pulse" : ""} />
                <span>Redactar IA</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export const AiTextInput = AiField;
