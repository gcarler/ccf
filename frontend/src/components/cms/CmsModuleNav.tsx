"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import clsx from "clsx";
import {
  ChevronRight,
  FileText,
  Globe,
  ImageIcon,
  Layers3,
  LayoutDashboard,
  Link2,
  MessageCircle,
  Palette,
  PanelsTopLeft,
  PackageOpen,
  Shield,
  Bell,
  Webhook,
  Puzzle,
  Search,
  FolderTree,
  RotateCcw,
  AlertTriangle,
  Gauge,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { canEditCms, canManageSites } from "@/lib/cms/permissions";
import { apiFetch } from "@/lib/http";

const CMS_TABS = [
  { id: "resumen", label: "Resumen", href: "/plataforma/cms", icon: LayoutDashboard },
  { id: "paginas", label: "Paginas", href: "/plataforma/cms/pages", icon: FileText },
  { id: "readiness", label: "Readiness", href: "/plataforma/cms/readiness", icon: Gauge },
  { id: "testimonios", label: "Testimonios", href: "/plataforma/cms/testimonials", icon: MessageCircle },
  { id: "menus", label: "Menus", href: "/plataforma/cms/menus", icon: Link2 },
  { id: "media", label: "Media", href: "/plataforma/cms/media", icon: ImageIcon },
  { id: "builder", label: "Builder", href: "/plataforma/cms/builder", icon: PanelsTopLeft },
  { id: "resources", label: "Recursos", href: "/plataforma/cms/resources", icon: PackageOpen },
  { id: "themes", label: "Temas", href: "/plataforma/cms/themes", icon: Palette },
  { id: "sites", label: "Sitios", href: "/plataforma/cms/sites", icon: Globe },
  { id: "audit", label: "Auditoria", href: "/plataforma/cms/audit", icon: Shield },
  { id: "notifications", label: "Notificaciones", href: "/plataforma/cms/notifications", icon: Bell },
  { id: "webhooks", label: "Webhooks", href: "/plataforma/cms/webhooks", icon: Webhook },
  { id: "custom-types", label: "Tipos Custom", href: "/plataforma/cms/custom-types", icon: Puzzle },
  { id: "section-types", label: "Tipos Seccion", href: "/plataforma/cms/section-types", icon: Layers3 },
  { id: "glossary", label: "Glosario", href: "/plataforma/cms/glossary", icon: FileText },
  { id: "search-admin", label: "Busqueda", href: "/plataforma/cms/search-admin", icon: Search },
  { id: "sessions", label: "Sesiones", href: "/plataforma/cms/sessions", icon: Shield },
  { id: "media-folders", label: "Carpetas", href: "/plataforma/cms/media-folders", icon: FolderTree },
  { id: "redirects", label: "Redirecciones", href: "/plataforma/cms/redirects", icon: RotateCcw },
  { id: "broken-links", label: "Links Rotos", href: "/plataforma/cms/broken-links", icon: AlertTriangle },
] as const;

interface CmsNavStats {
  mediaTotal: number;
  pagesTotal: number;
  testimonialsTotal: number;
  postsTotal: number;
}

export function CmsModuleNav() {
  const pathname = usePathname();
  const { token, user } = useAuth();
  const canEdit = canEditCms(user?.role);
  const canManage = canManageSites(user?.role);
  const [stats, setStats] = useState<CmsNavStats | null>(null);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    Promise.allSettled([
      apiFetch<{ items: unknown[]; total: number }>("/cms/media", { token, cache: "no-store", query: { include_archived: "false" }, signal: controller.signal }),
      apiFetch<{ items: unknown[]; total: number }>("/cms/v2/sites/ccf/pages", { token, cache: "no-store", signal: controller.signal }),
      apiFetch<unknown[]>("/admin/testimonials", { token, cache: "no-store", signal: controller.signal }),
      apiFetch<{ items: unknown[]; total: number }>("/cms/v2/sites/ccf/posts", { token, cache: "no-store", signal: controller.signal }),
    ]).then(([mediaRes, pagesRes, testRes, postsRes]) => {
      if (controller.signal.aborted) return;
      setStats({
        mediaTotal: mediaRes.status === "fulfilled" ? (mediaRes.value?.total ?? (Array.isArray(mediaRes.value) ? mediaRes.value.length : 0)) : 0,
        pagesTotal: pagesRes.status === "fulfilled" ? (pagesRes.value?.total ?? (Array.isArray(pagesRes.value) ? pagesRes.value.length : 0)) : 0,
        testimonialsTotal: testRes.status === "fulfilled" ? (Array.isArray(testRes.value) ? testRes.value.length : 0) : 0,
        postsTotal: postsRes.status === "fulfilled" ? (postsRes.value?.total ?? (Array.isArray(postsRes.value) ? postsRes.value.length : 0)) : 0,
      });
    });
    return () => controller.abort();
  }, [token]);

  const availableTabs = CMS_TABS.filter((tab) => {
    if (tab.id === "sites") return canManage;
    if (tab.id !== "resumen") return canEdit;
    return true;
  });

  const activeTab =
    availableTabs.find((tab) => {
      if (tab.href === "/plataforma/cms") return pathname === "/plataforma/cms";
      return pathname ? pathname.startsWith(tab.href) : false;
    }) ?? availableTabs[0];

  return (
    <nav className="shrink-0 border-b border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] dark:border-white/[0.05] dark:bg-[#141517]">
      <div className="flex items-center gap-1.5 px-4 pt-2.5">
        <Globe size={8} className="text-[hsl(var(--text-secondary))]" />
        <span className="text-[11px] text-[hsl(var(--text-secondary))]">Sitio web</span>
        <ChevronRight size={8} className="text-[hsl(var(--text-secondary))]" />
        <span className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
          {activeTab?.label ?? "CMS"}
        </span>
      </div>

      <div className="overflow-x-auto px-2 pt-1">
        <div className="flex min-w-max items-center" role="tablist" aria-label="Navegacion del CMS">
          {availableTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab?.id === tab.id;
            return (
              <Link
                key={tab.id}
                href={tab.href}
                aria-current={isActive ? "page" : undefined}
                className={clsx(
                  "flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-[12px] font-medium transition-colors whitespace-nowrap",
                  isActive
                    ? "border-blue-500 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]"
                    : "border-transparent text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--border))] hover:text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]",
                )}
              >
                <Icon size={8} />
                {tab.label}
              </Link>
            );
          })}
        </div>
      </div>

      {stats && (
        <div className="flex items-center gap-4 px-4 py-1.5 border-t border-[hsl(var(--border))] dark:border-white/[0.03] overflow-x-auto">
          <Link href="/plataforma/cms/pages" className="flex items-center gap-1.5 text-[10px] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors whitespace-nowrap">
            <FileText size={10} />
            <span className="font-semibold">{stats.pagesTotal}</span> paginas
          </Link>
          <Link href="/plataforma/cms/media" className="flex items-center gap-1.5 text-[10px] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors whitespace-nowrap">
            <ImageIcon size={10} />
            <span className="font-semibold">{stats.mediaTotal}</span> media
          </Link>
          <Link href="/plataforma/cms/testimonials" className="flex items-center gap-1.5 text-[10px] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors whitespace-nowrap">
            <MessageCircle size={10} />
            <span className="font-semibold">{stats.testimonialsTotal}</span> testimonios
          </Link>
          <Link href="/plataforma/cms/posts" className="flex items-center gap-1.5 text-[10px] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors whitespace-nowrap">
            <PackageOpen size={10} />
            <span className="font-semibold">{stats.postsTotal}</span> posts
          </Link>
        </div>
      )}
    </nav>
  );
}
