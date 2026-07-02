"use client";

import React from "react";
import { LayoutPanelTop } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { canEditCms, canPublishCms } from "@/lib/cms/permissions";
import { usePageBuilder } from "@/hooks/usePageBuilder";
import BuilderSidebar from "@/components/cms/builder/BuilderSidebar";
import BuilderCanvas from "@/components/cms/builder/BuilderCanvas";
import BuilderRightPanel from "@/components/cms/builder/BuilderRightPanel";
import MediaPicker from "@/components/cms/builder/MediaPicker";

export default function CmsBuilderPage() {
  const { token, user } = useAuth();
  const canEdit = canEditCms(user?.role);
  const canPublish = canPublishCms(user?.role);

  const builder = usePageBuilder({ token, canEdit, canPublish });

  return (
    <div className="space-y-3 p-3">
      <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#111418] p-3 flex items-center justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">CMS V2 Builder</p>
          <h1 className="mt-2 text-lg font-semibold">Constructor visual multisitio</h1>
        </div>
        <div className="rounded-md bg-primary/10 px-3 py-2 text-primary text-xs font-semibold uppercase tracking-wide inline-flex items-center gap-2">
          <LayoutPanelTop size={14} /> Beta
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        <BuilderSidebar builder={builder} />
        <BuilderCanvas builder={builder} />
        <BuilderRightPanel builder={builder} />
      </div>

      {builder.mediaPickerOpen && (
        <MediaPicker
          open
          token={builder.token}
          selectedUrl={builder.mediaPickerTarget === "seo" ? builder.seoImageDraft : ((builder.activeSection?.props_json as Record<string, unknown>)?.image_url as string | undefined)}
          onClose={() => builder.setMediaPickerOpen(false)}
          onSelect={(item) => {
            const url = typeof item === "string" ? item : (item as { url?: string }).url || "";
            if (builder.mediaPickerTarget === "section" && builder.activeSection) {
              const nextProps = {
                ...((builder.activeSection.props_json as Record<string, unknown>) || {}),
                image_url: url,
              };
              builder.updateSectionPropsLocal(nextProps);
              builder.saveSectionProps(nextProps);
            } else if (builder.mediaPickerTarget === "seo") {
              builder.setSeoImageDraft(url);
            }
            builder.setMediaPickerOpen(false);
          }}
        />
      )}
    </div>
  );
}
