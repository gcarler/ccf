"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Headphones, ImageIcon, LinkIcon, PlayCircle, Send, Smile } from "lucide-react";
import { apiFetch } from "@/lib/http";
import {
  activeTestimonialMediaAssets,
  TestimonialMediaAsset,
  TestimonialMediaType,
} from "@/lib/cms/testimonialMedia";

interface TestimonialFormProps {
  userId?: number | string | null;
  authorPersonaId?: string | null;
  token: string;
  onSubmitted?: () => void;
}

const isUuid = (value: unknown) =>
  typeof value === "string" &&
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);

export default function TestimonialForm({ userId, authorPersonaId, token, onSubmitted }: TestimonialFormProps) {
  const [content, setContent] = useState("");
  const [emotion, setEmotion] = useState("Feliz");
  const [mediaType, setMediaType] = useState<TestimonialMediaType>("text");
  const [imageUrl, setImageUrl] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [podcastUrl, setPodcastUrl] = useState("");
  const [mediaItems, setMediaItems] = useState<TestimonialMediaAsset[]>([]);
  const [mediaSearch, setMediaSearch] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setMediaItems([]);
      return;
    }

    apiFetch<{ items: TestimonialMediaAsset[]; total: number }>("/cms/media", { token, cache: "no-store" })
      .then((data) => setMediaItems(data?.items || []))
      .catch(() => setMediaItems([]));
  }, [token]);

  const activeMediaUrl = useMemo(() => {
    if (mediaType === "image") return imageUrl;
    if (mediaType === "video") return videoUrl;
    if (mediaType === "podcast") return podcastUrl;
    return "";
  }, [imageUrl, mediaType, podcastUrl, videoUrl]);

  const compatibleMedia = useMemo(
    () => activeTestimonialMediaAssets(mediaItems, mediaType, mediaSearch, 6),
    [mediaItems, mediaSearch, mediaType],
  );

  const setActiveMediaUrl = (value: string) => {
    if (mediaType === "image") setImageUrl(value);
    if (mediaType === "video") setVideoUrl(value);
    if (mediaType === "podcast") setPodcastUrl(value);
  };

  const selectMediaType = (nextType: TestimonialMediaType) => {
    setMediaType(nextType);
    setMediaSearch("");
    if (nextType === "text" || nextType !== mediaType) {
      setImageUrl("");
      setVideoUrl("");
      setPodcastUrl("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!token) {
      setMessage("Inicia sesion para enviar un testimonio.");
      return;
    }

    setIsSubmitting(true);
    const submittedMediaType = mediaType === "text" || !activeMediaUrl.trim() ? "text" : mediaType;
    const submittedMediaUrl = submittedMediaType === "text" ? null : activeMediaUrl.trim();

	    try {
	      const authorPayload = {
	        ...(authorPersonaId || isUuid(userId) ? { author_persona_id: authorPersonaId || String(userId) } : {}),
	      };
      await apiFetch("/cms/testimonials", {
        method: "POST",
        token,
        body: {
          content,
          emotion,
          media_type: submittedMediaType,
          media_url: submittedMediaUrl,
          image_url: submittedMediaType === "image" ? submittedMediaUrl : null,
          video_url: submittedMediaType === "video" ? submittedMediaUrl : null,
          podcast_url: submittedMediaType === "podcast" ? submittedMediaUrl : null,
          ...authorPayload,
        },
      });

        setMessage("Gracias. Tu testimonio fue enviado para moderacion.");
        setContent("");
        setImageUrl("");
        setVideoUrl("");
        setPodcastUrl("");
        setMediaType("text");
        setMediaSearch("");
        if (onSubmitted) onSubmitted();
    } catch (error) {
      console.error("testimonial error", error);
      setMessage("Hubo un error al enviar el testimonio.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-card relative mx-auto my-12 max-w-xl overflow-hidden p-4">
      <div className="absolute right-0 top-0 p-4 text-primary/20">
        <Smile size={80} />
      </div>

      <h3 className="relative z-10 mb-3 text-lg font-bold">Comparte tu experiencia</h3>

      <form onSubmit={handleSubmit} className="relative z-10 space-y-3">
        <div>
          <label className="mb-2 block text-sm font-medium">Tu testimonio</label>
          <textarea
            required
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="h-32 w-full resize-none rounded-md border border-[hsl(var(--border))] bg-white/70 p-4 outline-none transition-all focus:border-transparent focus:ring-2 focus:ring-primary"
            placeholder="Como ha sido tu proceso en la plataforma?..."
          />
        </div>

        <div>
          <label className="mb-3 block text-sm font-medium">Como te sientes hoy?</label>
          <div className="flex flex-wrap gap-3">
            {["Feliz", "Inspirado", "Agradecido", "Motivado"].map((emo) => (
              <button
                key={emo}
                type="button"
                onClick={() => setEmotion(emo)}
                className={`rounded-full border px-4 py-2 transition-all ${
                  emotion === emo
                    ? "border-primary bg-primary text-white"
                    : "border-[hsl(var(--border))] bg-white/70 hover:bg-[hsl(var(--surface-2))]"
                }`}
              >
                {emo}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <label className="block text-sm font-medium">Medio asociado (opcional)</label>
          <div className="grid grid-cols-2 gap-2">
            {[
              { id: "text", label: "Solo texto", icon: Smile },
              { id: "image", label: "Imagen", icon: ImageIcon },
              { id: "video", label: "Video", icon: PlayCircle },
              { id: "podcast", label: "Podcast", icon: Headphones },
            ].map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => selectMediaType(option.id as TestimonialMediaType)}
                className={`flex items-center justify-center gap-2 rounded-md border px-3 py-2 text-xs font-semibold uppercase tracking-wide transition-all ${
                  mediaType === option.id
                    ? "border-primary bg-primary text-white"
                    : "border-[hsl(var(--border))] bg-white/70 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]"
                }`}
              >
                <option.icon size={14} /> {option.label}
              </button>
            ))}
          </div>
          {mediaType !== "text" && (
            <div className="space-y-3">
              <label className="block space-y-2">
                <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                  <LinkIcon size={13} /> URL de {mediaType === "image" ? "imagen" : mediaType === "video" ? "video" : "podcast"}
                </span>
                <input
                  type="url"
                  value={activeMediaUrl}
                  onChange={(event) => setActiveMediaUrl(event.target.value)}
                  placeholder="Pega una URL o elige desde la biblioteca"
                  className="w-full rounded-md border border-[hsl(var(--border))] bg-white/70 px-4 py-3 text-sm outline-none transition-all focus:border-transparent focus:ring-2 focus:ring-primary"
                />
              </label>

              <div className="rounded-lg border border-[hsl(var(--border))] bg-white/70 p-3">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Biblioteca CMS</span>
                  <Link href="/plataforma/cms/media" className="text-[10px] font-semibold uppercase tracking-wide text-primary hover:underline">
                    Subir media
                  </Link>
                </div>
                <input
                  value={mediaSearch}
                  onChange={(event) => setMediaSearch(event.target.value)}
                  placeholder="Buscar archivo..."
                  className="mb-3 w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-primary/20"
                />
                {compatibleMedia.length === 0 ? (
                  <p className="rounded-md bg-[hsl(var(--surface-1))] px-3 py-3 text-xs font-medium text-[hsl(var(--text-secondary))]">
                    No hay archivos compatibles. Sube primero imagenes, videos o audios en la biblioteca.
                  </p>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    {compatibleMedia.map((item) => (
                      <button
                        key={item.id ?? item.url}
                        type="button"
                        onClick={() => setActiveMediaUrl(item.url)}
                        className={`flex items-center gap-2 rounded-md border px-3 py-2 text-left transition-all ${
                          activeMediaUrl === item.url
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-secondary))] hover:border-primary/40"
                        }`}
                      >
                        {mediaType === "image" ? <ImageIcon size={14} /> : mediaType === "video" ? <PlayCircle size={14} /> : <Headphones size={14} />}
                        <span className="min-w-0 truncate text-[11px] font-bold">{item.filename || item.url}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-primary py-1.5 font-bold text-white transition-colors hover:bg-[hsl(var(--primary))] disabled:opacity-50"
        >
          {isSubmitting ? "Enviando..." : <><Send size={18} /> Publicar testimonio</>}
        </button>

        {message && (
          <p className={`text-center text-sm font-medium ${message.includes("Gracias") ? "text-emerald-600" : "text-rose-600"}`}>
            {message}
          </p>
        )}
      </form>
    </div>
  );
}
