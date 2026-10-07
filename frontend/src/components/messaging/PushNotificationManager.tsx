"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import {
  Bell,
  BellRing,
  BellOff,
  Send,
  Check,
  Smartphone,
  Laptop,
  AlertCircle,
} from "lucide-react";
import clsx from "clsx";

interface PushSubscriptionItem {
  id: string;
  auth_user_id?: string;
  endpoint: string;
  device_name: string;
  created_at: string;
}

interface PushSubscriptionsResponse {
  subscriptions: PushSubscriptionItem[];
  count: number;
}

interface VapidKeyResponse {
  public_key: string;
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export default function PushNotificationManager() {
  const [isSupported, setIsSupported] = useState<boolean>(true);
  const [permission, setPermission] = useState<NotificationPermission>("default");
  const [subscriptions, setSubscriptions] = useState<PushSubscriptionItem[]>([]);
  const [_loading, setLoading] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  const checkSupportAndPermission = useCallback(() => {
    if (
      typeof window === "undefined" ||
      !("serviceWorker" in navigator) ||
      !("Notification" in window) ||
      !("PushManager" in window)
    ) {
      setIsSupported(false);
      return;
    }
    setIsSupported(true);
    setPermission(Notification.permission);
  }, []);

  const fetchSubscriptions = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiFetch<PushSubscriptionsResponse>(
        "/messaging/push/subscriptions"
      );
      setSubscriptions(res?.subscriptions || []);
    } catch {
      // Endpoint may require auth or network
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkSupportAndPermission();
    fetchSubscriptions();
  }, [checkSupportAndPermission, fetchSubscriptions]);

  const handleEnablePush = async () => {
    if (!isSupported) {
      toast.error("Tu navegador no soporta notificaciones push");
      return;
    }

    try {
      setActionLoading(true);
      const perm = await Notification.requestPermission();
      setPermission(perm);

      if (perm !== "granted") {
        toast.error("Permiso denegado por el navegador");
        return;
      }

      // Register service worker
      const reg = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;

      // Fetch VAPID public key
      const { public_key } = await apiFetch<VapidKeyResponse>(
        "/messaging/push/vapid-public-key"
      );

      const convertedKey = urlBase64ToUint8Array(public_key);
      const subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: convertedKey as unknown as BufferSource,
      });

      const subJson = subscription.toJSON();
      if (!subJson.endpoint || !subJson.keys?.p256dh || !subJson.keys?.auth) {
        throw new Error("No se pudo obtener las claves criptográficas de la suscripción");
      }

      // Determine friendly device name
      const ua = navigator.userAgent;
      const deviceName = /mobile/i.test(ua)
        ? "Dispositivo Móvil"
        : /mac/i.test(ua)
        ? "Mac OS Desktop"
        : /linux/i.test(ua)
        ? "Linux Desktop"
        : "Navegador Web";

      await apiFetch("/messaging/push/subscribe", {
        method: "POST",
        body: {
          endpoint: subJson.endpoint,
          keys: {
            p256dh: subJson.keys.p256dh,
            auth: subJson.keys.auth,
          },
          device_name: deviceName,
        },
      });

      toast.success("Notificaciones push activadas correctamente");
      await fetchSubscriptions();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al activar notificaciones";
      toast.error(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDisablePush = async (endpoint: string) => {
    try {
      setActionLoading(true);

      // Unsubscribe in browser if matching current registration
      if ("serviceWorker" in navigator) {
        const reg = await navigator.serviceWorker.getRegistration();
        const currentSub = await reg?.pushManager.getSubscription();
        if (currentSub && currentSub.endpoint === endpoint) {
          await currentSub.unsubscribe();
        }
      }

      await apiFetch("/messaging/push/unsubscribe", {
        method: "POST",
        body: { endpoint },
      });

      toast.success("Suscripción eliminada");
      await fetchSubscriptions();
    } catch {
      toast.error("Error al desactivar suscripción");
    } finally {
      setActionLoading(false);
    }
  };

  const handleTestPush = async () => {
    try {
      setActionLoading(true);
      const res = await apiFetch<{ status: string; sent_count: number }>(
        "/messaging/push/test",
        {
          method: "POST",
          body: {
            title: "Alerta Ministerial CCF",
            body: "Tu navegador está recibiendo notificaciones Web Push VAPID en tiempo real.",
            url: "/plataforma/messages",
          },
        }
      );

      toast.success(
        `Notificación emitida a ${res.sent_count || 1} dispositivo(s)`
      );
    } catch {
      toast.error("Error al emitir notificación de prueba");
    } finally {
      setActionLoading(false);
    }
  };

  if (!isSupported) {
    return (
      <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-xs text-[hsl(var(--text-secondary))] flex items-center gap-3">
        <AlertCircle className="size-5 text-[hsl(var(--destructive))] shrink-0" />
        <p>Las notificaciones Push no son compatibles con este navegador.</p>
      </div>
    );
  }

  const isGranted = permission === "granted" && subscriptions.length > 0;

  return (
    <div className="space-y-4">
      {/* Status Banner */}
      <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div
            className={clsx(
              "p-2.5 rounded-lg shrink-0",
              isGranted
                ? "bg-[hsl(var(--primary))/0.15] text-[hsl(var(--primary))]"
                : "bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))]"
            )}
          >
            {isGranted ? <BellRing className="size-6" /> : <BellOff className="size-6" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-bold text-sm text-[hsl(var(--text-primary))]">
                Notificaciones Web Push (VAPID)
              </h4>
              <span
                className={clsx(
                  "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-2xs font-bold uppercase tracking-wider",
                  isGranted
                    ? "bg-[hsl(var(--primary))/0.15] text-[hsl(var(--primary))]"
                    : "bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))]"
                )}
              >
                {isGranted ? (
                  <>
                    <Check className="size-3" />
                    Activas
                  </>
                ) : permission === "denied" ? (
                  "Bloqueadas"
                ) : (
                  "Inactivas"
                )}
              </span>
            </div>
            <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
              {isGranted
                ? `Recibes avisos pastorales y menciones en ${subscriptions.length} dispositivo(s).`
                : permission === "denied"
                ? "El navegador tiene bloqueado el permiso. Habilítalo en la barra de direcciones."
                : "Activa notificaciones instantáneas de mensajes y tareas en este navegador."}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {isGranted ? (
            <button
              type="button"
              onClick={handleTestPush}
              disabled={actionLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-3))] text-xs font-bold uppercase tracking-wider shadow-sm transition-all disabled:opacity-50"
            >
              <Send className="size-3.5" />
              Probar
            </button>
          ) : (
            <button
              type="button"
              onClick={handleEnablePush}
              disabled={actionLoading || permission === "denied"}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 active:scale-95 text-xs font-bold uppercase tracking-wider shadow-sm transition-all disabled:opacity-50"
            >
              <Bell className="size-3.5" />
              {actionLoading ? "Activando..." : "Activar Ahora"}
            </button>
          )}
        </div>
      </div>

      {/* Dispositivos Registrados */}
      {subscriptions.length > 0 && (
        <div className="space-y-2">
          <p className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] ml-1">
            Dispositivos Registrados ({subscriptions.length})
          </p>
          <div className="divide-y divide-[hsl(var(--border))] rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] overflow-hidden">
            {subscriptions.map((sub) => (
              <div
                key={sub.id || sub.endpoint}
                className="p-3 flex items-center justify-between gap-3 text-xs"
              >
                <div className="flex items-center gap-3">
                  <div className="p-1.5 rounded bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]">
                    {/móvil|mobile/i.test(sub.device_name) ? (
                      <Smartphone className="size-4" />
                    ) : (
                      <Laptop className="size-4" />
                    )}
                  </div>
                  <div>
                    <p className="font-semibold text-[hsl(var(--text-primary))]">
                      {sub.device_name}
                    </p>
                    <p className="text-2xs text-[hsl(var(--text-secondary))] font-mono truncate max-w-[240px] sm:max-w-md">
                      {sub.endpoint}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleDisablePush(sub.endpoint)}
                  disabled={actionLoading}
                  className="text-2xs font-semibold text-[hsl(var(--destructive))] hover:underline px-2 py-1 shrink-0"
                >
                  Eliminar
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
