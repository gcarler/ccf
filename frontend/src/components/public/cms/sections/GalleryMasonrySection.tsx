"use client";

import React, { useState, useEffect, useCallback } from "react";
import { CmsSection } from "@/types/cms-v2";
import { X, ChevronLeft, ChevronRight } from "lucide-react";
import OptimizedImage from "@/components/ui/OptimizedImage";

export function GalleryMasonrySection({ section }: { section: Partial<CmsSection<"gallery_masonry">> }) {
  const title = section.props_json?.title;
  const body = section.props_json?.body;
  const layout = section.props_json?.layout || "masonry";
  const albumUrl = section.props_json?.album_url || "";
  const albumLabel = section.props_json?.album_label || "Ver más fotos";
  const autoplay = Boolean(section.props_json?.autoplay);
  const fullBleed = Boolean(section.props_json?.full_bleed);
  const rawColumns = section.props_json?.columns;
  const cols = Number(rawColumns) || 3;
  const rawImages = section.props_json?.images;
  const images = Array.isArray(rawImages) ? rawImages : [];

  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [carouselIndex, setCarouselIndex] = useState(0);

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

  const nextCarousel = useCallback(() => {
    if (images.length < 2) return;
    setCarouselIndex((current) => (current + 1) % images.length);
  }, [images.length]);

  const prevCarousel = useCallback(() => {
    if (images.length < 2) return;
    setCarouselIndex((current) => (current - 1 + images.length) % images.length);
  }, [images.length]);

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

  useEffect(() => {
    if (layout !== "carousel" || !autoplay || images.length < 2) return;
    const timer = window.setInterval(nextCarousel, 5000);
    return () => window.clearInterval(timer);
  }, [layout, autoplay, images.length, nextCarousel]);

  const isCarousel = layout === "carousel";

  return (
    <section className={`py-12 md:py-16 ${fullBleed ? "relative left-1/2 w-screen -translate-x-1/2 max-w-none px-0" : "mx-auto max-w-7xl px-4"}`}>
      {title && (
        <h2
          className="mx-auto mb-8 max-w-4xl px-4 text-center text-3xl font-black tracking-tight md:mb-12 md:text-4xl lg:text-5xl"
          style={{ color: "var(--site-on-surface)" }}
        >
          {title}
        </h2>
      )}

      {body && <p className="mx-auto mb-8 max-w-2xl px-4 text-center text-sm leading-relaxed text-gray-600 dark:text-gray-300">{body}</p>}

      {isCarousel ? (
        <div className="relative">
          <div className={`overflow-hidden bg-gray-100 shadow-xl dark:bg-zinc-900 ${fullBleed ? "rounded-none" : "rounded-2xl"}`}>
            {images.length > 0 ? (
              <button
                type="button"
                onClick={() => setLightboxIndex(carouselIndex)}
                className="relative block aspect-[4/3] w-full cursor-zoom-in sm:aspect-[16/9]"
                aria-label={`Ampliar ${images[carouselIndex]?.alt || `imagen ${carouselIndex + 1}`}`}
              >
                <OptimizedImage
                  src={images[carouselIndex]?.url || ""}
                  alt={images[carouselIndex]?.alt || `Imagen ${carouselIndex + 1}`}
                  fill
                  sizes="(max-width: 640px) 100vw, 1200px"
                  className="object-cover"
                />
                {(images[carouselIndex]?.caption || images[carouselIndex]?.alt) && (
                  <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent px-5 pb-5 pt-12 text-left text-sm font-medium text-white">
                    {images[carouselIndex]?.caption || images[carouselIndex]?.alt}
                  </span>
                )}
              </button>
            ) : (
              <div className="flex aspect-[4/3] items-center justify-center text-sm text-gray-500 sm:aspect-[16/9]">Añade imágenes desde el editor CMS.</div>
            )}
          </div>
          {images.length > 1 && (
            <>
              <button type="button" onClick={prevCarousel} aria-label="Foto anterior" className="absolute left-3 top-1/2 -translate-y-1/2 rounded-full bg-black/55 p-3 text-white transition hover:bg-black/75">
                <ChevronLeft size={24} />
              </button>
              <button type="button" onClick={nextCarousel} aria-label="Foto siguiente" className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full bg-black/55 p-3 text-white transition hover:bg-black/75">
                <ChevronRight size={24} />
              </button>
              <div className="mt-4 flex justify-center gap-1.5" aria-label="Selector de fotografía">
                {images.map((_, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => setCarouselIndex(index)}
                    aria-label={`Ir a la imagen ${index + 1}`}
                    className={`h-2 rounded-full transition-all ${index === carouselIndex ? "w-6 bg-[hsl(var(--primary))]" : "w-2 bg-gray-300 dark:bg-zinc-700"}`}
                  />
                ))}
              </div>
            </>
          )}
          {albumUrl && (
            <div className="mt-7 text-center">
              <a href={albumUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center rounded-full bg-[hsl(var(--primary))] px-6 py-3 text-sm font-bold text-white shadow-lg transition hover:-translate-y-0.5 hover:shadow-xl">
                {albumLabel}
              </a>
            </div>
          )}
        </div>
      ) : (

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
      )}

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
