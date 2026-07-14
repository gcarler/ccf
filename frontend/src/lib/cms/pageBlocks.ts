import type { CmsPageBlocks } from "@/types/cms-v2";

type CmsSectionLike = {
  section_key?: string | null;
  props_json?: Record<string, unknown> | null;
};

export function buildCmsPageBlocks(sections: CmsSectionLike[] | undefined | null): CmsPageBlocks {
  const blocks: CmsPageBlocks = {};

  for (const section of sections ?? []) {
    const key = section.section_key?.trim();
    if (!key) continue;

    const parsed = section.props_json && typeof section.props_json === "object" && !Array.isArray(section.props_json)
      ? section.props_json
      : {};

    blocks[key] = {
      ...parsed,
      parsed,
      content: JSON.stringify(parsed),
    };
  }

  return blocks;
}
