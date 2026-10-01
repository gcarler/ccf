"use client";

import React, { useState, useEffect, useCallback } from "react";
import SidePanel from "@/components/ui/SidePanel";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import {
  ShieldCheck,
  ShieldAlert,
  Copy,
  Check,
  KeyRound,
  QrCode,
  AlertTriangle,
  Lock,
  Unlock,
  RefreshCw,
} from "lucide-react";

interface TwoFactorDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onStatusChange?: (isEnabled: boolean) => void;
}

interface TwoFactorStatus {
  is_mfa_enabled: boolean;
  has_secret: boolean;
  backup_codes_count: number;
}

interface SetupData {
  secret: string;
  otpauth_uri: string;
  is_mfa_enabled: boolean;
  backup_codes: string[];
}

export default function TwoFactorDrawer({
  isOpen,
  onClose,
  onStatusChange,
}: TwoFactorDrawerProps) {
  const [status, setStatus] = useState<TwoFactorStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [setupData, setSetupData] = useState<SetupData | null>(null);
  const [code, setCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedBackups, setCopiedBackups] = useState(false);
  const [confirmedBackups, setConfirmedBackups] = useState<string[]>([]);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiFetch<TwoFactorStatus>("/v3/auth/2fa/status");
      setStatus(res);
      onStatusChange?.(res.is_mfa_enabled);
    } catch {
      toast.error("Error al consultar estado de 2FA");
    } finally {
      setLoading(false);
    }
  }, [onStatusChange]);

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
      setSetupData(null);
      setCode("");
      setDisableCode("");
      setConfirmedBackups([]);
    }
  }, [isOpen, fetchStatus]);

  const handleStartSetup = async () => {
    try {
      setActionLoading(true);
      const res = await apiFetch<SetupData>("/v3/auth/2fa/setup", {
        method: "POST",
      });
      setSetupData(res);
      setCode("");
    } catch {
      toast.error("No se pudo iniciar la configuración 2FA");
    } finally {
      setActionLoading(false);
    }
  };

  const handleVerifySetup = async () => {
    if (!code || code.trim().length !== 6) {
      toast.error("Ingresa el código de 6 dígitos");
      return;
    }

    try {
      setActionLoading(true);
      const res = await apiFetch<{
        verified: boolean;
        is_mfa_enabled: boolean;
        backup_codes: string[];
      }>("/v3/auth/2fa/verify", {
        method: "POST",
        body: { code: code.trim() },
      });

      if (res.verified) {
        toast.success("Autenticación de dos factores activada con éxito");
        setConfirmedBackups(res.backup_codes || setupData?.backup_codes || []);
        setStatus({
          is_mfa_enabled: true,
          has_secret: true,
          backup_codes_count: (res.backup_codes || []).length,
        });
        onStatusChange?.(true);
      }
    } catch {
      toast.error("Código incorrecto o expirado");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDisable2FA = async () => {
    if (!disableCode || disableCode.trim().length < 6) {
      toast.error("Ingresa tu código TOTP o código de respaldo");
      return;
    }

    try {
      setActionLoading(true);
      await apiFetch<{ status: string; message: string }>("/v3/auth/2fa/disable", {
        method: "POST",
        body: { code: disableCode.trim() },
      });

      toast.success("2FA desactivado correctamente");
      setStatus({
        is_mfa_enabled: false,
        has_secret: false,
        backup_codes_count: 0,
      });
      setSetupData(null);
      setDisableCode("");
      setConfirmedBackups([]);
      onStatusChange?.(false);
    } catch {
      toast.error("Código de seguridad incorrecto");
    } finally {
      setActionLoading(false);
    }
  };

  const copyToClipboard = (text: string, type: "secret" | "backups") => {
    navigator.clipboard.writeText(text);
    if (type === "secret") {
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
      toast.success("Clave secreta copiada");
    } else {
      setCopiedBackups(true);
      setTimeout(() => setCopiedBackups(false), 2000);
      toast.success("Códigos de respaldo copiados");
    }
  };

  return (
    <SidePanel
      isOpen={isOpen}
      onClose={onClose}
      title="Autenticación de Dos Factores (2FA)"
      subtitle="Protección criptográfica RFC 6238 con TOTP y códigos de respaldo"
      width="w-full sm:w-[500px]"
    >
      <div className="space-y-6 text-sm text-[hsl(var(--text-primary))] pb-10">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <RefreshCw className="size-8 animate-spin text-[hsl(var(--primary))]" />
            <p className="text-[hsl(var(--text-secondary))] font-medium text-xs">
              Verificando estado de seguridad...
            </p>
          </div>
        ) : status?.is_mfa_enabled && confirmedBackups.length === 0 ? (
          /* Estado: Activo */
          <div className="space-y-6">
            <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-start gap-4 shadow-sm">
              <div className="p-2.5 rounded-lg bg-[hsl(var(--primary))/0.15] text-[hsl(var(--primary))] shrink-0">
                <ShieldCheck className="size-6" />
              </div>
              <div className="space-y-1">
                <h4 className="font-bold text-base text-[hsl(var(--text-primary))]">
                  2FA Activo y Protegido
                </h4>
                <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
                  Tu cuenta solicita una clave temporal de 6 dígitos generada por tu app autenticadora en cada inicio de sesión y cambio de contraseña.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] space-y-4">
              <div className="flex items-center gap-3">
                <KeyRound className="size-5 text-[hsl(var(--text-secondary))]" />
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                    Códigos de Respaldo
                  </p>
                  <p className="text-sm font-semibold">
                    {status.backup_codes_count} disponibles
                  </p>
                </div>
              </div>
            </div>

            {/* Desactivar 2FA */}
            <div className="p-4 rounded-xl bg-[hsl(var(--destructive)/0.08)] border border-[hsl(var(--destructive)/0.25)] space-y-3">
              <div className="flex items-center gap-2 text-[hsl(var(--destructive))]">
                <Lock className="size-4 shrink-0" />
                <h5 className="font-bold text-xs uppercase tracking-wider">
                  Zona de Desactivación
                </h5>
              </div>
              <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
                Para desactivar 2FA, ingresa tu código TOTP actual de 6 dígitos o un código de respaldo.
              </p>
              <div className="space-y-2 pt-1">
                <input
                  type="text"
                  maxLength={10}
                  placeholder="000000 o código de respaldo"
                  value={disableCode}
                  onChange={(e) => setDisableCode(e.target.value.trim())}
                  className="w-full bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg px-3 py-2 text-center text-base tracking-widest font-mono font-bold text-[hsl(var(--text-primary))] focus:ring-2 focus:ring-[hsl(var(--destructive))] outline-none"
                />
                <button
                  type="button"
                  onClick={handleDisable2FA}
                  disabled={actionLoading || !disableCode}
                  className="w-full py-2.5 px-4 rounded-lg bg-[hsl(var(--destructive))] text-white font-bold text-xs uppercase tracking-wider shadow hover:opacity-90 active:scale-[0.99] disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                >
                  <Unlock className="size-4" />
                  {actionLoading ? "Desactivando..." : "Desactivar Protección 2FA"}
                </button>
              </div>
            </div>
          </div>
        ) : confirmedBackups.length > 0 ? (
          /* Estado: Códigos de Respaldo Generados */
          <div className="space-y-6">
            <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-start gap-4">
              <div className="p-2.5 rounded-lg bg-[hsl(var(--primary))/0.15] text-[hsl(var(--primary))] shrink-0">
                <ShieldCheck className="size-6" />
              </div>
              <div className="space-y-1">
                <h4 className="font-bold text-base text-[hsl(var(--text-primary))]">
                  ¡2FA Activado Exitosamente!
                </h4>
                <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
                  Guarda estos códigos de respaldo en un lugar seguro. Cada uno solo puede utilizarse una vez si pierdes acceso a tu dispositivo autenticador.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                  Códigos de Emergencia Única
                </span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(confirmedBackups.join("\n"), "backups")}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] text-xs font-semibold text-[hsl(var(--text-primary))] transition-colors"
                >
                  {copiedBackups ? (
                    <>
                      <Check className="size-3.5 text-green-500" />
                      Copiados
                    </>
                  ) : (
                    <>
                      <Copy className="size-3.5 text-[hsl(var(--text-secondary))]" />
                      Copiar todos
                    </>
                  )}
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 font-mono text-center text-xs font-bold py-2">
                {confirmedBackups.map((bc, idx) => (
                  <div
                    key={idx}
                    className="p-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] select-all"
                  >
                    {bc}
                  </div>
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="w-full py-2.5 px-4 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] font-bold text-xs uppercase tracking-wider shadow hover:opacity-90 active:scale-[0.99] transition-all"
            >
              Entendido y Guardado
            </button>
          </div>
        ) : setupData ? (
          /* Estado: Configurando Secreto y Código */
          <div className="space-y-6">
            <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] space-y-3">
              <div className="flex items-center gap-2 text-[hsl(var(--primary))]">
                <QrCode className="size-5 shrink-0" />
                <h4 className="font-bold text-sm">
                  1. Vincula tu Aplicación Autenticadora
                </h4>
              </div>
              <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
                Abre Google Authenticator, 1Password, Authy o Microsoft Authenticator y selecciona "Ingresar clave manualmente".
              </p>

              <div className="space-y-1 pt-1">
                <label className="text-2xs uppercase tracking-wider font-bold text-[hsl(var(--text-secondary))]">
                  Clave Secreta Base32
                </label>
                <div className="flex items-center gap-2 bg-[hsl(var(--surface-1))] p-2.5 rounded-lg border border-[hsl(var(--border))]">
                  <span className="font-mono text-xs font-bold select-all tracking-wider break-all flex-1 text-[hsl(var(--text-primary))]">
                    {setupData.secret}
                  </span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(setupData.secret, "secret")}
                    className="p-1.5 rounded hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors shrink-0"
                    title="Copiar Clave"
                  >
                    {copiedSecret ? (
                      <Check className="size-4 text-green-500" />
                    ) : (
                      <Copy className="size-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] space-y-3">
              <h4 className="font-bold text-sm text-[hsl(var(--text-primary))]">
                2. Ingresa el Código de Verificación
              </h4>
              <p className="text-xs text-[hsl(var(--text-secondary))]">
                Ingresa el código temporal de 6 dígitos que muestra tu app:
              </p>
              <div className="space-y-3 pt-1">
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  placeholder="123456"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg px-3 py-2.5 text-center text-xl tracking-widest font-mono font-bold text-[hsl(var(--text-primary))] focus:ring-2 focus:ring-[hsl(var(--primary))] outline-none"
                />
                <button
                  type="button"
                  onClick={handleVerifySetup}
                  disabled={actionLoading || code.length !== 6}
                  className="w-full py-2.5 px-4 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] font-bold text-xs uppercase tracking-wider shadow hover:opacity-90 active:scale-[0.99] disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                >
                  <ShieldCheck className="size-4" />
                  {actionLoading ? "Verificando..." : "Verificar y Activar 2FA"}
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Estado: No configurado */
          <div className="space-y-6">
            <div className="p-5 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-start gap-4">
              <div className="p-3 rounded-xl bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] shrink-0">
                <ShieldAlert className="size-7" />
              </div>
              <div className="space-y-1.5">
                <h4 className="font-bold text-base text-[hsl(var(--text-primary))]">
                  2FA No Activado
                </h4>
                <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
                  Protege tu cuenta ministerial contra accesos no autorizados. Requiere un segundo factor criptográfico en cada inicio de sesión.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] space-y-3">
              <div className="flex items-center gap-2 text-[hsl(var(--text-primary))] font-semibold text-xs uppercase tracking-wider">
                <AlertTriangle className="size-4 text-[hsl(var(--primary))]" />
                ¿Qué necesitas?
              </div>
              <ul className="text-xs text-[hsl(var(--text-secondary))] space-y-2 list-disc list-inside leading-relaxed">
                <li>Una app de autenticación (Google Authenticator, Authy, Apple Passwords).</li>
                <li>Un minuto para vincular el código secreto.</li>
              </ul>
            </div>

            <button
              type="button"
              onClick={handleStartSetup}
              disabled={actionLoading}
              className="w-full py-3 px-4 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] font-bold text-xs uppercase tracking-wider shadow-md hover:opacity-90 active:scale-[0.99] disabled:opacity-50 transition-all flex items-center justify-center gap-2"
            >
              <KeyRound className="size-4" />
              {actionLoading ? "Generando..." : "Configurar 2FA Ahora"}
            </button>
          </div>
        )}
      </div>
    </SidePanel>
  );
}
