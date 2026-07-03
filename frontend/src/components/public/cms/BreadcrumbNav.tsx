"use client";

import React from "react";
import Link from "next/link";
import { ChevronRight, Home } from "lucide-react";
import type { BreadcrumbItem } from "@/types/cms-v2";

interface BreadcrumbNavProps {
  items: BreadcrumbItem[];
  className?: string;
}

export default function BreadcrumbNav({ items, className = "" }: BreadcrumbNavProps) {
  if (!items || items.length === 0) return null;

  const visibleItems = items.slice(0, -1);
  const currentItem = items[items.length - 1];

  return (
    <nav
      aria-label="Breadcrumb"
      className={`w-full ${className}`}
    >
      <ol className="flex flex-wrap items-center gap-1 text-sm text-[hsl(var(--text-secondary))]">
        {visibleItems.map((item, index) => {
          const isHome = index === 0;
          const href = item.item || "";
          const isClickable = href && index < visibleItems.length;

          return (
            <li key={index} className="flex items-center gap-1">
              {isClickable ? (
                <Link
                  href={href}
                  className="inline-flex items-center gap-1 hover:text-[hsl(var(--primary))] transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] rounded px-0.5"
                >
                  {isHome && <Home size={14} className="shrink-0" />}
                  <span className={isHome ? "sr-only" : ""}>{item.name}</span>
                  {isHome && <span aria-hidden="true" className="hidden">{item.name}</span>}
                </Link>
              ) : (
                <span className="inline-flex items-center gap-1">
                  {isHome && <Home size={14} className="shrink-0" />}
                  {item.name}
                </span>
              )}
              <ChevronRight size={14} className="shrink-0 opacity-50 mx-0.5" aria-hidden="true" />
            </li>
          );
        })}
        {currentItem && (
          <li className="flex items-center">
            <span
              aria-current="page"
              className="font-medium text-[hsl(var(--text-primary))] truncate max-w-[200px] sm:max-w-[300px] md:max-w-[400px]"
            >
              {currentItem.name}
            </span>
          </li>
        )}
      </ol>
    </nav>
  );
}
