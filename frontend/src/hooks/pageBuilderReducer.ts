/**
 * Centralized reducer for the CMS Page Builder state.
 *
 * Replaces the ~45 individual ``useState`` calls in ``usePageBuilder.ts``
 * with a single ``useReducer``, improving state traceability and making
 * batch updates atomic.
 *
 * The reducer manages **primitive/draft state only** — derived values
 * (``activePage``, ``activeSection``, ``seoAnalysis``, etc.) remain as
 * ``useMemo`` in the hook, and async callbacks (loaders, AI handlers,
 * workflow actions) remain as ``useCallback``.
 *
 * Action naming convention: ``SET_<FIELD>`` for simple field updates,
 * ``BATCH`` for multi-field updates, and specific named actions for
 * complex transitions (e.g. ``LOAD_SECTIONS``, ``SYNC_PAGE_DRAFTS``).
 */

import type { CmsPage, CmsPageVersion, CmsPublishLog, CmsSection, CmsTheme } from "@/types/cms-v2";
import type { CanvasMode, PreviewDevice, RightTab, Timeframe, HeatmapType, AiTemplate, AiTone } from "./usePageBuilder";
import { CANVAS_PREVIEW_TOKENS, safeString } from "@/components/cms/builder/utils";

// ── State shape ──────────────────────────────────────────────────────────────

export interface PageBuilderReducerState {
  // Site & page data
  siteKey: string;
  sites: Array<{ site_key: string; name: string; base_path: string }>;
  pages: CmsPage[];
  activeSlug: string;
  sections: CmsSection[];
  versions: CmsPageVersion[];
  publishLogs: CmsPublishLog[];

  // Draft / input state
  newPageTitle: string;
  newSectionType: string;
  pageTemplateKey: string;
  activeSectionId: string | null;
  note: string;

  // UI / interaction
  saving: boolean;
  draggedSectionId: string | null;
  previewDevice: PreviewDevice;
  canvasMode: CanvasMode;
  pageTitleDraft: string;
  pageSlugDraft: string;
  mediaPickerOpen: boolean;
  mediaPickerTarget: "section" | "seo";
  activeRightTab: RightTab;

  // SEO drafts
  seoTitleDraft: string;
  seoDescriptionDraft: string;
  seoImageDraft: string;
  seoCanonicalDraft: string;
  seoRobotsDraft: string;
  seoKeyword: string;

  // AI
  aiPrompt: string;
  aiGenerating: boolean;
  aiOutput: string;
  aiTone: AiTone;
  aiTemplate: AiTemplate;
  aiImagePrompt: string;
  aiImageResult: string;
  aiImageGenerating: boolean;

  // Analytics / A-B testing
  showHeatmap: boolean;
  timeframe: Timeframe;
  heatmapType: HeatmapType;
  abTestingActive: boolean;
  abTrafficSplit: number;
  serpPreviewDevice: PreviewDevice;

  // Theme / canvas
  canvasTokens: React.CSSProperties;
  canvasThemeName: string;
  themeLoading: boolean;
}

export const initialPageBuilderState: PageBuilderReducerState = {
  // Site & page data
  siteKey: "", // set by hook via SITE_KEY constant
  sites: [],
  pages: [],
  activeSlug: "",
  sections: [],
  versions: [],
  publishLogs: [],

  // Draft / input
  newPageTitle: "",
  newSectionType: "rich_text",
  pageTemplateKey: "simple",
  activeSectionId: null,
  note: "",

  // UI / interaction
  saving: false,
  draggedSectionId: null,
  previewDevice: "desktop",
  canvasMode: "esquema",
  pageTitleDraft: "",
  pageSlugDraft: "",
  mediaPickerOpen: false,
  mediaPickerTarget: "section",
  activeRightTab: "config",

  // SEO drafts
  seoTitleDraft: "",
  seoDescriptionDraft: "",
  seoImageDraft: "",
  seoCanonicalDraft: "",
  seoRobotsDraft: "",
  seoKeyword: "",

  // AI
  aiPrompt: "",
  aiGenerating: false,
  aiOutput: "",
  aiTone: "warm",
  aiTemplate: "aida",
  aiImagePrompt: "",
  aiImageResult: "",
  aiImageGenerating: false,

  // Analytics / A-B testing
  showHeatmap: false,
  timeframe: "7d",
  heatmapType: "clicks",
  abTestingActive: false,
  abTrafficSplit: 50,
  serpPreviewDevice: "desktop",

  // Theme / canvas
  canvasTokens: CANVAS_PREVIEW_TOKENS,
  canvasThemeName: "Por defecto",
  themeLoading: false,
};

// ── Actions ──────────────────────────────────────────────────────────────────

export type PageBuilderAction =
  // Simple field setters — generated for every top-level field.
  | { type: "SET"; field: keyof PageBuilderReducerState; value: unknown }
  // Functional updater — mirrors the ``setFoo(prev => prev + 1)`` useState API.
  | { type: "SET_FN"; field: keyof PageBuilderReducerState; updater: (prev: unknown) => unknown }
  // Batch update — useful when multiple fields change atomically
  // (e.g. loading a page syncs pageTitleDraft + pageSlugDraft + SEO drafts).
  | { type: "BATCH"; updates: Partial<PageBuilderReducerState> }
  // Named compound actions
  | { type: "SET_SITES"; sites: PageBuilderReducerState["sites"] }
  | { type: "SET_PAGES"; pages: CmsPage[]; autoSelectSlug?: string }
  | { type: "LOAD_SECTIONS"; sections: CmsSection[]; versions: CmsPageVersion[]; publishLogs: CmsPublishLog[] }
  | { type: "SYNC_PAGE_DRAFTS"; page: CmsPage }
  | { type: "SET_ACTIVE_SECTION"; sectionId: string | null; fallbackSectionId?: string | null }
  | { type: "UPDATE_SECTION_PROPS"; sectionId: string; props: Record<string, unknown> }
  | { type: "REORDER_SECTIONS"; sections: CmsSection[] }
  | { type: "SET_THEME"; tokens: React.CSSProperties; name: string }
  | { type: "RESET_AI" }
  | { type: "SET_AI_OUTPUT"; output: string };

// ── Reducer ──────────────────────────────────────────────────────────────────

export function pageBuilderReducer(
  state: PageBuilderReducerState,
  action: PageBuilderAction,
): PageBuilderReducerState {
  switch (action.type) {
    case "SET":
      return { ...state, [action.field]: action.value };

    case "SET_FN":
      return { ...state, [action.field]: action.updater(state[action.field]) };

    case "BATCH":
      return { ...state, ...action.updates };

    case "SET_SITES":
      return { ...state, sites: action.sites };

    case "SET_PAGES": {
      const nextActiveSlug =
        action.autoSelectSlug && !state.activeSlug && action.pages.length > 0
          ? action.pages[0].slug
          : state.activeSlug;
      return { ...state, pages: action.pages, activeSlug: nextActiveSlug };
    }

    case "LOAD_SECTIONS": {
      const ordered = [...action.sections].sort(
        (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0),
      );
      // Auto-select first section if current is invalid
      let nextActiveId = state.activeSectionId;
      if (ordered.length > 0) {
        const exists = ordered.some((s) => s.id === state.activeSectionId);
        if (!state.activeSectionId || !exists) {
          nextActiveId = ordered[0].id;
        }
      }
      return {
        ...state,
        sections: ordered,
        versions: action.versions,
        publishLogs: action.publishLogs,
        activeSectionId: nextActiveId,
      };
    }

    case "SYNC_PAGE_DRAFTS": {
      const seo = (action.page.seo_json ?? {}) as Record<string, unknown>;
      return {
        ...state,
        pageTitleDraft: action.page.title ?? "",
        pageSlugDraft: action.page.slug ?? "",
        seoTitleDraft: safeString(seo.meta_title),
        seoDescriptionDraft: safeString(seo.meta_description),
        seoImageDraft: safeString(seo.meta_image),
        seoCanonicalDraft: safeString(seo.canonical_url),
        seoRobotsDraft: safeString(seo.robots_meta),
      };
    }

    case "SET_ACTIVE_SECTION":
      return { ...state, activeSectionId: action.sectionId };

    case "UPDATE_SECTION_PROPS":
      return {
        ...state,
        sections: state.sections.map((s) =>
          s.id === action.sectionId ? { ...s, props_json: action.props } : s,
        ),
      };

    case "REORDER_SECTIONS":
      return {
        ...state,
        sections: action.sections.map((s, i) => ({ ...s, sort_order: i })),
      };

    case "SET_THEME":
      return {
        ...state,
        canvasTokens: { ...CANVAS_PREVIEW_TOKENS, ...action.tokens },
        canvasThemeName: action.name,
      };

    case "RESET_AI":
      return {
        ...state,
        aiPrompt: "",
        aiOutput: "",
        aiImagePrompt: "",
        aiImageResult: "",
      };

    case "SET_AI_OUTPUT":
      return { ...state, aiOutput: action.output };

    default:
      return state;
  }
}

// ── Convenience dispatch helpers ─────────────────────────────────────────────

/**
 * Creates a set of typed dispatch helpers that mirror the original
 * ``useState`` setter API, so callbacks in ``usePageBuilder`` can be
 * migrated incrementally with minimal diff.
 *
 * Usage in the hook:
 *   const [state, dispatch] = useReducer(pageBuilderReducer, initial);
 *   const setters = createSetters(dispatch);
 *   // Then: setters.setSiteKey("new-key") instead of setSiteKey("new-key")
 */
/**
 * Creates stable setter wrappers that match the React ``useState`` setter API
 * exactly — each accepts either a direct value **or** a functional updater.
 *
 * Usage in the hook:
 *   const [state, dispatch] = useReducer(pageBuilderReducer, initial);
 *   const { setters, batch } = createSetters(dispatch);
 *   // Then: setters.setSections(prev => prev.map(...)) or setters.setSaving(true)
 */
export function createSetters(
  dispatch: React.Dispatch<PageBuilderAction>,
): {
  setters: {
    [K in keyof PageBuilderReducerState]: (
      value: PageBuilderReducerState[K] | ((prev: PageBuilderReducerState[K]) => PageBuilderReducerState[K]),
    ) => void;
  };
  batch: (updates: Partial<PageBuilderReducerState>) => void;
} {
  const make = <K extends keyof PageBuilderReducerState>(field: K) =>
    (
      value: PageBuilderReducerState[K] | ((prev: PageBuilderReducerState[K]) => PageBuilderReducerState[K]),
    ) => {
      if (typeof value === "function") {
        dispatch({ type: "SET_FN", field, updater: value as (prev: unknown) => unknown });
      } else {
        dispatch({ type: "SET", field, value });
      }
    };

  // Generate all setters at call time so identities are stable across renders.
  const setters = {} as {
    [K in keyof PageBuilderReducerState]: (
      value: PageBuilderReducerState[K] | ((prev: PageBuilderReducerState[K]) => PageBuilderReducerState[K]),
    ) => void;
  };
  (Object.keys(initialPageBuilderState) as Array<keyof PageBuilderReducerState>).forEach((key) => {
    setters[key] = make(key);
  });

  return {
    setters,
    batch: (updates: Partial<PageBuilderReducerState>) => dispatch({ type: "BATCH", updates }),
  };
}
