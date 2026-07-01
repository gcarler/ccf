"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import { apiFetch } from "@/lib/http";

function VerifyEmailContent() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params?.get("token");

  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Confirmando tu correo…");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Token inválido o faltante. Revisa el enlace del correo.");
      return;
    }

    apiFetch<void>(`/v3/auth/verify-email`, {
      query: { token },
      silent: true,
    })
      .then(() => {
        setStatus("success");
        setMessage("¡Tu correo fue verificado correctamente!");
      })
      .catch((err: any) => {
        setStatus("error");
        setMessage(err?.message || "No pudimos verificar tu correo. El enlace podría haber expirado.");
      });
  }, [token]);

  return (
    <div className="flex w-screen min-h-screen font-sans">
      {/* ── LEFT PANEL: BRANDING ── */}
      <motion.section
        initial={{ opacity: 0, x: -30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="flex-[1.2] bg-[#001B48] relative flex flex-col justify-between px-[clamp(40px,8%,90px)] py-[clamp(40px,8%,90px)] min-h-screen overflow-hidden"
      >
        <div
          className="absolute top-[-20%] right-[-20%] w-[140%] h-[140%] pointer-events-none z-0"
          style={{
            background:
              "radial-gradient(circle at 70% 30%, rgba(1,138,189,0.25) 0%, transparent 60%)",
          }}
        />

        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="relative z-10"
        >
          <div className="inline-flex items-center gap-3 border border-white/20 rounded-full px-3 py-2.5 bg-white/5 backdrop-blur-md">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round"/>
              <circle cx="12" cy="4" r="1.5" fill="white" stroke="none"/>
            </svg>
            <span className="text-white font-bold uppercase tracking-wide text-[10px]">
              Ministerio Internacional
            </span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.8 }}
          className="relative z-10"
        >
          <h1 className="font-bold tracking-[-0.04em] leading-[0.88] text-white text-[clamp(3rem,6vw,4.5rem)] m-0">
            EL <br /> FARO
          </h1>
          <p className="text-[#018ABD] text-[clamp(1rem,2vw,1.25rem)] font-bold tracking-wide uppercase mt-3 leading-[1.4]">
            Comunidad <br /> Cristiana
          </p>
          <div className="w-16 h-1.5 bg-[hsl(var(--bg-primary))] mt-3 rounded-full" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="relative z-10"
        >
          <p className="text-white/90 text-lg font-medium tracking-normal leading-relaxed">
            Guiando a las naciones <br /> hacia la luz de la verdad.
          </p>
        </motion.div>

        <svg
          className="absolute bottom-0 left-0 w-full z-0 pointer-events-none"
          viewBox="0 0 1440 320"
          preserveAspectRatio="none"
        >
          <path fill="rgba(255,255,255,0.03)" d="M0,224L48,213.3C96,203,192,181,288,181.3C384,181,480,203,576,218.7C672,235,768,245,864,240C960,235,1056,213,1152,197.3C1248,181,1344,171,1392,165.3L1440,160L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"/>
          <path fill="rgba(255,255,255,0.06)" d="M0,128L48,144C96,160,192,192,288,197.3C384,203,480,181,576,160C672,139,768,117,864,128C960,139,1056,181,1152,186.7C1248,192,1344,160,1392,144L1440,128L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"/>
        </svg>
      </motion.section>

      {/* ── RIGHT PANEL: RESULT ── */}
      <motion.section
        initial={{ opacity: 0, x: 30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="flex-1 bg-[hsl(var(--bg-primary))] flex flex-col justify-center px-[clamp(40px,8%,90px)] py-[clamp(40px,8%,90px)] min-h-screen"
      >
        <div className="w-full max-w-[420px] mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3, type: "spring", stiffness: 200 }}
            className="mb-3 flex justify-center"
          >
            {status === "loading" && (
              <div className="w-20 h-20 rounded-full bg-[hsl(var(--bg-muted))] flex items-center justify-center">
                <Loader2 className="w-10 h-10 animate-spin text-[#018ABD]" />
              </div>
            )}
            {status === "success" && (
              <div className="w-20 h-20 rounded-full bg-emerald-50 flex items-center justify-center">
                <CheckCircle2 className="w-10 h-10 text-emerald-500" />
              </div>
            )}
            {status === "error" && (
              <div className="w-20 h-20 rounded-full bg-rose-50 flex items-center justify-center">
                <XCircle className="w-10 h-10 text-rose-500" />
              </div>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <h2 className="text-[clamp(1.5rem,3vw,2rem)] font-extrabold text-[#001B48] tracking-[-0.02em] leading-none m-0 mb-4">
              {status === "loading" && "Verificando..."}
              {status === "success" && "¡Correo verificado!"}
              {status === "error" && "No pudimos verificar"}
            </h2>
            <p className="text-[hsl(var(--text-primary))] text-sm font-medium leading-relaxed mb-3">
              {message}
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
            className="space-y-3"
          >
            {status !== "loading" && (
              <>
                <button
                  onClick={() => router.push("/login")}
                  className="w-full py-1.5 bg-[#018ABD] text-white rounded-lg font-bold text-[11px] uppercase tracking-wide border-none cursor-pointer hover:bg-[#004581] transition-all"
                >
                  {status === "success" ? "Ir al inicio de sesión →" : "Volver al inicio"}
                </button>

                <div className="relative my-4">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t-2 border-[hsl(var(--border))]" />
                  </div>
                  <div className="relative flex justify-center">
                    <span className="bg-[hsl(var(--bg-primary))] px-4 text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      Salmos 133:1
                    </span>
                  </div>
                </div>

                <p className="text-[hsl(var(--text-secondary))] italic text-sm leading-relaxed">
                  &ldquo;Mirad cu&aacute;n bueno y cu&aacute;n delicioso es<br />
                  habitar los hermanos juntos en armon&iacute;a.&rdquo;
                </p>
              </>
            )}
          </motion.div>
        </div>
      </motion.section>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="flex w-screen min-h-screen items-center justify-center bg-[#001B48]">
        <Loader2 className="w-8 h-8 animate-spin text-white" />
      </div>
    }>
      <VerifyEmailContent />
    </Suspense>
  );
}
