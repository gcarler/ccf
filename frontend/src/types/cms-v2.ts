export interface CmsSite {
  id: number;
  site_key: string;
  name: string;
  base_path: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CmsTheme {
  id: number;
  site_id: number;
  name: string;
  tokens_json: Record<string, string>;
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface CmsMenu {
  id: number;
  site_id: number;
  menu_key: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CmsMenuItem {
  id: number;
  menu_id: number;
  parent_id: number | null;
  label: string;
  href: string;
  target: string;
  is_external: boolean;
  visibility: string;
  sort_order: number;
  meta_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CmsPublicMenu {
  site_key: string;
  menu_key: string;
  items: Array<{
    id: number;
    parent_id: number | null;
    label: string;
    href: string;
    target: string;
    is_external: boolean;
    visibility: string;
    sort_order: number;
    meta_json: Record<string, unknown>;
  }>;
}
