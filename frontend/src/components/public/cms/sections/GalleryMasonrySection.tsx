"use client";

import React, { useState, useEffect, useCallback } from "react";
import { CmsSection } from "@/types/cms-v2";
import { X, ChevronLeft, ChevronRight } from "lucide-react";
import OptimizedImage from "@/components/ui/OptimizedImage";

export function GalleryMasonrySection({ section }: { section: Partial<CmsSection<"gallery_masonry">> }) {
  const title = section.props_json?.title;
  const rawColumns = section.props_json?.columns;
  const cols = Number(rawColumns) || 3;
  const rawImages = section.props_json?.images;
  const images = Array.isArray(rawImages) ? rawImages : [];

  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const columnClass =
    cols === 2
      ? "columns-2 gap-4"
      : cols === 3
      ? "columns-2 md:columns-3 gap-4"
      : "columns-2 md:columns-3 lg:columns-4 gap-4";

  const openLightbox = (index: number) => {
    setLightboxIndex(index);
  };

  const closeLightbox = useCallback(() => {
    setLightboxIndex(null);
  }, []);

  const prevImage = useCallback(() => {
    if (lightboxIndex === null || images.length === 0) return;
    setLightboxIndex((prev) => (prev === null ? 0 : (prev - 1 + images.length) % images.length));
  }, [lightboxIndex, images.length]);

  const nextImage = useCallback(() => {
    if (lightboxIndex === null || images.length === 0) return;
    setLightboxIndex((prev) => (prev === null ? 0 : (prev + 1) % images.length));
  }, [lightboxIndex, images.length]);

  useEffect(() => {
    if (lightboxIndex === null) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        closeLightbox();
      } else if (e.key === "ArrowLeft") {
        prevImage();
      } else if (e.key === "ArrowRight") {
        nextImage();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [lightboxIndex, closeLightbox, prevImage, nextImage]);

  return (
    <section className="py-12 md:py-16 px-4 max-w-7xl mx-auto">
      {title && (
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-8 md:mb-12 text-gray-900 dark:text-white">
          {title}
        </h2>
      )}

      <div className={columnClass}>
        {images.map((img, idx) => {
          const imgUrl = img.url || "";
          const imgAlt = img.alt || `Imagen ${idx + 1}`;
          const imgCaption = img.caption;

          if (!imgUrl) return null;

          return (
            <div
              key={idx}
              onClick={() => openLightbox(idx)}
              className="relative mb-4 break-inside-avoid overflow-hidden rounded-xl group cursor-pointer border border-gray-100 dark:border-zinc-800 shadow-sm transition-transform duration-300 hover:-translate-y-0.5"
            >
              <OptimizedImage
                src={imgUrl}
                alt={imgAlt}
                width={800}
                height={600}
                className="w-full h-auto object-cover transition-transform duration-500 group-hover:scale-105"
              />
              {(imgCaption || imgAlt) && (
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end p-4 text-white">
                  <p className="text-sm font-medium line-clamp-2">
                    {imgCaption || imgAlt}
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Lightbox Overlay */}
      {lightboxIndex !== null && images[lightboxIndex] && (
        <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4">
          {/* Close button */}
          <button
            type="button"
            onClick={closeLightbox}
            className="absolute top-4 right-4 text-white/80 hover:text-white p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors z-10"
            aria-label="Cerrar"
          >
            <X size={24} />
          </button>

          {/* Prev button */}
          {images.length > 1 && (
            <button
              type="button"
              onClick={prevImage}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-white/80 hover:text-white p-3 rounded-full bg-white/10 hover:bg-white/20 transition-colors z-10"
              aria-label="Anterior"
            >
              <ChevronLeft size={28} />
            </button>
          )}

          {/* Image & Caption */}
          <div className="max-w-5xl max-h-[85vh] flex flex-col items-center justify-center">
            <OptimizedImage
              src={images[lightboxIndex].url || ""}
              alt={images[lightboxIndex].alt || `Imagen ${lightboxIndex + 1}`}
              width={1200}
              height={900}
              className="max-h-[75vh] w-auto object-contain rounded-lg shadow-2xl"
            />
            {(images[lightboxIndex].caption || images[lightboxIndex].alt) && (
              <p className="mt-4 text-center text-white/90 text-sm md:text-base max-w-2xl px-4">
                {images[lightboxIndex].caption || images[lightboxIndex].alt}
              </p>
            )}
          </div>

          {/* Next button */}
          {images.length > 1 && (
            <button
              type="button"
              onClick={nextImage}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-white/80 hover:text-white p-3 rounded-full bg-white/10 hover:bg-white/20 transition-colors z-10"
              aria-label="Siguiente"
            >
              <ChevronRight size={28} />
            </button>
          )}
        </div>
      )}
    </section>
  );
}
