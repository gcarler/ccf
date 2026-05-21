"use client";

import React from "react";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import { CmsModuleNav } from "@/components/cms/CmsModuleNav";

export default function CmsLayout({ children }: { children: React.ReactNode }) {
  return (
    <WorkspaceLayout>
      <div className="flex h-full flex-col">
        <CmsModuleNav />
        <div className="flex-1 overflow-hidden">{children}</div>
      </div>
    </WorkspaceLayout>
  );
}

