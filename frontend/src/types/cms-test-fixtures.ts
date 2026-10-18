/**
 * Fixtures tipadas para los tests del módulo CMS.
 *
 * Reutilizan los contratos de `@/types/cms-v2` y `@/types/cms-builder`
 * para sustituir los usos de tipos laxos en mocks de vitest por
 * fixtures dentro del sistema de tipos (vi.mocked + mocks completos).
 */
import type { ReactElement } from "react";
import type { Mock } from "vitest";
import type { CmsPage, CmsSection } from "@/types/cms-v2";
import type { PuckData } from "@/types/cms-builder";

/**
 * Construye un `CmsPage` completo con defaults válidos para resolvers de
 * mocks (workflowCmsPage, listCmsPages, etc.).
 */
export function makeCmsPage(overrides: Partial<CmsPage> = {}): CmsPage {
  return {
    id: "page-fixture",
    site_id: "site-fixture",
    slug: "home",
    title: "Página fixture",
    status: "draft",
    seo_json: {},
    published_version_id: null,
    publish_at: null,
    expires_at: null,
    created_at: "2026-01-01T00:00:00.000Z",
    updated_at: "2026-01-01T00:00:00.000Z",
    ...overrides,
  };
}

// ─── Mock tipado del Config de Puck capturado por el stub ──────────────

/** Field mockeado de la config del builder (custom/array/text/number…). */
export interface PuckFieldMock {
  type?: string;
  label?: string;
  render?(props: Record<string, unknown>): ReactElement;
  arrayFields?: Record<string, PuckFieldMock>;
  min?: number;
  max?: number;
  getItemSummary(item: unknown, index?: number): string;
  defaultItemProps?: Record<string, unknown>;
  [key: string]: unknown;
}

/** Component mockeado del builder (label + fields + render + defaultProps). */
export interface PuckComponentMock {
  label?: string;
  fields?: Record<string, PuckFieldMock>;
  render?(props: Record<string, unknown>): ReactElement;
  defaultProps?: Record<string, unknown>;
  [key: string]: unknown;
}

/** Mapa de componentes mockeado del Config de Puck. */
export type PuckComponentsMock = Record<string, PuckComponentMock>;

/** Config completo capturado (components + root). */
export interface PuckConfigMock {
  components?: PuckComponentsMock;
  root?: {
    render?(props: Record<string, unknown>): ReactElement;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

/** Extrae de forma segura el field mockeado de un componente del config. */
export function puckField(config: PuckConfigMock | null, component: string, field: string): PuckFieldMock {
  const f = puckComponents(config)[component]?.fields?.[field];
  if (!f) throw new Error(`El field ${component}.${field} no está en el config mockeado`);
  return f;
}

/** Extrae de forma segura la función render() de un componente del config. */
export function puckRenderOf(
  config: PuckConfigMock | null,
  component: string,
): (props: Record<string, unknown>) => ReactElement {
  const render = puckComponents(config)[component]?.render;
  if (!render) throw new Error(`El componente ${component} mockeado no expone render()`);
  return render;
}

/** Extrae el mapa de componentes del config capturado (falla si es null). */
export function puckComponents(config: PuckConfigMock | null): PuckComponentsMock {
  if (!config) throw new Error("El stub de <Puck> aún no capturó el config");
  return config.components ?? {};
}

/** Invoca de forma segura el render() de un field mockeado. */
export function puckNode(
  fn: ((props: Record<string, unknown>) => ReactElement) | undefined,
  props: Record<string, unknown>,
): ReactElement {
  if (!fn) throw new Error("El field mockeado no expone render()");
  return fn(props);
}

// ─── TOTEM: asserts centrales (mantener líneas cortas en los diffs) ────

/**
 * Construye un `CmsSection` completo con defaults válidos para
 * resolvers de mocks (`mockResolvedValue`) que exigen el DTO exacto.
 */
export function makeDbSection(overrides: Partial<CmsSection> = {}): CmsSection {
  // El builder usa `section_key || type` como clave de sección: el fixture
  // deriva section_key del type (a menos que el override lo defina) para
  // mantener la misma semántica sin romper aserciones de los tests.
  const type = overrides.type ?? "hero";
  return {
    id: "sec-fixture",
    page_id: "page-fixture",
    section_key: overrides.section_key ?? type,
    type,
    props_json: {},
    sort_order: 0,
    is_visible: true,
    status: "active",
    created_at: "2026-01-01T00:00:00.000Z",
    updated_at: "2026-01-01T00:00:00.000Z",
    ...overrides,
  };
}

/**
 * Firma del payload de mutación de secciones (espejo exacto del argumento
 * de `patchCmsSection` en `@/lib/cms/v2`).
 */
export interface CmsSectionPatchPayload {
  type?: string;
  section_key?: string;
  props_json?: Record<string, unknown>;
  sort_order?: number;
  is_visible?: boolean;
  status?: string;
}

/** Helper: extrae la propiedad escalonada `title` del payload (string seguro). */
export function payloadTitle(payload: CmsSectionPatchPayload | undefined): string {
  const raw = payload?.props_json?.title;
  return typeof raw === "string" ? raw : "";
}

// ─── Mock del componente <Puck> del editor ────────────────────────────

/**
 * Props capturadas por el stub de `<Puck>` en los tests del builder:
 * el editor real invoca `onChange` con los datos serializados de Puck.
 */
export interface PuckMockProps {
  data?: PuckData;
  onChange: (data: PuckData) => void;
  onPublish?: (data?: PuckData) => void;
  [key: string]: unknown;
}

/** Placeholder de captura: `position: PuckMockProps | null`. */
export type CapturedPuckProps = PuckMockProps | null;

// ─── Asserts de mocks de módulos (helper opt-in) ──────────────────────

/** Wrapper legible para un mock de función (ayuda a TS a no inferir any). */
export function asMock<TArgs extends unknown[], TReturn>(fn: (...args: TArgs) => TReturn): Mock {
  return fn as unknown as Mock;
}


