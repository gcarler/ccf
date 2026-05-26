'use client';

// Removed fetch-patch import — it was patching globalThis.fetch which
// could interfere with Next.js internal fetch calls and cause the
// platform to hang on "Verificando Credenciales...".
// apiFetch already has its own token injection logic, so the patch is redundant.
import { WebVitalsReporter } from './(analytics)/WebVitalsReporter';

export function ClientBootstrap() {
  return <WebVitalsReporter />;
}
