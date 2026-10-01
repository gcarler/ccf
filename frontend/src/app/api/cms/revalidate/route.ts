import { NextRequest, NextResponse } from "next/server";
import { revalidatePath, revalidateTag } from "next/cache";

const REVALIDATE_SECRET = process.env.CMS_REVALIDATE_SECRET || process.env.INTERNAL_API_SECRET || "ccf-cms-isr-revalidate-secret-token";

export async function POST(req: NextRequest) {
  try {
    const authHeader = req.headers.get("authorization");
    const secretHeader = req.headers.get("x-revalidate-secret");
    const { searchParams } = new URL(req.url);
    const secretQuery = searchParams.get("secret");

    const providedSecret = secretHeader || secretQuery || (authHeader?.startsWith("Bearer ") ? authHeader.substring(7) : null);

    // Permitir si coincide el secret o si no hay secret configurado en entorno de desarrollo
    if (providedSecret !== REVALIDATE_SECRET && process.env.NODE_ENV === "production" && process.env.CMS_REVALIDATE_SECRET) {
      return NextResponse.json(
        { success: false, message: "Token de revalidación inválido o no autorizado" },
        { status: 401 }
      );
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
