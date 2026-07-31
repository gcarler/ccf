"use client";

import React from "react";
import { CmsSection } from "@/types/cms-v2";

export function MapEmbedSection({ section }: { section: Partial<CmsSection<"map_embed">> }) {
  const title = section.props_json?.title;
  const address = section.props_json?.address || "";
  const rawLat = section.props_json?.lat;
  const rawLng = section.props_json?.lng;
  const rawZoom = section.props_json?.zoom;
  const rawHeight = section.props_json?.height_px;

  const parseCoord = (val: unknown): number | null => {
    if (val === null || val === undefined || val === "") return null;
    const n = typeof val === "number" ? val : parseFloat(String(val));
    return isNaN(n) ? null : n;
  };

  const lat = parseCoord(rawLat);
  const lng = parseCoord(rawLng);
  const zoom = Number(rawZoom) || 14;
  const heightPx = Number(rawHeight) || 400;

  // Calculate bbox delta based on zoom
  const delta = 360 / Math.pow(2, zoom) / 2;

  let embedUrl = "";
  if (lat !== null && !isNaN(lat) && lng !== null && !isNaN(lng)) {
    const minLng = (lng - delta).toFixed(5);
    const minLat = (lat - delta).toFixed(5);
    const maxLng = (lng + delta).toFixed(5);
    const maxLat = (lat + delta).toFixed(5);
    embedUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${minLng}%2C${minLat}%2C${maxLng}%2C${maxLat}&layer=mapnik&marker=${lat}%2C${lng}`;
  } else if (address) {
    embedUrl = `https://maps.google.com/maps?q=${encodeURIComponent(address)}&output=embed`;
  }

  return (
    <section className="py-12 md:py-16 px-4 max-w-7xl mx-auto">
      {title && (
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-6 text-gray-900 dark:text-white">
          {title}
        </h2>
      )}
      {address && (
        <p className="text-center text-sm font-medium text-gray-600 dark:text-gray-400 mb-6">
          📍 {address}
        </p>
      )}
      <div
        className="w-full rounded-xl overflow-hidden shadow-lg border border-gray-200 dark:border-zinc-800 bg-gray-100 dark:bg-zinc-900"
        style={{ height: `${heightPx}px` }}
      >
        {embedUrl ? (
          <iframe
            src={embedUrl}
            title={title || "Mapa"}
            className="w-full h-full border-0"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
            Sin ubicación o coordenadas para mostrar en el mapa
          </div>
        )}
      </div>
    </section>
  );
}
