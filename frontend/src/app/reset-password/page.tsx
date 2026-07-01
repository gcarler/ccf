"use client";

import React, { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Loader2, Lock, Eye, EyeOff, CheckCircle2 } from "lucide-react";
import { apiFetch } from "@/lib/http";

function ResetPasswordContent() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params?.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!token) {
    return (
      <div className="flex w-screen min-h-screen font-sans bg-[#001B48]">
        <div className="w-full flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center max-w-md mx-auto px-4"
          >
            <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-3">
              <Lock className="w-8 h-8 text-white/60" />
            </div>
            <h2 className="text-lg font-extrabold text-white tracking-[-0.02em] mb-3">
              Token inválido
            </h2>
            <p className="text-white/60 text-sm mb-3">
              El enlace no es válido o ya fue utilizado. Solicita uno nuevo.
            </p>
            <button
              onClick={() => router.push("/auth/forgot")}
              className="px-4 py-1.5 bg-[#018ABD] text-white rounded-lg font-bold text-[11px] uppercase tracking-wide border-none cursor-pointer hover:bg-[#004581] transition-all"
            >
              Solicitar nuevo enlace
            </button>
          </motion.div>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }
    if (password.length < 6) {
      setError("La contraseña debe tener al menos 6 caracteres");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await apiFetch<void>("/v3/auth/reset-password", {
        method: "POST",
        query: { token, new_password: password },
        silent: true,
      });
      setSuccess(true);
      setTimeout(() => router.push("/login"), 2500);
    } catch (err: any) {
      setError(err?.message || "No pudimos actualizar tu contraseña.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="flex w-screen min-h-screen font-sans">
        <motion.section
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex-1 bg-[hsl(var(--bg-primary))] flex flex-col justify-center items-center px-4 min-h-screen"
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
            className="w-20 h-20 rounded-full bg-emerald-50 flex items-center justify-center mb-3"
          >
            <CheckCircle2 className="w-10 h-10 text-emerald-500" />
          </motion.div>
          <h2 className="text-lg font-extrabold text-[#001B48] tracking-[-0.02em] mb-3">
            Contraseña actualizada
          </h2>
          <p className="text-[hsl(var(--text-primary))] text-sm">Redirigiendo al inicio de sesión...</p>
        </motion.section>
      </div>
    );
  }

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
          style={{ background: "radial-gradient(circle at 70% 30%, rgba(1,138,189,0.25) 0%, transparent 60%)" }}
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
          viewBox="0 0 1440 320" preserveAspectRatio="none"
        >
          <path fill="rgba(255,255,255,0.03)" d="M0,224L48,213.3C96,203,192,181,288,181.3C384,181,480,203,576,218.7C672,235,768,245,864,240C960,235,1056,213,1152,197.3C1248,181,1344,171,1392,165.3L1440,160L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"/>
          <path fill="rgba(255,255,255,0.06)" d="M0,128L48,144C96,160,192,192,288,197.3C384,203,480,181,576,160C672,139,768,117,864,128C960,139,1056,181,1152,186.7C1248,192,1344,160,1392,144L1440,128L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"/>
        </svg>
      </motion.section>

      {/* ── RIGHT PANEL: FORM ── */}
      <motion.section
        initial={{ opacity: 0, x: 30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="flex-1 bg-[hsl(var(--bg-primary))] flex flex-col justify-center px-[clamp(40px,8%,90px)] py-[clamp(40px,8%,90px)] min-h-screen"
      >
        <div className="w-full max-w-[420px] mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mb-4"
          >
            <h2 className="text-[clamp(1.8rem,3.5vw,2.5rem)] font-extrabold text-[#001B48] tracking-[-0.02em] leading-none m-0 mb-4">
              Restablecer contraseña
            </h2>
            <p className="text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide text-[10px] m-0">
              Crea una nueva clave segura
            </p>
          </motion.div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            {/* Nueva contraseña */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.45 }}
            >
              <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wider block mb-3 ml-2">
                Nueva contraseña
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-[hsl(var(--bg-muted))] border-2 border-[hsl(var(--border))] rounded-lg py-1.5 px-3 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:border-[#018ABD] focus:bg-[hsl(var(--bg-primary))] transition-all pr-14"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] bg-transparent border-none cursor-pointer p-0 flex"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </motion.div>

            {/* Confirmar contraseña */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.55 }}
            >
              <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wider block mb-3 ml-2">
                Confirmar contraseña
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={6}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-[hsl(var(--bg-muted))] border-2 border-[hsl(var(--border))] rounded-lg py-1.5 px-3 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:border-[#018ABD] focus:bg-[hsl(var(--bg-primary))] transition-all pr-14"
                />
              </div>
            </motion.div>

            {/* Error */}
            {error && (
              <motion.div
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                className="px-3 py-1.5 bg-rose-50 border-2 border-rose-200 rounded-lg text-rose-600 text-[11px] font-bold text-center uppercase tracking-wider"
              >
                {error}
              </motion.div>
            )}

            {/* Submit */}
            <motion.button
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.65 }}
              type="submit"
              disabled={loading}
              className="w-full py-1.5 bg-[#018ABD] text-white rounded-lg font-bold text-[11px] uppercase tracking-wide border-none cursor-pointer hover:bg-[#004581] transition-all mt-2 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-3"
            >
              {loading ? (
                <Loader2 className="animate-spin" size={20} />
              ) : (
                <>
                  Actualizar contraseña
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                </>
              )}
            </motion.button>
          </form>
        </div>
      </motion.section>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="flex w-screen min-h-screen items-center justify-center bg-[#001B48]">
          <Loader2 className="w-8 h-8 animate-spin text-white" />
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
