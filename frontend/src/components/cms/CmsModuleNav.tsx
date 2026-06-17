"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  CalendarRange,
  ChevronRight,
  Feather,
  FileText,
  Globe,
  ImageIcon,
  LayoutDashboard,
  Link2,
  MessageCircle,
  Palette,
  PanelsTopLeft,
  PackageOpen,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { canEditCms, canManageSites } from "@/lib/cms/permissions";

const CMS_TABS = [
  { id: "resumen", label: "Resumen", href: "/cms", icon: LayoutDashboard },
  { id: "paginas", label: "Paginas", href: "/cms/pages", icon: FileText },
  { id: "testimonios", label: "Testimonios", href: "/cms/testimonials", icon: MessageCircle },
  { id: "hero", label: "Landing hero", href: "/cms/content", icon: Feather },
  { id: "eventos", label: "Eventos", href: "/cms/events", icon: CalendarRange },
  { id: "menus", label: "Menus", href: "/cms/menus", icon: Link2 },
  { id: "media", label: "Media", href: "/cms/media", icon: ImageIcon },
  { id: "builder", label: "Builder", href: "/cms/builder", icon: PanelsTopLeft },
  { id: "resources", label: "Recursos", href: "/cms/resources", icon: PackageOpen },
  { id: "themes", label: "Temas", href: "/cms/themes", icon: Palette },
  { id: "sites", label: "Sitios", href: "/cms/sites", icon: Globe },
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
    <nav className="shrink-0 border-b border-slate-100 bg-[hsl(var(--bg-primary))] dark:border-white/[0.05] dark:bg-[#141517]">
      <div className="flex items-center gap-1.5 px-4 pt-2.5">
        <Globe size={8} className="text-slate-400" />
        <span className="text-[11px] text-slate-400">Sitio web</span>
        <ChevronRight size={8} className="text-slate-300" />
        <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-200">
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
                    : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100",
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
