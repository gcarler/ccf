"use client";

import React from "react";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import { ModuleErrorBoundary } from "@/components/ModuleErrorBoundary";
import { CmsModuleNav } from "@/components/cms/CmsModuleNav";

export default function CmsLayout({ children }: { children: React.ReactNode }) {
  return (
    <ModuleErrorBoundary moduleName="CMS">
      <WorkspaceLayout allowedPermissions={['cms:read']}>
        <div className="flex h-full flex-col">
          <CmsModuleNav />
          <div className="flex-1">{children}</div>
        </div>
      </WorkspaceLayout>
    </ModuleErrorBoundary>
  );
}

