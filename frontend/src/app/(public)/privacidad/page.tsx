"use client";

import React from "react";
import { motion } from "framer-motion";
import { useContentBlock } from "@/hooks/useContent";
import RichText from "@/components/public/RichText";
import CmsPageOverride from "@/components/public/cms/CmsPageOverride";

const DEFAULT_SECTIONS = [
  {
    title: "Política de Privacidad",
    body: "En FARO, valoramos tu privacidad y estamos comprometidos con la protección de tus datos personales. Esta política explica cómo recopilamos, usamos y protegemos la información que compartes con nosotros.",
  },
  {
    title: "1. Información que recopilamos",
    body: "Recopilamos información personal (como nombre, correo electrónico y número de teléfono) únicamente cuando nos la proporcionas voluntariamente a través de nuestros formularios de contacto, registro a eventos o suscripción al boletín.",
  },
  {
    title: "2. Uso de la información",
    body: "Utilizamos tu información para enviarte comunicaciones relevantes, gestionar tu participación en actividades de la comunidad y mejorar tu experiencia en nuestra plataforma. No vendemos ni compartimos tus datos con terceros sin tu consentimiento explícito.",
  },
  {
    title: "3. Seguridad",
    body: "Implementamos medidas de seguridad estándar de la industria para proteger tu información contra acceso no autorizado, alteración o destrucción.",
  },
  {
    title: "4. Tus derechos",
    body: "Tienes el derecho de acceder, rectificar o eliminar tus datos personales en cualquier momento. Si deseas ejercer estos derechos, por favor contáctanos en hola@comunidadfaro.org.",
  },
];

export default function PrivacidadPage() {
  const { data: cms } = useContentBlock("faro_privacidad");

  const sections = (() => {
    if (cms?.parsed && typeof cms.parsed === "object" && !Array.isArray(cms.parsed)) {
      const parsed = cms.parsed as Record<string, unknown>;
      if (Array.isArray(parsed.sections)) return parsed.sections as typeof DEFAULT_SECTIONS;
      if (typeof parsed.content === "string") {
        return [{ title: (parsed.title as string) || "Política de Privacidad", body: parsed.content }];
      }
    }
    if (cms?.parsed && Array.isArray(cms.parsed)) return cms.parsed as typeof DEFAULT_SECTIONS;
    return DEFAULT_SECTIONS;
  })();

  return (
    <CmsPageOverride slug="privacidad">
      <main className="pt-[120px] pb-4 px-3 md:px-4 lg:px-8 xl:px-12 bg-faro-surface min-h-screen">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-lg md:text-xl font-bold mb-3 text-faro-on-background">
          {cms?.parsed && typeof cms.parsed === "object" && !Array.isArray(cms.parsed)
            ? (cms.parsed as Record<string, unknown>).title as string || "Política de Privacidad"
            : "Política de Privacidad"}
        </h1>
        <div className="space-y-3 text-faro-on-surface-variant leading-relaxed text-lg">
          {sections.map((section, idx) => (
            <div key={idx}>
              <h2 className="text-lg font-bold text-faro-on-surface mt-3 mb-4">
                {section.title}
              </h2>
              <RichText html={section.body || ""} />
            </div>
          ))}
        </div>
      </motion.div>
    </main>
    </CmsPageOverride>
  );
}
