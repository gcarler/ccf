"use client";

import React, { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { listPublicPopups } from "@/lib/cms/v2";
import { CmsPublicPopup } from "@/types/cms-v2";
import { SITE_KEY } from "@/lib/site-config";
import { sanitizeCmsHtml } from "@/lib/cms/sanitize";

function matchesPath(pattern: string, pathname: string | null | undefined): boolean {
  if (!pattern || pattern === "*") return true;
  if (!pathname) return false;
  if (pattern === pathname) return true;
  if (pattern.endsWith("*")) {
    const prefix = pattern.slice(0, -1);
    return pathname.startsWith(prefix);
  }
  return false;
}

export function PopupManager() {
  const pathname = usePathname();
  const [activePopup, setActivePopup] = useState<CmsPublicPopup | null>(null);
  const [popups, setPopups] = useState<CmsPublicPopup[]>([]);

  // 1. Fetch active public popups on mount
  useEffect(() => {
    let isMounted = true;
    listPublicPopups(SITE_KEY)
      .then((data) => {
        if (isMounted && Array.isArray(data)) {
          setPopups(data);
        }
      })
      .catch(() => {
        // Silently swallow fetch errors in public context
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // 2. Trigger calculation on route change or when popups load
  useEffect(() => {
    if (!popups || popups.length === 0) return;

    // Find candidate popup matching current pathname and unshown in sessionStorage
    const candidate = popups.find((p) => {
      const shownKey = `popup_shown_${p.id}`;
      const alreadyShown = typeof window !== "undefined" && sessionStorage.getItem(shownKey) === "1";
      if (alreadyShown) return false;

      const pages = p.show_on_pages || ["*"];
      return pages.some((pattern) => matchesPath(pattern, pathname || "/"));
    });

    if (!candidate) return;

    let timerId: NodeJS.Timeout | null = null;

    const triggerPopup = (popup: CmsPublicPopup) => {
      setActivePopup(popup);
      if (typeof window !== "undefined") {
        sessionStorage.setItem(`popup_shown_${popup.id}`, "1");
      }
    };

    switch (candidate.trigger_type) {
      case "on_load":
        triggerPopup(candidate);
        break;

      case "time_delay": {
        const delaySeconds = candidate.trigger_value && candidate.trigger_value > 0 ? candidate.trigger_value : 5;
        timerId = setTimeout(() => {
          triggerPopup(candidate);
        }, delaySeconds * 1000);
        break;
      }

      case "scroll_percent": {
        const targetPercent = candidate.trigger_value && candidate.trigger_value > 0 ? candidate.trigger_value : 50;
        const handleScroll = () => {
          const scrollTop = window.scrollY || document.documentElement.scrollTop;
          const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
          if (scrollHeight <= 0) return;
          const currentPercent = (scrollTop / scrollHeight) * 100;
          if (currentPercent >= targetPercent) {
            triggerPopup(candidate);
            window.removeEventListener("scroll", handleScroll);
          }
        };
        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => window.removeEventListener("scroll", handleScroll);
      }

      case "exit_intent": {
        const handleMouseLeave = (e: MouseEvent) => {
          if (e.clientY < 10) {
            triggerPopup(candidate);
            document.removeEventListener("mouseleave", handleMouseLeave);
          }
        };
        document.addEventListener("mouseleave", handleMouseLeave);
        return () => document.removeEventListener("mouseleave", handleMouseLeave);
      }
    }

    return () => {
      if (timerId) clearTimeout(timerId);
    };
  }, [pathname, popups]);

  const handleClose = () => {
    if (activePopup && typeof window !== "undefined") {
      sessionStorage.setItem(`popup_shown_${activePopup.id}`, "1");
    }
    setActivePopup(null);
  };

  if (!activePopup) return null;

  return (
    <AnimatePresence>
      {activePopup && (
        <div className="fixed inset-0 z-[999] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="relative bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl max-w-lg w-full p-6 sm:p-8 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 my-auto"
          >
            {/* Close Button */}
            <button
              onClick={handleClose}
              aria-label="Cerrar popup"
              className="absolute top-4 right-4 p-2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Rich HTML Content */}
            <div
              className="prose dark:prose-invert max-w-none text-sm sm:text-base"
              dangerouslySetInnerHTML={{ __html: sanitizeCmsHtml(activePopup.content_html) }}
            />
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

export default PopupManager;
