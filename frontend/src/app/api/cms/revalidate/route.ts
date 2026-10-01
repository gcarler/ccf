import { NextRequest, NextResponse } from "next/server";
import { revalidatePath, revalidateTag } from "next/cache";

const REVALIDATE_SECRET = process.env.CMS_REVALIDATE_SECRET || process.env.INTERNAL_API_SECRET || "ccf-cms-isr-revalidate-secret-token";
const API_BASE = (process.env.API_BASE_URL || process.env.E2E_API_URL || "http://127.0.0.1:8000/api").replace(/\/$/, "");

export async function POST(req: NextRequest) {
  try {
    const authHeader = req.headers.get("authorization");
    const secretHeader = req.headers.get("x-revalidate-secret");
    const { searchParams } = new URL(req.url);
    const secretQuery = searchParams.get("secret");

    const providedSecret = secretHeader || secretQuery || (authHeader?.startsWith("Bearer ") ? authHeader.substring(7) : null);

    // Autorización: secret de servicio (backend/CI) o sesión de plataforma
    // válida verificada contra el backend (GET /v3/auth/sessions). En
    // producción el acceso anónimo queda denegado (401).
    const secretMatch = providedSecret !== null && providedSecret === REVALIDATE_SECRET;
    if (!secretMatch) {
      let authenticated = false;
      if (authHeader) {
        try {
          const probe = await fetch(`${API_BASE}/v3/auth/sessions`, {
            headers: { authorization: authHeader, accept: "application/json" },
            cache: "no-store",
          });
          authenticated = probe.ok;
        } catch {
          authenticated = false;
        }
      }
      if (!authenticated) {
        return NextResponse.json(
          { success: false, message: "Token de revalidación inválido o no autorizado" },
          { status: 401 }
        );
      }
    }

    const body = await req.json().catch(() => ({}));
    const path = body.path || searchParams.get("path");
    const tag = body.tag || searchParams.get("tag");
    const type = body.type as "page" | "layout" | undefined;

    if (!path && !tag) {
      return NextResponse.json(
        { success: false, message: "Debe especificar un 'path' o 'tag' a revalidar" },
        { status: 400 }
      );
    }

    if (path) {
      if (type) {
        revalidatePath(path, type);
      } else {
        revalidatePath(path);
      }
    }

    if (tag) {
      revalidateTag(tag);
    }

    // Fallback canónico: la portada pública se revalida junto con el objetivo
    // para que la tarjeta OpenGraph por defecto quede fresca al compartir.
    revalidatePath("/");

    return NextResponse.json({
      success: true,
      revalidated: true,
      path: path || null,
      tag: tag || null,
      timestamp: new Date().toISOString(),
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Error interno al revalidar";
    return NextResponse.json(
      { success: false, message },
      { status: 500 }
    );
  }
}
