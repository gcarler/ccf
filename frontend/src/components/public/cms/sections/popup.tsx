"use client";

import { CmsSection } from "@/types/cms-v2";
import type { PopupProps } from "@/types/cms-section-props";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { normalizePopupProps, shouldRenderCmsPopup } from "@/lib/cms/heroPopup";
import { asProps } from "./shared";

export function PopupBlock({ section }: { section: CmsSection<"popup_banner"> }) {
  const props: PopupProps = section.props_json ?? {};
  const popup = normalizePopupProps(asProps(props), section.id);
  const pathname = usePathname() || "/";
  const titleId = `cms-popup-title-${section.id}`;
  const bodyId = `cms-popup-body-${section.id}`;
  const [isVisible, setIsVisible] = useState(false);
  const shouldRenderForRoute = useMemo(() => {
    return shouldRenderCmsPopup(popup, pathname);
  }, [pathname, popup]);

  const isDismissed = useCallback(() => {
    if (popup.dismissMode === "none") return false;
    if (typeof window === "undefined") return false;
    try {
      const storage = popup.dismissMode === "session" ? window.sessionStorage : window.localStorage;
      const raw = storage.getItem(popup.dismissKey);
      if (!raw) return false;
      if (popup.dismissMode === "session") return raw === "closed";
      const parsed = JSON.parse(raw) as { expiresAt?: number } | string;
      if (typeof parsed === "string") return parsed === "closed";
      if (parsed?.expiresAt && Date.now() > parsed.expiresAt) {
        storage.removeItem(popup.dismissKey);
        return false;
      }
      return true;
    } catch {
      return false;
    }
  }, [popup.dismissKey, popup.dismissMode]);

  const handleClose = useCallback(() => {
    setIsVisible(false);
    if (popup.dismissMode === "none") return;
    if (typeof window === "undefined") return;
    try {
      const storage = popup.dismissMode === "session" ? window.sessionStorage : window.localStorage;
      if (popup.dismissMode === "session") {
        storage.setItem(popup.dismissKey, "closed");
      } else {
        storage.setItem(popup.dismissKey, JSON.stringify({
          closedAt: Date.now(),
          expiresAt: Date.now() + popup.dismissDays * 24 * 60 * 60 * 1000,
        }));
      }
    } catch {
      // ignore storage failures
    }
  }, [popup.dismissDays, popup.dismissKey, popup.dismissMode]);

  useEffect(() => {
    if (!shouldRenderForRoute || isDismissed()) {
      setIsVisible(false);
      return;
    }
    const timer = setTimeout(() => setIsVisible(true), popup.delayMs);
    return () => clearTimeout(timer);
  }, [isDismissed, popup.delayMs, shouldRenderForRoute]);

  useEffect(() => {
    if (!isVisible) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isVisible]);

  useEffect(() => {
    if (!isVisible) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") handleClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleClose, isVisible]);

  if (!shouldRenderForRoute) {
    return null;
  }

  return (
    <AnimatePresence>
      {isVisible && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="absolute inset-0 backdrop-blur-sm"
            style={{ background: "rgba(0,0,0,0.5)" }}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: 24 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 24 }}
            className="relative w-full max-w-md rounded-2xl p-8 shadow-2xl"
            style={{ background: "var(--site-surface-container)" }}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={popup.body ? bodyId : undefined}
          >
            <button
              type="button"
              onClick={handleClose}
              aria-label="Cerrar pop-up"
              className="absolute top-4 right-4 p-2 rounded-full transition-colors"
              style={{ background: "var(--site-surface-container-high, rgba(0,0,0,0.05))" }}
            >
              <X size={18} style={{ color: "var(--site-on-surface-variant)" }} />
            </button>
            <div className="text-center mt-2">
              <h2 id={titleId} className="text-xl font-black mb-3" style={{ color: "var(--site-on-surface)" }}>{popup.title}</h2>
              {popup.body && <p id={bodyId} className="text-sm leading-relaxed mb-6" style={{ color: "var(--site-on-surface-variant)" }}>{popup.body}</p>}
              <div className="flex flex-col gap-3">
                {popup.ctaLabel && popup.ctaHref && (
                  <Link
                    href={popup.ctaHref}
                    onClick={handleClose}
                    className="w-full py-3 rounded-full text-sm font-black uppercase tracking-widest text-white text-center transition-transform hover:scale-[1.02]"
                    style={{ background: "var(--site-cta-gradient)" }}
                  >
                    {popup.ctaLabel}
                  </Link>
                )}
                <button
                  type="button"
                  onClick={handleClose}
                  className="w-full py-3 rounded-full text-sm font-bold transition-opacity hover:opacity-70"
                  style={{ color: "var(--site-on-surface-variant)" }}
                >
                  No, gracias
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

// ─── Button Row ────────────────────────────────────────────────────────────────
