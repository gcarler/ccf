'use client';

import '@/lib/fetch-patch';
import { WebVitalsReporter } from './(analytics)/WebVitalsReporter';

export function ClientBootstrap() {
  return <WebVitalsReporter />;
}

