"use client";

import { CmsSection } from "@/types/cms-v2";
import type { FaqProps } from "@/types/cms-section-props";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { asItems, asProps, val } from "./shared";

export function FaqSection({ section }: { section: CmsSection<"faq"> }) {
  const props: FaqProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const items = asItems(p).slice(0, 12) as Array<{ q?: string; a?: string }>;
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-6" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      <div className="space-y-2">
        {items.map((item, i) => {
          const isOpen = openIndex === i;
          return (
            <div key={i} className="rounded-xl overflow-hidden" style={{ background: "var(--site-surface-container)" }}>
              <button
                onClick={() => setOpenIndex(isOpen ? null : i)}
                className="w-full flex items-center justify-between gap-4 p-5 text-left"
              >
                <span className="font-bold text-base" style={{ color: "var(--site-on-surface)" }}>
                  {item.q || `Pregunta ${i + 1}`}
                </span>
                {isOpen ? (
                  <ChevronUp size={18} style={{ color: "var(--site-primary)", flexShrink: 0 }} />
                ) : (
                  <ChevronDown size={18} style={{ color: "var(--site-on-surface-variant)", flexShrink: 0 }} />
                )}
              </button>
              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <p className="px-5 pb-5 text-sm leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
                      {item.a || "Respuesta pendiente"}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </section>
  );
}
