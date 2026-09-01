"use client";

import { usePublicBootstrap } from "../PublicBootstrapProvider";

type UiCopy = Record<string, unknown>;

export function uiRecord(value: unknown): UiCopy {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as UiCopy
    : {};
}

/** Copy transversal publicado en la página global footer del CMS. */
export function usePublicUiCopy(): UiCopy {
  const bootstrap = usePublicBootstrap();
  const footer = bootstrap?.footerPage?.sections?.find((section) => section.type === "footer_config");
  return uiRecord(uiRecord(footer?.props_json).public_ui);
}

export function uiText(copy: UiCopy, key: string): string {
  const value = copy[key];
  return typeof value === "string" ? value : "";
}

export function uiList(copy: UiCopy, key: string): string[] {
  const value = copy[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}
