"use client";

import React, { useMemo } from "react";
import CmsMediaUrlField from "@/components/cms/CmsMediaUrlField";

type JsonValue = Record<string, unknown> | unknown[];
type JsonPath = Array<string | number>;

interface CmsJsonMediaFieldProps {
  label?: string;
  value?: string;
  token?: string | null;
  /** Enables the guided editor for sermon thumbnail overrides on feed sections. */
  allowThumbnailOverrides?: boolean;
  onChange: (value: string) => void;
}

function isMediaKey(key: string): boolean {
  const normalized = key.toLowerCase();
  return normalized.includes("image")
    || normalized.includes("photo")
    || normalized.includes("thumbnail")
    || normalized.includes("poster")
    || normalized.includes("avatar")
    || normalized.includes("cover")
    || normalized.includes("banner")
    || normalized === "img"
    || normalized === "bg";
}

function pathLooksLikeMedia(path: JsonPath): boolean {
  return path.some((part) => {
    const value = String(part).toLowerCase();
    return value.includes("image")
      || value.includes("gallery")
      || value.includes("slide")
      || value.includes("thumbnail")
      || value.includes("poster")
      || value.includes("photo")
      || value.includes("media")
      || value === "img";
  });
}

function parseNestedJson(value: string): Record<string, unknown> | unknown[] | null {
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

function isThumbnailOverridesKey(key: string): boolean {
  return key.toLowerCase() === "thumbnail_overrides";
}

function collectThumbnailOverridePaths(value: unknown, path: JsonPath = []): JsonPath[] {
  if (Array.isArray(value)) {
    return value.flatMap((child, index) => collectThumbnailOverridePaths(child, [...path, index]));
  }
  if (!value || typeof value !== "object") {
    if (typeof value === "string") {
      const parsed = parseNestedJson(value);
      return parsed ? collectThumbnailOverridePaths(parsed, path) : [];
    }
    return [];
  }

  const result: JsonPath[] = [];
  for (const [key, child] of Object.entries(value)) {
    const childPath = [...path, key];
    if (isThumbnailOverridesKey(key) && child && typeof child === "object" && !Array.isArray(child)) {
      result.push(childPath);
      continue;
    }
    if (isThumbnailOverridesKey(key) && typeof child === "string") {
      const parsed = parseNestedJson(child);
      if (parsed && !Array.isArray(parsed)) result.push(childPath);
      continue;
    }
    result.push(...collectThumbnailOverridePaths(child, childPath));
  }
  return result;
}

function looksLikeImageUrl(value: unknown): value is string {
  return typeof value === "string" && /^https?:\/\/|^\/api\/static\//i.test(value)
    && /\.(?:avif|gif|jpe?g|png|svg|webp)(?:[?#].*)?$/i.test(value);
}

function collectMediaPaths(value: unknown, path: JsonPath = []): Array<{ path: JsonPath; value: string }> {
  if (Array.isArray(value)) {
    return value.flatMap((child, index) => collectMediaPaths(child, [...path, index]));
  }
  if (!value || typeof value !== "object") return [];

  const result: Array<{ path: JsonPath; value: string }> = [];
  for (const [key, child] of Object.entries(value)) {
    const childPath = [...path, key];
    if (typeof child === "string" && (isMediaKey(key) || (key === "src" && pathLooksLikeMedia(childPath)) || looksLikeImageUrl(child))) {
      result.push({ path: childPath, value: child });
      continue;
    }
    if (typeof child === "string") {
      const nested = parseNestedJson(child);
      if (nested) result.push(...collectMediaPaths(nested, childPath));
    } else {
      result.push(...collectMediaPaths(child, childPath));
    }
  }
  return result;
}

function getAtPath(value: unknown, path: JsonPath): unknown {
  if (path.length === 0) return value;
  if (typeof value === "string") {
    const parsed = parseNestedJson(value);
    return parsed ? getAtPath(parsed, path) : undefined;
  }
  if (value === null || typeof value !== "object") return undefined;
  return getAtPath((value as Record<string | number, unknown>)[path[0]], path.slice(1));
}

function updateAtPath(value: unknown, path: JsonPath, nextValue: unknown): unknown {
  if (path.length === 0) return nextValue;
  if (typeof value === "string") {
    const parsed = parseNestedJson(value);
    if (!parsed) return value;
    return JSON.stringify(updateAtPath(parsed, path, nextValue), null, 2);
  }
  if (!value || typeof value !== "object") return value;
  if (Array.isArray(value)) {
    const index = path[0];
    if (typeof index !== "number") return value;
    const clone = [...value];
    clone[index] = updateAtPath(clone[index], path.slice(1), nextValue);
    return clone;
  }
  const clone = { ...(value as Record<string, unknown>) };
  const key = String(path[0]);
  clone[key] = updateAtPath(clone[key], path.slice(1), nextValue);
  return clone;
}

function setAtPath(value: JsonValue, path: JsonPath, nextValue: unknown): JsonValue {
  return updateAtPath(value, path, nextValue) as JsonValue;
}

export default function CmsJsonMediaField({
  label = "Contenido editable (JSON)",
  value = "{}",
  token,
  allowThumbnailOverrides = false,
  onChange,
}: CmsJsonMediaFieldProps) {
  const parsed = useMemo<JsonValue | null>(() => {
    try {
      const candidate = JSON.parse(value);
      return candidate && typeof candidate === "object" && !Array.isArray(candidate) ? candidate : null;
    } catch {
      return null;
    }
  }, [value]);

  const mediaPaths = useMemo(() => (parsed ? collectMediaPaths(parsed) : []), [parsed]);
  const thumbnailOverridePaths = useMemo(() => (parsed ? collectThumbnailOverridePaths(parsed) : []), [parsed]);
  const looksLikeSermonFeed = allowThumbnailOverrides && Boolean(
    parsed && ["hero_eyebrow", "youtube_channel_url", "thumbnail_overrides"].some((key) => JSON.stringify(parsed).includes(key)),
  );

  const updateJson = (path: JsonPath, nextValue: unknown) => {
    if (!parsed) return;
    onChange(JSON.stringify(setAtPath(parsed, path, nextValue), null, 2));
  };

  const updateMedia = (path: JsonPath, nextValue: string) => updateJson(path, nextValue);

  const renameThumbnailOverride = (path: JsonPath, oldKey: string, nextKey: string) => {
    if (!parsed || !nextKey.trim() || oldKey === nextKey) return;
    const current = getAtPath(parsed, path);
    if (!current || typeof current !== "object" || Array.isArray(current)) return;
    const next = { ...(current as Record<string, unknown>) };
    const normalizedKey = nextKey.trim();
    if (normalizedKey in next && normalizedKey !== oldKey) return;
    const value = next[oldKey] ?? "";
    delete next[oldKey];
    next[normalizedKey] = value;
    updateJson(path, next);
  };

  const enableThumbnailOverrides = () => {
    if (!parsed) return;
    const content = getAtPath(parsed, ["content"]);
    const nested = typeof content === "string" ? parseNestedJson(content) : null;
    if (nested && !Array.isArray(nested)) {
      updateJson(["content"], JSON.stringify({ ...(nested as Record<string, unknown>), thumbnail_overrides: {} }, null, 2));
      return;
    }
    updateJson([], { ...parsed, thumbnail_overrides: {} });
  };

  const addThumbnailOverride = (path: JsonPath) => {
    const current = getAtPath(parsed, path);
    if (!current || typeof current !== "object" || Array.isArray(current)) return;
    const next = { ...(current as Record<string, unknown>) };
    let key = `video-${Object.keys(next).length + 1}`;
    while (key in next) key = `${key}-nuevo`;
    next[key] = "";
    updateJson(path, next);
  };

  return (
    <div className="space-y-3">
      <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">{label}</label>
      {looksLikeSermonFeed && thumbnailOverridePaths.length === 0 && (
        <div className="flex items-center justify-between gap-3 rounded-md border border-[hsl(var(--border))] p-3 dark:border-white/10">
          <div>
            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Miniaturas de prédicas</p>
            <p className="mt-1 text-2xs text-[hsl(var(--text-secondary))]">Activa overrides para reemplazar miniaturas de YouTube desde la biblioteca CMS.</p>
          </div>
          <button
            type="button"
            onClick={enableThumbnailOverrides}
            className="shrink-0 rounded-md bg-[hsl(var(--primary))] px-2.5 py-1.5 text-2xs font-semibold text-white hover:bg-[hsl(var(--primary-hover))]"
          >
            Activar selector
          </button>
        </div>
      )}
      {thumbnailOverridePaths.map((path) => {
        const overrides = getAtPath(parsed, path);
        if (!overrides || typeof overrides !== "object" || Array.isArray(overrides)) return null;
        return (
          <div key={`overrides-${path.join(".")}`} className="space-y-3 rounded-md border border-[hsl(var(--border))] p-3 dark:border-white/10">
            <div className="flex items-center justify-between gap-3">
              <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Miniaturas de prédicas
              </p>
              <button
                type="button"
                onClick={() => addThumbnailOverride(path)}
                className="rounded-md border border-[hsl(var(--border))] px-2 py-1 text-2xs font-semibold hover:bg-black/5 dark:border-white/10 dark:hover:bg-white/5"
              >
                Añadir video
              </button>
            </div>
            {Object.entries(overrides as Record<string, unknown>).map(([videoId, imageUrl]) => (
              <div key={`${path.join(".")}-${videoId}`} className="space-y-2 rounded-md bg-black/[0.02] p-2 dark:bg-white/[0.03]">
                <input
                  aria-label={`ID de video ${videoId}`}
                  value={videoId}
                  onChange={(event) => renameThumbnailOverride(path, videoId, event.target.value)}
                  className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-xs dark:border-white/10 dark:bg-[hsl(var(--admin-bg-secondary))]"
                  placeholder="ID del video de YouTube"
                />
                <CmsMediaUrlField
                  label="Imagen de miniatura"
                  value={String(imageUrl || "")}
                  token={token}
                  onChange={(nextValue) => updateJson([...path, videoId], nextValue)}
                />
              </div>
            ))}
            {Object.keys(overrides).length === 0 && (
              <p className="text-2xs text-[hsl(var(--text-secondary))]">Añade un ID de video para seleccionar una miniatura desde la biblioteca CMS.</p>
            )}
          </div>
        );
      })}
      {mediaPaths.length > 0 && (
        <div className="space-y-3 rounded-md border border-[hsl(var(--border))] p-3 dark:border-white/10">
          <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
            Imágenes de esta sección
          </p>
          {mediaPaths.map(({ path }) => (
            <CmsMediaUrlField
              key={path.join(".")}
              label={path.join(" / ")}
              value={String(getAtPath(parsed, path) || "")}
              token={token}
              onChange={(nextValue) => updateMedia(path, nextValue)}
            />
          ))}
        </div>
      )}
      <textarea
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-48 w-full rounded-md border border-[hsl(var(--border))] bg-transparent p-3 font-mono text-xs dark:border-white/10"
        spellCheck={false}
      />
      <p className="text-3xs text-[hsl(var(--text-secondary))]">
        Las rutas de imagen detectadas pueden seleccionarse desde la biblioteca CMS sin editar la URL a mano.
      </p>
    </div>
  );
}
