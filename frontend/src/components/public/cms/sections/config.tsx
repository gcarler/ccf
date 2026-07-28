"use client";

import { CmsSection } from "@/types/cms-v2";
import type { FooterConfigProps, MobileMenuConfigProps } from "@/types/cms-section-props";
import Link from "next/link";
import { asItems, asProps, val } from "./shared";

export function FooterConfigSection({ section }: { section: CmsSection<"footer_config"> }) {
  const props: FooterConfigProps = section.props_json ?? {};
  const p = asProps(props);
  const description = val(p, "brand_description", "");
  const copyright = val(p, "copyright", "");
  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {description && <p className="text-sm leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>{description}</p>}
      {copyright && <p className="mt-4 text-xs" style={{ color: "var(--site-on-surface-variant)" }}>{copyright}</p>}
    </section>
  );
}

// ─── Mobile Menu Config (rendered as a regular section when used inside a page) ─

export function MobileMenuConfigSection({ section }: { section: CmsSection<"mobile_menu_config"> }) {
  const props: MobileMenuConfigProps = section.props_json ?? {};
  const p = asProps(props);
  const items = asItems(p).slice(0, 8) as Array<{ label?: string; href?: string; icon?: string }>;
  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {items.map((item, i) => (
          <Link key={i} href={item.href || "/"} className="rounded-xl p-4 text-center text-sm font-bold" style={{ background: "var(--site-surface-container)", color: "var(--site-on-surface)" }}>
            {item.label || `Item ${i + 1}`}
          </Link>
        ))}
      </div>
    </section>
  );
}

