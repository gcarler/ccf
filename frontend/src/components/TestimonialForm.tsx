"use client";

import React, { useState } from "react";
import { Send, Smile } from "lucide-react";
import { apiFetch } from "@/lib/http";

interface TestimonialFormProps {
  userId: number;
  token: string;
  onSubmitted?: () => void;
}

export default function TestimonialForm({ userId, token, onSubmitted }: TestimonialFormProps) {
  const [content, setContent] = useState("");
  const [emotion, setEmotion] = useState("Feliz");
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
      await apiFetch("/testimonials", {
        method: "POST",
        token,
        body: {
          content,
          emotion,
          author_id: userId,
        },
      });

        setMessage("Gracias. Tu testimonio fue enviado para moderacion.");
        setContent("");
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
