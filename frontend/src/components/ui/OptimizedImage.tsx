"use client";

import Image from "next/image";
import { useState } from "react";

/**
 * OptimizedImage — replaces raw <img> tags and unoptimized next/image.
 *
 * - Uses Next.js <Image> with fill/sizes for automatic responsive resizing.
 * - Server-side sharp converts JPEG/PNG to WebP at build time.
 * - Shows a subtle loading blur placeholder while the image loads.
 * - If the image fails to load, it switches to an inline fallback SVG.
 *
 * Usage
 * -----
 * ```tsx
 * <OptimizedImage src="/api/static/course/abc.webp" alt="Curso" className="..." />
 * ```
 *
 * Props mirror a subset of next/image.  Pass `width` and `height` when you know
 * them; otherwise use `fill` + `sizes` (preferred for CMS content).
 */
interface Props {
  src: string;
  alt: string;
  fill?: boolean;
  width?: number;
  height?: number;
  sizes?: string;
  className?: string;
  priority?: boolean;
  loading?: "lazy" | "eager";
  objectFit?: "cover" | "contain" | "fill" | "none" | "scale-down";
}

export default function OptimizedImage({
  src,
  alt,
  fill,
  width,
  height,
  sizes,
  className,
  priority = false,
  loading,
  objectFit = "cover",
}: Props) {
  const [error, setError] = useState(false);

  if (!src || error) {
    return (
      <div
        className={className || "flex items-center justify-center bg-slate-100 dark:bg-slate-800"}
        style={fill ? { position: "relative", width: "100%", height: "100%" } : { width, height }}
        aria-label={alt || "Imagen no disponible"}
      >
        <svg
          className="w-8 h-8 text-slate-300 dark:text-slate-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
          />
        </svg>
      </div>
    );
  }

  return (
    <Image
      src={src}
      alt={alt}
      fill={fill}
      width={!fill ? width : undefined}
      height={!fill ? height : undefined}
      sizes={sizes}
      className={className}
      priority={priority}
      loading={loading}
      style={fill || !width ? { objectFit } : undefined}
      onError={() => setError(true)}
    />
  );
}
