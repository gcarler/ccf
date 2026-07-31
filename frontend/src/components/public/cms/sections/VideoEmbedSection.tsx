"use client";

import React from "react";
import { CmsSection } from "@/types/cms-v2";

export function VideoEmbedSection({ section }: { section: Partial<CmsSection<"video_embed">> }) {
  const title = section.props_json?.title;
  const videoUrl = section.props_json?.video_url || "";
  const caption = section.props_json?.caption;
  const autoplay = Boolean(section.props_json?.autoplay);
  const poster = (section.props_json as { poster?: string } | undefined)?.poster;

  const videoInfo = parseVideoUrl(videoUrl, autoplay);

  return (
    <section className="py-12 md:py-16 px-4 max-w-5xl mx-auto">
      {title && (
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-6 text-gray-900 dark:text-white">
          {title}
        </h2>
      )}
      <div className="relative w-full aspect-video rounded-xl overflow-hidden shadow-lg bg-black border border-gray-200 dark:border-zinc-800">
        {!videoInfo ? (
          <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
            Sin URL de video configurada
          </div>
        ) : videoInfo.type === "youtube" || videoInfo.type === "vimeo" ? (
          <iframe
            src={videoInfo.embedUrl}
            title={title || "Video embed"}
            className="w-full h-full border-0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : (
          <video
            src={videoInfo.embedUrl}
            poster={poster}
            controls
            autoPlay={autoplay}
            muted={autoplay}
            playsInline
            className="w-full h-full object-cover"
          />
        )}
      </div>
      {caption && (
        <p className="mt-3 text-center text-sm text-gray-600 dark:text-gray-400 italic">
          {caption}
        </p>
      )}
    </section>
  );
}

function parseVideoUrl(url: string, autoplay = false) {
  if (!url || typeof url !== "string") return null;

  const trimmed = url.trim();

  // YouTube match
  const ytMatch = trimmed.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
  if (ytMatch && ytMatch[1]) {
    const videoId = ytMatch[1];
    const autoPlayParam = autoplay ? "1" : "0";
    return {
      type: "youtube",
      embedUrl: `https://www.youtube.com/embed/${videoId}?autoplay=${autoPlayParam}&rel=0`,
    };
  }

  // Vimeo match
  const vimeoMatch = trimmed.match(/(?:vimeo\.com\/|player\.vimeo\.com\/video\/)(\d+)/);
  if (vimeoMatch && vimeoMatch[1]) {
    const videoId = vimeoMatch[1];
    const autoPlayParam = autoplay ? "1" : "0";
    return {
      type: "vimeo",
      embedUrl: `https://player.vimeo.com/video/${videoId}?autoplay=${autoPlayParam}`,
    };
  }

  // Direct video
  return {
    type: "direct",
    embedUrl: trimmed,
  };
}
