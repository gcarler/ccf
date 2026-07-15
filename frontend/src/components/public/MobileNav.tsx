"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CalendarDays,
  Home,
  MapPin,
  Menu,
  PlayCircle,
  type LucideIcon,
} from "lucide-react";
import { getCmsPublicMenu } from "@/lib/cms/v2";
import { SITE_KEY } from "@/lib/site-config";
import { usePublicBootstrap } from "./PublicBootstrapProvider";

const ICON_MAP: Record<string, LucideIcon> = {
  Home,
  CalendarDays,
  PlayCircle,
  MapPin,
  Menu,
};

function fallbackIcon(href: string): LucideIcon {
  if (href === "/") return Home;
  if (href === "/eventos") return CalendarDays;
  if (href === "/predicas") return PlayCircle;
  if (href === "/sedes") return MapPin;
  return Menu;
}

type MobileMenuItem = {
  id: string;
  href: string;
  label: string;
  meta_json: Record<string, unknown>;
};

export default function MobileNav() {
  const pathname = usePathname();
  const bootstrapMenu = usePublicBootstrap()?.menus?.mobile ?? null;
  const [items, setItems] = useState<MobileMenuItem[]>(() => {
    if (!bootstrapMenu) return [];
    return (bootstrapMenu.items || [])
      .filter((item) => item.visibility !== "hidden")
      .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
      .map((item) => ({
        id: item.id,
        href: item.href,
        label: item.label,
        meta_json: item.meta_json || {},
      }));
  });

  useEffect(() => {
    if (bootstrapMenu) {
      setItems(
        (bootstrapMenu.items || [])
          .filter((item) => item.visibility !== "hidden")
          .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
          .map((item) => ({
            id: item.id,
            href: item.href,
            label: item.label,
            meta_json: item.meta_json || {},
          }))
      );
      return;
    }

    let mounted = true;
    const loadMenu = async () => {
      try {
        const data = await getCmsPublicMenu(SITE_KEY, "mobile");
        const all = (data?.items || [])
          .filter((item) => item.visibility !== "hidden")
          .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
        if (mounted) {
          setItems(
            all.map((item) => ({
              id: item.id,
              href: item.href,
              label: item.label,
              meta_json: item.meta_json || {},
            }))
          );
        }
      } catch {
        // Ignore; empty menu renders nothing.
      }
    };
    loadMenu();
    return () => {
      mounted = false;
    };
  }, [bootstrapMenu]);

  return (
    <nav className="md:hidden fixed bottom-0 left-0 w-full flex justify-center z-50" style={{ paddingBottom: 'max(1.75rem, env(safe-area-inset-bottom))' }}>
      <div
        className="backdrop-blur-2xl w-[92%] max-w-md rounded-[1rem] px-4 py-3.5 flex justify-between items-center"
        style={{
          background: "var(--site-mobile-nav-bg)",
          boxShadow: "var(--site-mobile-nav-shadow)",
        }}
      >
        {items.map(({ id, href, label, meta_json }) => {
          const isActive = pathname === href || (href !== "/" && pathname?.startsWith(href));
          const iconName = String((meta_json as Record<string, unknown>)?.icon || "");
          const Icon = ICON_MAP[iconName] || fallbackIcon(href);
          return (
            <Link
              key={id}
              href={href}
              className="flex flex-col items-center justify-center rounded-[0.875rem] px-2.5 py-2 transition-all"
              style={isActive
                ? {
                    color: "var(--site-primary)",
                    background: "var(--site-primary-container)",
                    boxShadow: "var(--site-mobile-nav-glow)",
                  }
                : {
                    color: "var(--site-mobile-nav-inactive)",
                  }
              }
            >
              <Icon size={22} strokeWidth={2} aria-hidden="true" />
              <span className="font-body text-[11px] font-medium tracking-wide mt-1">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export const MobileNav_compat = MobileNav;
