"use client";

import React, { useState } from "react";
import { Headphones, ImageIcon, LinkIcon, PlayCircle, Send, Smile } from "lucide-react";
import { apiFetch } from "@/lib/http";

interface TestimonialFormProps {
  userId: number;
  token: string;
  onSubmitted?: () => void;
}

export default function TestimonialForm({ userId, token, onSubmitted }: TestimonialFormProps) {
  const [content, setContent] = useState("");
  const [emotion, setEmotion] = useState("Feliz");
  const [mediaType, setMediaType] = useState<"text" | "image" | "video" | "podcast">("text");
  const [imageUrl, setImageUrl] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [podcastUrl, setPodcastUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!token) {
      setMessage("Inicia sesion para enviar un testimonio.");
      return;
    }

    setIsSubmitting(true);

    try {
      await apiFetch("/cms/testimonials", {
        method: "POST",
        token,
        body: {
          content,
          emotion,
          media_type: mediaType,
          media_url: mediaType === "image" ? imageUrl : mediaType === "video" ? videoUrl : mediaType === "podcast" ? podcastUrl : null,
          image_url: imageUrl || null,
          video_url: videoUrl || null,
          podcast_url: podcastUrl || null,
          author_id: userId,
        },
      });

        setMessage("Gracias. Tu testimonio fue enviado para moderacion.");
        setContent("");
        setImageUrl("");
        setVideoUrl("");
        setPodcastUrl("");
        if (onSubmitted) onSubmitted();
    } catch (error) {
      console.error("testimonial error", error);
      setMessage("Hubo un error al enviar el testimonio.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-card relative mx-auto my-12 max-w-xl overflow-hidden p-8">
      <div className="absolute right-0 top-0 p-4 text-primary/20">
        <Smile size={80} />
      </div>

      <h3 className="relative z-10 mb-6 text-2xl font-bold">Comparte tu experiencia</h3>

      <form onSubmit={handleSubmit} className="relative z-10 space-y-6">
        <div>
          <label className="mb-2 block text-sm font-medium">Tu testimonio</label>
          <textarea
            required
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="h-32 w-full resize-none rounded-xl border border-slate-200 bg-white/70 p-4 outline-none transition-all focus:border-transparent focus:ring-2 focus:ring-primary"
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
                    : "border-slate-300 bg-white/70 hover:bg-slate-100"
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
                onClick={() => setMediaType(option.id as typeof mediaType)}
                className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-2 text-xs font-black uppercase tracking-widest transition-all ${
                  mediaType === option.id
                    ? "border-primary bg-primary text-white"
                    : "border-slate-300 bg-white/70 text-slate-600 hover:bg-slate-100"
                }`}
              >
                <option.icon size={14} /> {option.label}
              </button>
            ))}
          </div>
          {mediaType !== "text" && (
            <label className="block space-y-2">
              <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-slate-500">
                <LinkIcon size={13} /> URL de {mediaType === "image" ? "imagen" : mediaType === "video" ? "video" : "podcast"}
              </span>
              <input
                type="url"
                value={mediaType === "image" ? imageUrl : mediaType === "video" ? videoUrl : podcastUrl}
                onChange={(event) => {
                  if (mediaType === "image") setImageUrl(event.target.value);
                  if (mediaType === "video") setVideoUrl(event.target.value);
                  if (mediaType === "podcast") setPodcastUrl(event.target.value);
                }}
                placeholder="Pega la URL desde la biblioteca de medios"
                className="w-full rounded-xl border border-slate-200 bg-white/70 px-4 py-3 text-sm outline-none transition-all focus:border-transparent focus:ring-2 focus:ring-primary"
              />
            </label>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-4 font-bold text-white transition-colors hover:bg-blue-600 disabled:opacity-50"
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

