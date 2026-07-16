"use client";

import { AllCommunityModule, ModuleRegistry } from "ag-grid-community";

let agGridModulesRegistered = false;

export function ensureAgGridModulesRegistered() {
  if (agGridModulesRegistered) return;
  ModuleRegistry.registerModules([AllCommunityModule]);
  agGridModulesRegistered = true;
}

ensureAgGridModulesRegistered();
