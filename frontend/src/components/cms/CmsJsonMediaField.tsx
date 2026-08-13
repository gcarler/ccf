"use client";

import React, { useMemo } from "react";
import CmsMediaUrlField from "@/components/cms/CmsMediaUrlField";

type JsonValue = Record<string, unknown> | unknown[];
type JsonPath = Array<string | number>;

interface CmsJsonMediaFieldProps {
  label?: string;
  value?: string;
  token?: string | null;
  onChange: (value: string) => void;
}

function isMediaKey(key: string): boolean {
  const normalized = key.toLowerCase();
  return normalized.includes("image")
    || normalized.includes("photo")
    || normalized.includes("thumbnail")
    || normalized.includes("poster")
    || normalized === "img"
    || normalized === "bg";
}

function pathLooksLikeMedia(path: JsonPath): boolean {
  return path.some((part) => {
    const value = String(part).toLowerCase();
    return value.includes("image") || value.includes("gallery") || value.includes("slide") || value === "img";
  });
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
    result.push(...collectMediaPaths(child, childPath));
  }
  return result;
}

function getAtPath(value: unknown, path: JsonPath): unknown {
  return path.reduce<unknown>((current, part) => {
    if (current === null || typeof current !== "object") return undefined;
    return (current as Record<string | number, unknown>)[part];
  }, value);
}

function setAtPath(value: JsonValue, path: JsonPath, nextValue: string): JsonValue {
  const clone = JSON.parse(JSON.stringify(value)) as JsonValue;
  let current: any = clone;
  path.slice(0, -1).forEach((part) => {
    current = current[part];
  });
  current[path[path.length - 1]] = nextValue;
  return clone;
}

export default function CmsJsonMediaField({ label = "Contenido editable (JSON)", value = "{}", token, onChange }: CmsJsonMediaFieldProps) {
  const parsed = useMemo<JsonValue | null>(() => {
    try {
      const candidate = JSON.parse(value);
      return candidate && typeof candidate === "object" && !Array.isArray(candidate) ? candidate : null;
    } catch {
      return null;
    }
  }, [value]);

  const mediaPaths = useMemo(() => (parsed ? collectMediaPaths(parsed) : []), [parsed]);

  const updateMedia = (path: JsonPath, nextValue: string) => {
    if (!parsed) return;
    onChange(JSON.stringify(setAtPath(parsed, path, nextValue), null, 2));
  };

  return (
    <div className="space-y-3">
      <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">{label}</label>
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
