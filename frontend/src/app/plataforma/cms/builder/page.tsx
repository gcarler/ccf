"use client";

import React, { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { Puck, Config } from "@puckeditor/core";
import "@puckeditor/core/dist/index.css";
import { useSearchParams, useRouter } from "next/navigation";
import { LayoutPanelTop, ArrowLeft, Loader2, Palette, CheckCircle2, AlertTriangle, Save, ImageIcon, Trash2, Plus } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { canEditCms, canPublishCms } from "@/lib/cms/permissions";
import { listCmsSections, patchCmsSection, createCmsSection, deleteCmsSection, workflowCmsPage } from "@/lib/cms/v2";
import { apiFetch } from "@/lib/http";
import { SITE_KEY } from "@/lib/site-config";
import type { CmsTheme } from "@/types/cms-v2";
import { toast } from "sonner";
import { preserveSelectedMediaId, type SelectedMedia } from "./media-utils";
import MediaPicker from "@/components/cms/builder/MediaPicker";
import MediaPickerField, { setMediaPickerTrigger } from "@/components/cms/builder/MediaPickerField";
import CmsJsonMediaField from "@/components/cms/CmsJsonMediaField";
import AiField from "@/components/cms/builder/AiField";
import OptimizedImage from "@/components/ui/OptimizedImage";

export type SaveStatus = "saved" | "dirty" | "saving" | "error";

// The public routes use a few rich, page-specific section types (feed, about,
// policy_document, etc.) that are rendered by PublicSectionRenderer but are not
// part of the small native Puck form catalogue. Keep those sections editable by
// exposing their complete props as JSON instead of silently dropping them from
// the editor.
const JSON_EDITABLE_SECTION_TYPES = [
  "about",
  "feed",
  "team",
  "events_calendar",
  "policy_document",
  "welcome",
  "footer_config",
  "mobile_menu_config",
  "content_blocks",
  "newsletter",
  "contact_form",
  "course_grid",
  "locations_list",
  "testimonials_masonry",
] as const;

const NATIVE_PUCK_SECTION_TYPES = new Set([
  "hero",
  "rich_text",
  "cta_banner",
  "faq",
  "testimonials",
  "stats",
  "gallery",
  "cards",
]);

function serializeJsonProps(props: Record<string, unknown>): Record<string, unknown> {
  return {
    ...props,
    __cms_json: JSON.stringify(props, null, 2),
  };
}

function deserializePuckProps(props: Record<string, unknown>): Record<string, unknown> {
  const serialized = props.__cms_json;
  if (typeof serialized !== "string") {
    return props;
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(serialized);
  } catch {
    throw new Error("El contenido JSON de la sección no es válido");
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("El contenido JSON debe ser un objeto");
  }
  return parsed as Record<string, unknown>;
}

function SaveStatusBadge({ status }: { status: SaveStatus }) {
  switch (status) {
    case "saving":
      return (
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/20 text-2xs text-amber-500 font-medium">
          <Loader2 className="animate-spin" size={12} />
          <span>Guardando cambios...</span>
        </div>
      );
    case "dirty":
      return (
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-500/10 border border-blue-500/20 text-2xs text-blue-400 font-medium">
          <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" />
          <span>Sin guardar</span>
        </div>
      );
    case "error":
      return (
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-red-500/10 border border-red-500/20 text-2xs text-red-400 font-medium">
          <AlertTriangle size={12} />
          <span>Error al guardar</span>
        </div>
      );
    case "saved":
    default:
      return (
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-2xs text-emerald-400 font-medium">
          <CheckCircle2 size={12} />
          <span>Guardado en borrador</span>
        </div>
      );
  }
}


export default function PuckBuilderPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { token, user } = useAuth();
  const canEdit = canEditCms(user?.role);
  const canPublish = canPublishCms(user?.role);

  const siteKey = searchParams?.get("site") || SITE_KEY;
  const pageSlug = searchParams?.get("page") || "";
  const contentMode = searchParams?.get("mode") === "content";
  const heroMediaMode = searchParams?.get("mode") === "hero-media";

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [initialData, setInitialData] = useState<{ content: any[] }>({ content: [] });
  const [dbSections, setDbSections] = useState<any[]>([]);

  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");

  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const latestDataRef = useRef<{ content: any[] }>({ content: [] });
  const saveSequenceRef = useRef<number>(0);
  const latestCompletedSeqRef = useRef<number>(0);
  const saveQueueRef = useRef<Promise<void>>(Promise.resolve());
  const isInitialLoadRef = useRef<boolean>(true);
  const dbSectionsRef = useRef<any[]>([]);
  const savingRef = useRef<boolean>(false);

  useEffect(() => {
    dbSectionsRef.current = dbSections;
  }, [dbSections]);

  useEffect(() => {
    savingRef.current = saving;
  }, [saving]);
  
  // Theme state
  const [themeStyles, setThemeStyles] = useState<React.CSSProperties>({});
  const [themeName, setThemeName] = useState<string>("Por defecto");

  // MediaPicker state
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);
  const mediaPickerCallbackRef = useRef<((url: string) => void) | null>(null);
  const selectedMediaRef = useRef<SelectedMedia | null>(null);
  const [mediaPickerValue, setMediaPickerValue] = useState("");

  // Setup global trigger callback for Puck's custom field renderers
  useEffect(() => {
    setMediaPickerTrigger((onChange, currentValue) => {
      setMediaPickerValue(currentValue);
      mediaPickerCallbackRef.current = onChange;
      setMediaPickerOpen(true);
    });
    return () => {
      setMediaPickerTrigger(null);
    };
  }, []);

  // Load existing sections and site theme from the backend
  useEffect(() => {
    if (!token || !pageSlug) return;

    async function fetchData() {
      try {
        setLoading(true);
        const [sections, themeData] = await Promise.all([
          listCmsSections(siteKey, pageSlug, token),
          apiFetch<CmsTheme>(`/cms/v2/public/sites/${siteKey}/theme`, { method: "GET", silent: true }).catch(() => null),
        ]);

        setDbSections(sections || []);
        dbSectionsRef.current = sections || [];
        
        // Convert array of database sections to Puck's data schema
        const puckContent = (sections || []).map((sec: any) => ({
          type: sec.type,
          props: {
            ...(NATIVE_PUCK_SECTION_TYPES.has(sec.type)
              ? (sec.props_json || {})
              : serializeJsonProps(sec.props_json || {})),
            id: sec.id, // Store database ID in Puck block properties
          },
        }));

        setInitialData({ content: puckContent });
        latestDataRef.current = { content: puckContent };
        isInitialLoadRef.current = true;

        if (themeData?.tokens_json) {
          const vars: Record<string, string> = {};
          Object.entries(themeData.tokens_json).forEach(([k, v]) => {
            vars[k.startsWith("--") ? k : `--site-${k}`] = v;
          });
          setThemeStyles(vars as React.CSSProperties);
          setThemeName(themeData.name || "Por defecto");
        }
      } catch (err) {
        toast.error("Error al cargar las secciones o el tema de la página");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [token, siteKey, pageSlug]);

  // Dynamically memoize Puck configuration to inject token closure for the AI text inputs
  const puckConfig = useMemo<Config>(() => {
    const genericComponents = Object.fromEntries(
      JSON_EDITABLE_SECTION_TYPES.map((type) => [
        type,
        {
          label: `Contenido CMS (${type})`,
          fields: {
            __cms_json: {
              type: "custom",
              label: "Contenido editable (JSON)",
              render: ({ value, onChange }: any) => (
                <CmsJsonMediaField
                  label="Contenido editable (JSON)"
                  value={value || "{}"}
                  token={token}
                  allowThumbnailOverrides={type === "feed"}
                  onChange={onChange}
                />
              ),
            },
          },
          render: ({ __cms_json }: { __cms_json?: string }) => (
            <section className="rounded-lg border border-dashed border-[var(--site-outline-variant,rgba(255,255,255,0.2))] p-6 my-4">
              <p className="text-sm font-semibold">Sección {type}</p>
              <p className="mt-2 text-xs opacity-70">
                Edita todos los campos de esta sección desde el panel lateral.
              </p>
              <pre className="mt-4 max-h-40 overflow-auto whitespace-pre-wrap text-2xs opacity-70">
                {__cms_json || "{}"}
              </pre>
            </section>
          ),
        },
      ]),
    );

    return {
      root: {
        render: ({ children }: any) => (
          <div 
            className="p-8 min-h-screen transition-colors duration-200"
            style={{
              backgroundColor: "var(--site-background, #001134)",
              color: "var(--site-on-background, #d9e2ff)",
              fontFamily: "var(--font-inter, sans-serif)",
            }}
          >
            <div className="max-w-6xl mx-auto space-y-6">
              {children}
            </div>
          </div>
        )
      },
      components: {
        ...genericComponents,
        hero: {
          label: "Banner Héroe (Hero)",
          fields: {
            title: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <AiField label="Título Principal" value={value} onChange={onChange} fieldType="title" token={token} />
              )
            },
            body: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <AiField label="Cuerpo del Mensaje" value={value} onChange={onChange} isTextArea fieldType="body" token={token} />
              )
            },
            cta_label: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <AiField label="Texto del Botón" value={value} onChange={onChange} fieldType="cta" placeholder="ej. Comenzar ahora" token={token} />
              )
            },
            cta_href: { type: "text", label: "Enlace del Botón" },
            bg_image: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <MediaPickerField label="Imagen de Fondo" value={value} onChange={onChange} />
              )
            },
            slides: {
              type: "array",
              label: "Imágenes del carrusel",
              min: 0,
              max: 12,
              getItemSummary: (item: any, idx?: number) =>
                item?.alt || item?.title || `Imagen #${(idx ?? 0) + 1}`,
              defaultItemProps: { src: "", alt: "Imagen principal", title: "", caption: "", href: "" },
              arrayFields: {
                src: {
                  type: "custom",
                  label: "Imagen",
                  render: ({ value, onChange }: any) => (
                    <MediaPickerField label="Imagen del slide" value={value} onChange={onChange} />
                  ),
                },
                alt: { type: "text", label: "Texto alternativo" },
                title: { type: "text", label: "Título opcional" },
                caption: { type: "text", label: "Descripción opcional" },
                href: { type: "text", label: "Enlace opcional" },
              },
            },
          },
          render: ({ title, body, cta_label, cta_href, bg_image, slides }: any) => (
            <section
              className="relative py-20 px-6 text-center bg-cover bg-center rounded-lg overflow-hidden my-4 border border-[var(--site-outline-variant,rgba(255,255,255,0.05))]"
              style={{
                backgroundImage: bg_image || slides?.[0]?.src
                  ? `linear-gradient(rgba(0,0,0,0.65), rgba(0,0,0,0.65)), url(${bg_image || slides?.[0]?.src})`
                  : "var(--site-cta-gradient, linear-gradient(135deg, #004581, #018abd))",
                minHeight: "380px",
              }}
            >
              <div className="relative z-10 max-w-2xl mx-auto flex flex-col items-center justify-center min-h-[250px]">
                <h1 
                  className="text-3xl font-extrabold tracking-tight sm:text-4xl md:text-5xl"
                  style={{ color: "var(--site-on-hero, #ffffff)", fontFamily: "var(--font-outfit, sans-serif)" }}
                >
                  {title || "Título del Héroe"}
                </h1>
                <p 
                  className="mt-4 text-lg max-w-lg"
                  style={{ color: "var(--site-on-hero, rgba(255,255,255,0.9))" }}
                >
                  {body || "Este es el cuerpo del mensaje del banner de la página."}
                </p>
                {cta_label && (
                  <a
                    href={cta_href || "#"}
                    className="mt-8 px-6 py-3 text-sm font-semibold rounded-md shadow-md transition-all duration-200 hover:scale-[1.02]"
                    style={{
                      backgroundColor: "var(--site-primary, #a5c8ff)",
                      color: "var(--site-on-primary, #00315e)",
                      boxShadow: "var(--site-cta-shadow, 0 4px 12px rgba(0,0,0,0.15))",
                    }}
                  >
                    {cta_label}
                  </a>
                )}
              </div>
            </section>
          ),
        },
        rich_text: {
          label: "Texto Enriquecido (Rich Text)",
          fields: {
            title: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <AiField label="Título de la Sección" value={value} onChange={onChange} fieldType="title" token={token} />
              )
            },
            body: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <AiField label="Contenido de Texto" value={value} onChange={onChange} isTextArea fieldType="body" token={token} />
              )
            },
            cta_label: { type: "text", label: "Texto del Enlace" },
            cta_href: { type: "text", label: "Destino del Enlace" },
          },
          render: ({ title, body, cta_label, cta_href }: any) => (
            <section 
              className="py-12 px-6 max-w-3xl mx-auto my-4 border rounded-lg shadow-sm"
              style={{
                backgroundColor: "var(--site-surface, #001134)",
                borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))",
              }}
            >
              {title && (
                <h2 
                  className="text-2xl font-bold tracking-tight"
                  style={{ color: "var(--site-on-surface, #d9e2ff)" }}
                >
                  {title}
                </h2>
              )}
              <div 
                className="mt-4 text-base leading-7 whitespace-pre-wrap"
                style={{ color: "var(--site-on-surface-variant, #c2c6d1)" }}
              >
                {body || "Escribe el contenido aquí..."}
              </div>
              {cta_label && (
                <div className="mt-6">
                  <a
                    href={cta_href || "#"}
                    className="text-sm font-semibold hover:underline flex items-center gap-1"
                    style={{ color: "var(--site-primary, #a5c8ff)" }}
                  >
                    {cta_label} &rarr;
                  </a>
                </div>
              )}
            </section>
          ),
        },
        cta_banner: {
          label: "Banner CTA (CTA Banner)",
          fields: {
            title: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <AiField label="Título" value={value} onChange={onChange} fieldType="title" token={token} />
              )
            },
            body: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <AiField label="Descripción" value={value} onChange={onChange} isTextArea fieldType="description" token={token} />
              )
            },
            cta_label: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <AiField label="Botón Principal" value={value} onChange={onChange} fieldType="cta" placeholder="ej. Inscribirme" token={token} />
              )
            },
            cta_href: { type: "text", label: "Enlace Botón Principal" },
            cta_label_2: { type: "text", label: "Botón Secundario" },
            cta_href_2: { type: "text", label: "Enlace Botón Secundario" },
          },
          render: ({ title, body, cta_label, cta_href, cta_label_2, cta_href_2 }: any) => (
            <section 
              className="py-12 px-6 border rounded-lg text-center my-4 max-w-4xl mx-auto"
              style={{
                backgroundColor: "var(--site-primary-container, #004581)",
                borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))",
              }}
            >
              <h2 
                className="text-2xl font-bold tracking-tight"
                style={{ color: "var(--site-on-surface, #d9e2ff)" }}
              >
                {title || "Llamada a la acción"}
              </h2>
              {body && (
                <p 
                  className="mt-4 text-base max-w-xl mx-auto"
                  style={{ color: "var(--site-on-surface-variant, #c2c6d1)" }}
                >
                  {body}
                </p>
              )}
              <div className="mt-8 flex justify-center gap-4">
                {cta_label && (
                  <a 
                    href={cta_href || "#"} 
                    className="px-5 py-2.5 text-sm font-semibold rounded-md shadow transition-all hover:scale-[1.02]"
                    style={{
                      backgroundColor: "var(--site-primary, #a5c8ff)",
                      color: "var(--site-on-primary, #00315e)",
                    }}
                  >
                    {cta_label}
                  </a>
                )}
                {cta_label_2 && (
                  <a 
                    href={cta_href_2 || "#"} 
                    className="px-5 py-2.5 bg-transparent border text-sm font-semibold rounded-md transition-all hover:bg-white/5"
                    style={{
                      borderColor: "var(--site-outline, #8c919b)",
                      color: "var(--site-primary, #a5c8ff)",
                    }}
                  >
                    {cta_label_2}
                  </a>
                )}
              </div>
            </section>
          ),
        },
        faq: {
          label: "Preguntas Frecuentes (FAQ)",
          fields: {
            title: { type: "text", label: "Título de la Sección" },
            items: {
              type: "array",
              label: "Preguntas",
              getItemSummary: (item: any) => item.q || "Pregunta vacía",
              defaultItemProps: { q: "Nueva Pregunta", a: "Respuesta..." },
              arrayFields: {
                q: { type: "text", label: "Pregunta" },
                a: { type: "textarea", label: "Respuesta" },
              },
            },
          },
          render: ({ title, items }: any) => (
            <section 
              className="py-12 px-6 max-w-3xl mx-auto my-4 border rounded-lg"
              style={{
                backgroundColor: "var(--site-surface, #001134)",
                borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))",
              }}
            >
              {title && (
                <h2 
                  className="text-2xl font-bold tracking-tight mb-6"
                  style={{ color: "var(--site-on-surface, #d9e2ff)" }}
                >
                  {title}
                </h2>
              )}
              <div className="space-y-4">
                {(items || []).map((item: any, idx: number) => (
                  <div 
                    key={idx} 
                    className="border-b pb-4 last:border-0"
                    style={{ borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))" }}
                  >
                    <h3 
                      className="text-lg font-semibold"
                      style={{ color: "var(--site-on-surface, #d9e2ff)" }}
                    >
                      {item.q}
                    </h3>
                    <p 
                      className="mt-2 text-base"
                      style={{ color: "var(--site-on-surface-variant, #c2c6d1)" }}
                    >
                      {item.a}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          ),
        },
        testimonials: {
          label: "Testimonios (Testimonials)",
          fields: {
            title: { type: "text", label: "Título de la Sección" },
            items: {
              type: "array",
              label: "Testimonios",
              getItemSummary: (item: any) => item.author || "Autor vacío",
              defaultItemProps: { author: "Nombre del Autor", role: "Colaborador", content: "El testimonio...", stars: 5 },
              arrayFields: {
                author: { type: "text", label: "Autor" },
                role: { type: "text", label: "Cargo/Rol" },
                content: { type: "textarea", label: "Testimonio" },
                stars: { type: "number", label: "Estrellas (1-5)" },
              },
            },
          },
          render: ({ title, items }: any) => (
            <section className="py-12 px-6 max-w-4xl mx-auto my-4">
              {title && (
                <h2 
                  className="text-2xl font-bold text-center tracking-tight mb-8"
                  style={{ color: "var(--site-on-surface, #d9e2ff)" }}
                >
                  {title}
                </h2>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {(items || []).map((item: any, idx: number) => (
                  <div 
                    key={idx} 
                    className="p-6 border rounded-lg shadow-sm"
                    style={{
                      backgroundColor: "var(--site-surface-container-low, #001944)",
                      borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))",
                    }}
                  >
                    <div className="flex gap-1 mb-3 text-amber-400">
                      {Array.from({ length: Math.min(5, Math.max(1, item.stars || 5)) }).map((_, i) => (
                        <span key={i}>★</span>
                      ))}
                    </div>
                    <p 
                      className="text-base italic"
                      style={{ color: "var(--site-on-surface-variant, #c2c6d1)" }}
                    >
                      &quot;{item.content}&quot;
                    </p>
                    <div className="mt-4 flex items-center gap-3">
                      <div>
                        <h4 
                          className="text-sm font-bold"
                          style={{ color: "var(--site-on-surface, #d9e2ff)" }}
                        >
                          {item.author}
                        </h4>
                        <p 
                          className="text-xs"
                          style={{ color: "var(--site-on-surface-variant, #c2c6d1)" }}
                        >
                          {item.role}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ),
        },
        stats: {
          label: "Estadísticas (Stats)",
          fields: {
            title: { type: "text", label: "Título de la Sección" },
            items: {
              type: "array",
              label: "Estadísticas",
              getItemSummary: (item: any) => `${item.value || ""} - ${item.label || ""}`,
              defaultItemProps: { value: "100%", label: "Descripción" },
              arrayFields: {
                value: { type: "text", label: "Valor (ej: 15K, 100%)" },
                label: { type: "text", label: "Etiqueta" },
              },
            },
          },
          render: ({ title, items }: any) => (
            <section 
              className="py-12 px-6 text-center max-w-4xl mx-auto my-4 border rounded-lg"
              style={{
                backgroundColor: "var(--site-surface, #001134)",
                borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))",
              }}
            >
              {title && (
                <h2 
                  className="text-2xl font-bold tracking-tight mb-8"
                  style={{ color: "var(--site-on-surface, #d9e2ff)" }}
                >
                  {title}
                </h2>
              )}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                {(items || []).map((item: any, idx: number) => (
                  <div key={idx} className="space-y-2">
                    <p 
                      className="text-3xl font-extrabold"
                      style={{ color: "var(--site-primary, #a5c8ff)" }}
                    >
                      {item.value}
                    </p>
                    <p 
                      className="text-sm"
                      style={{ color: "var(--site-on-surface-variant, #c2c6d1)" }}
                    >
                      {item.label}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          ),
        },
        gallery: {
          label: "Galería (Gallery)",
          defaultProps: {
            title: "Galería de imágenes",
            items: [
              { url: "", alt: "Galería 1", caption: "Imagen 1" },
              { url: "", alt: "Galería 2", caption: "Imagen 2" },
              { url: "", alt: "Galería 3", caption: "Imagen 3" },
            ],
          },
          fields: {
            title: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <AiField label="Título de la Sección" value={value} onChange={onChange} fieldType="title" token={token} />
              )
            },
            body: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <AiField label="Descripción" value={value} onChange={onChange} isTextArea fieldType="body" token={token} />
              )
            },
            items: {
              type: "array",
              label: "Imágenes de la Galería",
              min: 1,
              max: 12,
              getItemSummary: (item: any, idx?: number) =>
                item?.caption || (item?.alt && item.alt !== "Imagen" ? item.alt : `Imagen #${(idx ?? 0) + 1}`),
              defaultItemProps: { url: "", alt: "Imagen", caption: "" },
              arrayFields: {
                url: {
                  type: "custom",
                  label: "Imagen",
                  render: ({ value, onChange }: any) => (
                    <MediaPickerField label="Imagen" value={value} onChange={onChange} />
                  )
                },
                alt: { type: "text", label: "Texto Alt" },
                caption: { type: "text", label: "Leyenda / Copete" },
              }
            }
          },
          render: ({ title, body, items }: any) => {
            const itemList = items || [];
            return (
              <section 
                className="py-12 px-6 max-w-5xl mx-auto my-4 text-center border rounded-lg"
                style={{
                  backgroundColor: "var(--site-surface, #001134)",
                  borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))",
                }}
              >
                {title && (
                  <h2 
                    className="text-2xl font-bold tracking-tight mb-2"
                    style={{ color: "var(--site-on-surface, #d9e2ff)" }}
                  >
                    {title}
                  </h2>
                )}
                {body && (
                  <p 
                    className="text-base mb-8"
                    style={{ color: "var(--site-on-surface-variant, #c2c6d1)" }}
                  >
                    {body}
                  </p>
                )}
                {itemList.length === 0 ? (
                  <div 
                    className="p-8 border-2 border-dashed rounded-lg text-center my-4"
                    style={{
                      borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))",
                      color: "var(--site-on-surface-variant, #c2c6d1)",
                    }}
                  >
                    <p className="text-sm font-medium">
                      No hay imágenes agregadas. Añade elementos desde el panel lateral.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                    {itemList.map((item: any, idx: number) => (
                      <div 
                        key={idx} 
                        className="group relative aspect-square overflow-hidden rounded-lg bg-black/10 border flex items-center justify-center"
                        style={{
                          borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))",
                        }}
                      >
                        {item?.url ? (
                          <img 
                            src={item.url} 
                            alt={item.alt || ""} 
                            className="h-full w-full object-cover transition duration-300 group-hover:scale-105" 
                          />
                        ) : (
                          <div 
                            className="flex flex-col items-center justify-center p-3 text-center w-full h-full bg-white/5"
                            style={{ color: "var(--site-on-surface-variant, #c2c6d1)" }}
                          >
                            <span className="text-2xs font-semibold px-2.5 py-1 rounded border border-current opacity-70">
                              Sin imagen
                            </span>
                            {item?.alt && item.alt !== "Imagen" && (
                              <span className="text-3xs mt-1 truncate max-w-[90%] opacity-80">
                                {item.alt}
                              </span>
                            )}
                          </div>
                        )}
                        {item?.caption && (
                          <div className="absolute inset-x-0 bottom-0 bg-black/60 p-2 text-2xs text-white text-left opacity-0 group-hover:opacity-100 transition-opacity">
                            {item.caption}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </section>
            );
          }
        },
        cards: {
          label: "Tarjetas (Cards)",
          defaultProps: {
            title: "Tarjetas",
            items: [
              { title: "Tarjeta 1", body: "Descripción de la tarjeta 1...", cta_label: "Saber más", cta_href: "/", image_url: "" },
              { title: "Tarjeta 2", body: "Descripción de la tarjeta 2...", cta_label: "Saber más", cta_href: "/", image_url: "" },
              { title: "Tarjeta 3", body: "Descripción de la tarjeta 3...", cta_label: "Saber más", cta_href: "/", image_url: "" },
            ],
          },
          fields: {
            title: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <AiField label="Título de la Sección" value={value} onChange={onChange} fieldType="title" token={token} />
              )
            },
            body: {
              type: "custom",
              render: ({ value, onChange }: any) => (
                <AiField label="Descripción de la Sección" value={value} onChange={onChange} isTextArea fieldType="body" token={token} />
              )
            },
            items: {
              type: "array",
              label: "Tarjetas",
              min: 1,
              max: 6,
              getItemSummary: (item: any, idx?: number) =>
                item?.title || `Tarjeta #${(idx ?? 0) + 1}`,
              defaultItemProps: { title: "Título de Tarjeta", body: "Descripción corta...", cta_label: "Saber más", cta_href: "/", image_url: "" },
              arrayFields: {
                title: {
                  type: "custom",
                  label: "Título",
                  render: ({ value, onChange }: any) => (
                    <AiField label="Título" value={value} onChange={onChange} fieldType="title" token={token} />
                  )
                },
                body: {
                  type: "custom",
                  label: "Descripción",
                  render: ({ value, onChange }: any) => (
                    <AiField label="Descripción" value={value} onChange={onChange} isTextArea fieldType="body" token={token} />
                  )
                },
                cta_label: { type: "text", label: "Etiqueta Botón" },
                cta_href: { type: "text", label: "Enlace Botón" },
                image_url: {
                  type: "custom",
                  label: "Imagen",
                  render: ({ value, onChange }: any) => (
                    <MediaPickerField label="Imagen" value={value} onChange={onChange} />
                  )
                }
              }
            }
          },
          render: ({ title, body, items }: any) => {
            const itemList = items || [];
            return (
              <section 
                className="py-12 px-6 max-w-5xl mx-auto my-4 border rounded-lg"
                style={{
                  backgroundColor: "var(--site-surface, #001134)",
                  borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))",
                }}
              >
                {title && (
                  <h2 
                    className="text-2xl font-bold tracking-tight mb-2 text-center" 
                    style={{ color: "var(--site-on-surface, #d9e2ff)" }}
                  >
                    {title}
                  </h2>
                )}
                {body && (
                  <p 
                    className="text-base text-center mb-8" 
                    style={{ color: "var(--site-on-surface-variant, #c2c6d1)" }}
                  >
                    {body}
                  </p>
                )}
                {itemList.length === 0 ? (
                  <div 
                    className="p-8 border-2 border-dashed rounded-lg text-center my-4"
                    style={{
                      borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))",
                      color: "var(--site-on-surface-variant, #c2c6d1)",
                    }}
                  >
                    <p className="text-sm font-medium">
                      No hay tarjetas agregadas. Añade elementos desde el panel lateral.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
                    {itemList.map((item: any, idx: number) => (
                      <div 
                        key={idx} 
                        className="overflow-hidden border rounded-lg flex flex-col shadow-sm"
                        style={{
                          backgroundColor: "var(--site-surface-container-low, #001944)",
                          borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))",
                        }}
                      >
                        {item?.image_url ? (
                          <img 
                            src={item.image_url} 
                            alt={item.title || ""} 
                            className="w-full h-48 object-cover" 
                          />
                        ) : (
                          <div 
                            className="w-full h-48 flex flex-col items-center justify-center bg-white/5 border-b"
                            style={{ 
                              borderColor: "var(--site-outline-variant, rgba(255,255,255,0.1))",
                              color: "var(--site-on-surface-variant, #c2c6d1)",
                            }}
                          >
                            <span className="text-2xs font-semibold px-2.5 py-1 rounded border border-current opacity-70">
                              Sin imagen
                            </span>
                          </div>
                        )}
                        <div className="p-5 flex-1 flex flex-col justify-between">
                          <div>
                            <h3 
                              className="text-lg font-bold" 
                              style={{ color: "var(--site-on-surface, #d9e2ff)" }}
                            >
                              {item?.title || `Tarjeta #${idx + 1}`}
                            </h3>
                            {item?.body && (
                              <p 
                                className="mt-2 text-sm" 
                                style={{ color: "var(--site-on-surface-variant, #c2c6d1)" }}
                              >
                                {item.body}
                              </p>
                            )}
                          </div>
                          {item?.cta_label && (
                            <a 
                              href={item.cta_href || "#"} 
                              className="mt-4 inline-block text-sm font-semibold hover:underline"
                              style={{ color: "var(--site-primary, #a5c8ff)" }}
                            >
                              {item.cta_label} &rarr;
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            );
          }
        }
      },
    };
  }, [token]);

  const savePageData = useCallback(
    async (
      dataToSave: { content: any[] },
      options: { isAutoSave: boolean }
    ) => {
      if (!token || !pageSlug || !canEdit) {
        if (!options.isAutoSave) {
          toast.error("No tienes permisos de edición");
        }
        return;
      }

      const currentSeq = ++saveSequenceRef.current;
      const previousSave = saveQueueRef.current;
      const queuedSave = previousSave.then(async () => {
        // Autosaves are latest-wins. Do not issue any API mutation for a
        // snapshot that was superseded while an earlier save was in flight.
        if (options.isAutoSave && currentSeq !== saveSequenceRef.current) {
          return;
        }

      if (options.isAutoSave) {
        setSaveStatus("saving");
      } else {
        setSaving(true);
        savingRef.current = true;
        setSaveStatus("saving");
      }

      let draftSaved = false;
      try {
        const activeIdsInPuck = new Set<string>();
        const currentDbSections = dbSectionsRef.current;

        const contentToSave = dataToSave?.content || [];
        // 1. Process inserts and updates
        for (let i = 0; i < contentToSave.length; i++) {
          if (currentSeq !== saveSequenceRef.current) {
            return;
          }
          const item = contentToSave[i];
          const id = item.props?.id;

          // Clean properties by stripping the editor-only id field. Generic
          // page sections store their complete editable payload in
          // ``__cms_json``; restore it to the object expected by the API.
          const { id: _, ...rawProps } = item.props || {};
          const deserializedProps = deserializePuckProps(rawProps);
          const existingSection = currentDbSections.find((s) => s.id === id);
          // Native Puck blocks expose only their compact field schema. Merge
          // their edited values over the stored payload so page-specific keys
          // (eyebrow, title_lead, SEO copy, etc.) are not lost on save.
          const cleanProps =
            existingSection && NATIVE_PUCK_SECTION_TYPES.has(item.type)
              ? { ...(existingSection.props_json || {}), ...deserializedProps }
              : deserializedProps;

          if (id && existingSection) {
            // Exists in DB: Update sort_order and props_json
            activeIdsInPuck.add(id);
            await patchCmsSection(
              siteKey,
              pageSlug,
              id,
              { sort_order: i, props_json: cleanProps },
              token
            );
          } else {
            // New block: Create in DB
            const created = await createCmsSection(
              siteKey,
              pageSlug,
              { type: item.type, sort_order: i, props_json: cleanProps },
              token
            );
            if (created?.id) {
              activeIdsInPuck.add(created.id);
              // Patch in-memory id so next edits track it correctly
              if (item.props) {
                item.props.id = created.id;
              } else {
                item.props = { id: created.id };
              }
            }
          }
        }

        // 2. Process deletions: Archive database sections missing from Puck
        const missingFromPuck = currentDbSections.filter((s) => !activeIdsInPuck.has(s.id));
        for (const sectionToDelete of missingFromPuck) {
          if (currentSeq !== saveSequenceRef.current) {
            return;
          }
          await deleteCmsSection(siteKey, pageSlug, sectionToDelete.id, token);
        }

        // Out-of-order sequence check
        if (currentSeq < latestCompletedSeqRef.current) {
          return;
        }
        latestCompletedSeqRef.current = currentSeq;

        // Reload fresh state from DB
        const freshSections = await listCmsSections(siteKey, pageSlug, token);
        const updated = freshSections || [];
        setDbSections(updated);
        dbSectionsRef.current = updated;
        draftSaved = true;

        // A manual save is the explicit publish action in this compact Puck
        // editor. Auto-save only persists the draft; publishing creates the
        // immutable snapshot consumed by the public endpoint.
        if (!options.isAutoSave && canPublish) {
          await workflowCmsPage(siteKey, pageSlug, "publish", "Publicado desde el editor visual", token);
        }

        // Check if newer changes arrived while save was in flight
        if (
          latestDataRef.current !== dataToSave &&
          JSON.stringify(latestDataRef.current) !== JSON.stringify(dataToSave)
        ) {
          setSaveStatus("dirty");
        } else {
          setSaveStatus("saved");
        }

        if (!options.isAutoSave) {
          toast.success(
            canPublish
              ? "¡Página publicada exitosamente con Puck!"
              : "Cambios guardados como borrador. Un publicador debe aprobarlos.",
          );
        }
      } catch (err) {
        setSaveStatus("error");
        if (!options.isAutoSave) {
          toast.error(
            draftSaved
              ? "Borrador guardado, pero la publicación falló"
              : "Error al guardar y publicar la página",
          );
        } else {
          toast.error("Error en el auto-guardado", { id: "autosave-err" });
        }
      } finally {
        if (!options.isAutoSave) {
          setSaving(false);
          savingRef.current = false;
        }
      }
      });
      // Keep the queue alive after a handled failure so later saves are not
      // blocked by a rejected promise.
      saveQueueRef.current = queuedSave.catch(() => undefined);
      return queuedSave;
    },
    [token, pageSlug, canEdit, canPublish, siteKey]
  );

  const handlePuckChange = (newData: { content: any[] }) => {
    const dataWithMediaId = selectedMediaRef.current
      ? preserveSelectedMediaId(newData, selectedMediaRef.current)
      : newData;
    selectedMediaRef.current = null;

    if (isInitialLoadRef.current) {
      isInitialLoadRef.current = false;
      latestDataRef.current = dataWithMediaId;
      return;
    }

    latestDataRef.current = dataWithMediaId;
    setSaveStatus("dirty");

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      savePageData(latestDataRef.current, { isAutoSave: true });
    }, 3000);
  };

  const handlePublish = useCallback(
    async (data?: { content: any[] }) => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
      const dataToSave = data || latestDataRef.current;
      await savePageData(dataToSave, { isAutoSave: false });
    },
    [savePageData]
  );

  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (!savingRef.current) {
          handlePublish(latestDataRef.current);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handlePublish]);

  if (!token || !pageSlug) {
    return (
      <div className="flex h-screen items-center justify-center p-6 text-center bg-[hsl(var(--bg-primary))]">
        <div className="space-y-3">
          <p className="text-sm text-[hsl(var(--text-secondary))]">Selecciona un sitio y página en la lista de páginas para editar.</p>
          <button
            onClick={() => router.push("/plataforma/cms/pages")}
            className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-md shadow-md hover:bg-primary-hover transition-colors"
          >
            Volver a Páginas
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[hsl(var(--bg-primary))]">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="animate-spin text-primary" size={32} />
          <p className="text-sm text-[hsl(var(--text-secondary))]">Cargando lienzo de Puck...</p>
        </div>
      </div>
    );
  }

  if (contentMode) {
    return (
      <PublicContentEditor
        siteKey={siteKey}
        pageSlug={pageSlug}
        sections={dbSections}
        token={token}
        canEdit={canEdit}
        canPublish={canPublish}
        onBack={() => router.push(`/plataforma/cms/pages?site=${siteKey}`)}
      />
    );
  }

  // Home uses the canonical public-content model. Do not expose the retired
  // generic Puck hero fields (title/body/cta) for this page.
  const hasCanonicalHomeHero = dbSections.some((section) => {
    const props = section?.props_json;
    return section?.section_key === "hero" && props && typeof props === "object" && (
      "title_lead" in props || "title_accent" in props || "title_tail" in props
    );
  });

  if (pageSlug === "home" && hasCanonicalHomeHero && !heroMediaMode) {
    return (
      <PublicContentEditor
        siteKey={siteKey}
        pageSlug={pageSlug}
        sections={dbSections}
        token={token}
        canEdit={canEdit}
        canPublish={canPublish}
        onBack={() => router.push(`/plataforma/cms/pages?site=${siteKey}`)}
      />
    );
  }

  if (heroMediaMode) {
    return (
      <HeroMediaEditor
        siteKey={siteKey}
        pageSlug={pageSlug}
        sections={dbSections}
        token={token}
        canEdit={canEdit}
        canPublish={canPublish}
        onBack={() => router.push(`/plataforma/cms/pages?site=${siteKey}`)}
      />
    );
  }

  return (
    <main aria-label="Editor visual Puck" className="h-screen flex flex-col bg-[hsl(var(--bg-primary))]" style={themeStyles}>
      {/* Header bar */}
      <div className="shrink-0 border-b border-[hsl(var(--border))] dark:border-white/[0.05] p-3 flex items-center justify-between bg-white dark:bg-[hsl(var(--surface-2))]">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push(`/plataforma/cms/pages?site=${siteKey}`)}
            className="p-2 border border-[hsl(var(--border))] dark:border-white/10 rounded-md hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
            title="Volver a Páginas"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <span className="text-3xs uppercase tracking-wider font-semibold text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
              <LayoutPanelTop size={10} /> Puck Editor
            </span>
            <h1 className="text-md font-bold tracking-tight mt-0.5">
              Editando página: <span className="text-primary">/{pageSlug}</span>
            </h1>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-primary/10 border border-primary/20 rounded-md text-2xs text-primary font-medium">
            <Palette size={12} /> Tema: <span className="font-bold">{themeName}</span>
          </div>

          <SaveStatusBadge status={saveStatus} />

          <button
            onClick={() => handlePublish(latestDataRef.current)}
            disabled={saveStatus === "saving" || saving}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white text-xs font-semibold rounded-md shadow hover:bg-primary-hover disabled:opacity-50 transition-colors"
            title="Guardar cambios (Ctrl+S / Cmd+S)"
          >
            {saveStatus === "saving" || saving ? (
              <Loader2 className="animate-spin" size={14} />
            ) : (
              <Save size={14} />
            )}
            <span>Guardar</span>
          </button>
        </div>
      </div>

      {/* Editor Frame */}
      <div className="flex-1 overflow-hidden relative">
        <Puck
          config={puckConfig}
          data={initialData}
          onChange={handlePuckChange}
          onPublish={handlePublish}
          iframe={{ enabled: false }}
        />
      </div>

      {/* Custom MediaPicker Drawer integration */}
      {mediaPickerOpen && (
        <MediaPicker
          open
          token={token}
          selectedUrl={mediaPickerValue}
          onClose={() => setMediaPickerOpen(false)}
          onSelect={(item) => {
            const selected: { url?: string; id?: string | number } = typeof item === "string" ? { url: item } : item as { url?: string; id?: string | number };
            const url = selected.url || "";
            if (typeof item !== "string" && selected.id !== undefined) {
              selectedMediaRef.current = { url, media_id: selected.id };
            }
            if (mediaPickerCallbackRef.current) {
              mediaPickerCallbackRef.current(url);
            }
            setMediaPickerOpen(false);
          }}
        />
      )}
    </main>
  );
}

type ContentSection = {
  id: string;
  section_key: string;
  type: string;
  props_json?: Record<string, unknown> | null;
  sort_order?: number;
};

type HeroSlide = {
  src: string;
  alt?: string;
  title?: string;
  caption?: string;
  href?: string;
};

const CONTENT_LABELS: Record<string, string> = {
  eyebrow: "Etiqueta superior",
  title: "Título",
  title_lead: "Título · primera línea",
  title_accent: "Título · énfasis",
  title_tail: "Título · última línea",
  description: "Descripción",
  body: "Contenido",
  primary_cta: "Botón principal",
  secondary_cta: "Botón secundario",
  scroll_indicator: "Indicador de desplazamiento",
};

const HOME_HERO_CONTENT_FIELDS = [
  "eyebrow",
  "title_lead",
  "title_accent",
  "title_tail",
  "description",
  "primary_cta",
  "secondary_cta",
];

function contentLabel(key?: string): string {
  if (!key) return "Sección";
  return CONTENT_LABELS[key] || key.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

type EditablePath = { path: string[]; value: string };

function flattenEditableStrings(value: unknown, path: string[] = []): EditablePath[] {
  if (typeof value === "string" && !path.some((part) => /(^|_)(href|url|src|image)$/i.test(part))) {
    return [{ path, value }];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => flattenEditableStrings(item, [...path, String(index)]));
  }
  if (value && typeof value === "object") {
    return Object.entries(value).flatMap(([key, child]) => flattenEditableStrings(child, [...path, key]));
  }
  return [];
}

function setNestedValue(source: Record<string, unknown>, path: string[], value: string): Record<string, unknown> {
  if (path.length === 0) return source;
  const next: Record<string, unknown> = Array.isArray(source) ? [...source] as unknown as Record<string, unknown> : { ...source };
  const [head, ...tail] = path;
  if (tail.length === 0) {
    next[head] = value;
    return next;
  }
  const child = next[head];
  const childRecord = child && typeof child === "object" ? child as Record<string, unknown> : {};
  next[head] = setNestedValue(childRecord, tail, value);
  return next;
}

function PublicContentEditor({
  siteKey,
  pageSlug,
  sections,
  token,
  canEdit,
  canPublish,
  onBack,
}: {
  siteKey: string;
  pageSlug: string;
  sections: ContentSection[];
  token: string;
  canEdit: boolean;
  canPublish: boolean;
  onBack: () => void;
}) {
  const [drafts, setDrafts] = useState<Record<string, Record<string, unknown>>>({});
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    setDrafts(Object.fromEntries(sections.map((section) => [
      section.id,
      section.props_json || {},
    ])));
  }, [sections]);

  const textFields = (section: ContentSection): EditablePath[] => {
    const visibleEntries = flattenEditableStrings(drafts[section.id] || {})
      .filter(({ path }) => !(pageSlug === "home" && section.section_key === "hero" && !HOME_HERO_CONTENT_FIELDS.includes(path[0])));

    if (pageSlug === "home" && section.section_key === "hero") {
      return visibleEntries.sort(
        ({ path: first }, { path: second }) => HOME_HERO_CONTENT_FIELDS.indexOf(first[0]) - HOME_HERO_CONTENT_FIELDS.indexOf(second[0]),
      );
    }

    return visibleEntries.sort(({ path: first }, { path: second }) => (first[0] === "eyebrow" ? -1 : second[0] === "eyebrow" ? 1 : first.join(".").localeCompare(second.join("."))));
  };

  const saveDraft = async () => {
    if (!canEdit) return;
    setSaving(true);
    try {
      await Promise.all(sections.map((section) => patchCmsSection(siteKey, pageSlug, section.id, {
        props_json: drafts[section.id] || section.props_json || {},
      }, token)));
      toast.success("Contenido guardado como borrador");
    } catch {
      toast.error("No se pudo guardar el contenido");
      throw new Error("No se pudo guardar el contenido");
    } finally {
      setSaving(false);
    }
  };

  const publish = async () => {
    if (!canPublish) return;
    setPublishing(true);
    try {
      await saveDraft();
      await workflowCmsPage(siteKey, pageSlug, "publish", "Publicado desde Contenido público", token);
      toast.success("Contenido publicado");
    } catch {
      toast.error("No se pudo publicar el contenido");
    } finally {
      setPublishing(false);
    }
  };

  return (
    <main className="min-h-screen bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] dark:bg-[hsl(var(--admin-bg-deep))]">
      <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))]/95 px-4 py-3 backdrop-blur dark:border-white/10 dark:bg-[hsl(var(--surface-2))]/95">
        <div className="flex items-center gap-3">
          <button type="button" onClick={onBack} className="rounded-lg border border-[hsl(var(--border))] p-2 hover:bg-[hsl(var(--surface-2))]" aria-label="Volver a páginas"><ArrowLeft size={16} /></button>
          <div>
            <p className="text-2xs font-bold uppercase tracking-[0.16em] text-[hsl(var(--primary))]">Contenido público</p>
            <h1 className="text-lg font-bold">Editar contenido de /{pageSlug}</h1>
          </div>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={saveDraft} disabled={!canEdit || saving || publishing} className="rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-xs font-semibold disabled:opacity-50">{saving ? "Guardando…" : "Guardar borrador"}</button>
          <button type="button" onClick={publish} disabled={!canPublish || saving || publishing} className="rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{publishing ? "Publicando…" : "Publicar"}</button>
        </div>
      </header>
      <div className="mx-auto max-w-4xl space-y-4 px-4 py-6">
        <div className="rounded-xl border border-[hsl(var(--info)/30%)] bg-info-soft/30 px-4 py-3 text-sm text-[hsl(var(--text-secondary))]">
          Aquí editas las palabras que lee el visitante. Los cambios se guardan como borrador; usa Publicar para hacerlos visibles.
        </div>
        {[...sections].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0)).map((section) => (
          <section key={section.id} className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
            <div className="mb-4 flex items-center justify-between gap-3 border-b border-[hsl(var(--border))] pb-3 dark:border-white/10">
              <div><h2 className="font-bold">{section.section_key === "hero" ? "Hero principal" : contentLabel(section.section_key)}</h2><p className="text-2xs text-[hsl(var(--text-secondary))]">{section.type}</p></div>
              {section.section_key === "hero" && <span className="rounded-full bg-info-soft px-2 py-1 text-2xs font-bold uppercase text-[hsl(var(--primary))]">Visible al inicio</span>}
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {textFields(section).map(({ path, value }) => {
                const key = path[path.length - 1];
                const fieldKey = path.join(".");
                return (
                <label key={fieldKey} className={value.length > 100 || key === "description" || key === "body" ? "md:col-span-2" : ""}>
                  <span className="mb-1 block text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{contentLabel(key)} <span className="font-normal normal-case opacity-60">({fieldKey})</span></span>
                  {value.length > 100 || key === "description" || key === "body" ? <textarea value={value} onChange={(event) => setDrafts((current) => ({ ...current, [section.id]: setNestedValue(current[section.id] || {}, path, event.target.value) }))} rows={4} disabled={!canEdit} className="w-full rounded-lg border border-[hsl(var(--border))] bg-transparent px-3 py-2 text-sm disabled:opacity-60" /> : <input value={value} onChange={(event) => setDrafts((current) => ({ ...current, [section.id]: setNestedValue(current[section.id] || {}, path, event.target.value) }))} disabled={!canEdit} className="w-full rounded-lg border border-[hsl(var(--border))] bg-transparent px-3 py-2 text-sm disabled:opacity-60" />}
                </label>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}

function HeroMediaEditor({
  siteKey,
  pageSlug,
  sections,
  token,
  canEdit,
  canPublish,
  onBack,
}: {
  siteKey: string;
  pageSlug: string;
  sections: ContentSection[];
  token: string;
  canEdit: boolean;
  canPublish: boolean;
  onBack: () => void;
}) {
  const hero = sections.find((section) => section.section_key === "hero" && section.type === "hero");
  const [background, setBackground] = useState("");
  const [slides, setSlides] = useState<HeroSlide[]>([]);
  const [mediaOpen, setMediaOpen] = useState(false);
  const [mediaTarget, setMediaTarget] = useState<"background" | number>("background");
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    const props = hero?.props_json || {};
    setBackground(typeof props.bg_image === "string" ? props.bg_image : "");
    setSlides(Array.isArray(props.slides) ? props.slides.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object").map((item) => ({
      src: typeof item.src === "string" ? item.src : "",
      alt: typeof item.alt === "string" ? item.alt : "Imagen del hero",
      title: typeof item.title === "string" ? item.title : "",
      caption: typeof item.caption === "string" ? item.caption : "",
      href: typeof item.href === "string" ? item.href : "",
    })) : []);
  }, [hero]);

  const chooseMedia = (target: "background" | number) => {
    setMediaTarget(target);
    setMediaOpen(true);
  };

  const selectMedia = (item: { url?: string }) => {
    const url = item.url || "";
    if (mediaTarget === "background") setBackground(url);
    else setSlides((current) => current.map((slide, index) => index === mediaTarget ? { ...slide, src: url } : slide));
    setMediaOpen(false);
  };

  const save = async (publish = false) => {
    if (!hero || !canEdit) return;
    if (publish && !canPublish) return;
    setSaving(!publish);
    setPublishing(publish);
    try {
      await patchCmsSection(siteKey, pageSlug, hero.id, {
        props_json: { ...(hero.props_json || {}), bg_image: background, slides },
      }, token);
      if (publish) {
        await workflowCmsPage(siteKey, pageSlug, "publish", "Publicado desde Imágenes del hero", token);
        toast.success("Imágenes del hero publicadas");
      } else {
        toast.success("Imágenes del hero guardadas como borrador");
      }
    } catch {
      toast.error(publish ? "No se pudieron publicar las imágenes" : "No se pudieron guardar las imágenes");
    } finally {
      setSaving(false);
      setPublishing(false);
    }
  };

  return (
    <main className="min-h-screen bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] dark:bg-[hsl(var(--admin-bg-deep))]">
      <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))]/95 px-4 py-3 backdrop-blur dark:border-white/10 dark:bg-[hsl(var(--surface-2))]/95">
        <div className="flex items-center gap-3"><button type="button" onClick={onBack} className="rounded-lg border border-[hsl(var(--border))] p-2" aria-label="Volver a páginas"><ArrowLeft size={16} /></button><div><p className="text-2xs font-bold uppercase tracking-[0.16em] text-[hsl(var(--primary))]">Media pública</p><h1 className="text-lg font-bold">Imágenes del hero</h1></div></div>
        <div className="flex gap-2"><button type="button" onClick={() => save()} disabled={!canEdit || saving || publishing} className="rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-xs font-semibold disabled:opacity-50">{saving ? "Guardando…" : "Guardar borrador"}</button><button type="button" onClick={() => save(true)} disabled={!canPublish || saving || publishing} className="rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{publishing ? "Publicando…" : "Publicar"}</button></div>
      </header>
      <div className="mx-auto max-w-5xl space-y-5 px-4 py-6">
        <div className="rounded-xl border border-[hsl(var(--info)/30%)] bg-info-soft/30 px-4 py-3 text-sm text-[hsl(var(--text-secondary))]">Este editor modifica únicamente la sección Hero de /{pageSlug}. El contenido y las demás secciones permanecen intactos.</div>
        {!hero ? <div className="rounded-xl border border-[hsl(var(--danger)/30%)] p-6">No se encontró la sección Hero de esta página.</div> : <>
          <section className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm"><h2 className="mb-3 font-bold">Imagen de respaldo</h2><div className="flex flex-col gap-3 sm:flex-row sm:items-center"><div className="relative h-28 w-full overflow-hidden rounded-lg bg-[hsl(var(--surface-2))] sm:w-52"><OptimizedImage src={background} alt="Imagen de respaldo del hero" fill sizes="208px" /></div><div className="min-w-0 flex-1"><p className="mb-2 break-all text-xs text-[hsl(var(--text-secondary))]">{background || "Sin imagen seleccionada"}</p><button type="button" onClick={() => chooseMedia("background")} disabled={!canEdit} className="inline-flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"><ImageIcon size={14} />Elegir de Media</button></div></div></section>
          <section className="space-y-3"><div className="flex items-center justify-between"><h2 className="font-bold">Carrusel del hero ({slides.length})</h2><button type="button" onClick={() => setSlides((current) => current.length >= 12 ? current : [...current, { src: "", alt: "Imagen del hero" }])} disabled={!canEdit || slides.length >= 12} className="inline-flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-xs font-semibold disabled:opacity-50"><Plus size={14} />Agregar imagen</button></div>{slides.map((slide, index) => <article key={`${index}-${slide.src}`} className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm"><div className="flex flex-col gap-4 lg:flex-row"><div className="relative h-36 w-full shrink-0 overflow-hidden rounded-lg bg-[hsl(var(--surface-2))] lg:w-64"><OptimizedImage src={slide.src} alt={slide.alt || `Imagen ${index + 1}`} fill sizes="256px" /></div><div className="grid flex-1 gap-3 sm:grid-cols-2"><button type="button" onClick={() => chooseMedia(index)} disabled={!canEdit} className="rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-left text-xs font-semibold disabled:opacity-50"><ImageIcon className="mr-2 inline" size={14} />Elegir imagen desde Media</button><button type="button" onClick={() => setSlides((current) => current.filter((_, itemIndex) => itemIndex !== index))} disabled={!canEdit} className="rounded-lg border border-[hsl(var(--danger)/30%)] px-3 py-2 text-xs font-semibold text-danger-text disabled:opacity-50"><Trash2 className="mr-2 inline" size={14} />Quitar imagen</button>{(["alt", "title", "caption", "href"] as const).map((field) => <label key={field} className={field === "caption" ? "sm:col-span-2" : ""}><span className="mb-1 block text-2xs font-bold uppercase text-[hsl(var(--text-secondary))]">{field === "alt" ? "Texto alternativo" : field === "href" ? "Enlace opcional" : field === "title" ? "Título" : "Descripción"}</span><input value={slide[field] || ""} onChange={(event) => setSlides((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: event.target.value } : item))} disabled={!canEdit} className="w-full rounded-lg border border-[hsl(var(--border))] bg-transparent px-3 py-2 text-sm disabled:opacity-60" /></label>)}</div></div></article>)}</section>
        </>}
      </div>
      {mediaOpen && <MediaPicker open token={token} selectedUrl={mediaTarget === "background" ? background : slides[mediaTarget]?.src || ""} onClose={() => setMediaOpen(false)} onSelect={selectMedia} />}
    </main>
  );
}
