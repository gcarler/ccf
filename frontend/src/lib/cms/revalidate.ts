/**
 * Helper para invocar la revalidación bajo demanda ISR del CMS.
 */

export interface RevalidateOptions {
  path?: string;
  tag?: string;
  type?: "page" | "layout";
}

export async function triggerCmsRevalidation(options: RevalidateOptions): Promise<{ success: boolean; message?: string }> {
  try {
    const res = await fetch("/api/cms/revalidate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(options),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      return {
        success: false,
        message: errData.message || `Error HTTP ${res.status} al revalidar`,
      };
    }

    const data = await res.json();
    return { success: true, message: data.message };
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : "Error al revalidar ruta CMS",
    };
  }
}
