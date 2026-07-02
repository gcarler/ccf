"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  ChevronRight,
  FileText,
  Globe,
  ImageIcon,
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
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { canEditCms, canManageSites } from "@/lib/cms/permissions";

const CMS_TABS = [
  { id: "resumen", label: "Resumen", href: "/cms", icon: LayoutDashboard },
  { id: "paginas", label: "Paginas", href: "/cms/pages", icon: FileText },
  { id: "testimonios", label: "Testimonios", href: "/cms/testimonials", icon: MessageCircle },
  { id: "menus", label: "Menus", href: "/cms/menus", icon: Link2 },
  { id: "media", label: "Media", href: "/cms/media", icon: ImageIcon },
  { id: "builder", label: "Builder", href: "/cms/builder", icon: PanelsTopLeft },
  { id: "resources", label: "Recursos", href: "/cms/resources", icon: PackageOpen },
  { id: "themes", label: "Temas", href: "/cms/themes", icon: Palette },
  { id: "sites", label: "Sitios", href: "/cms/sites", icon: Globe },
  { id: "audit", label: "Auditoria", href: "/cms/audit", icon: Shield },
  { id: "notifications", label: "Notificaciones", href: "/cms/notifications", icon: Bell },
  { id: "webhooks", label: "Webhooks", href: "/cms/webhooks", icon: Webhook },
  { id: "custom-types", label: "Tipos Custom", href: "/cms/custom-types", icon: Puzzle },
  { id: "glossary", label: "Glosario", href: "/cms/glossary", icon: FileText },
  { id: "search-admin", label: "Busqueda", href: "/cms/search-admin", icon: Search },
  { id: "sessions", label: "Sesiones", href: "/cms/sessions", icon: Shield },
  { id: "media-folders", label: "Carpetas", href: "/cms/media-folders", icon: FolderTree },
  { id: "redirects", label: "Redirecciones", href: "/cms/redirects", icon: RotateCcw },
  { id: "broken-links", label: "Links Rotos", href: "/cms/broken-links", icon: AlertTriangle },
] as const;

export function CmsModuleNav() {
  const pathname = usePathname();
  const { user } = useAuth();
  const canEdit = canEditCms(user?.role);
  const canManage = canManageSites(user?.role);

  const availableTabs = CMS_TABS.filter((tab) => {
    if (tab.id === "sites") return canManage;
    if (tab.id !== "resumen") return canEdit;
    return true;
  });

  const activeTab =
    availableTabs.find((tab) => {
      if (tab.href === "/cms") return pathname === "/cms";
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
    </nav>
  );
}
