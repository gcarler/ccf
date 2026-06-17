"use client";

import ErrorBoundary from "@/components/ErrorBoundary";
import { SITE_NAME } from "@/lib/site-config";

export default function GlobalError() {
  return <ErrorBoundary moduleName={SITE_NAME} />;
}
