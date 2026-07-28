/**
 * Shared helpers for CMS public section renderers.
 *
 * Extracted from ``PublicSectionRenderer.tsx`` to reduce duplication and
 * enable individual section files to import these utilities without
 * depending on the monolithic renderer file.
 *
 * ``val`` / ``asItems`` delegate to ``@/lib/cms/heroPopup`` which
 * normalises raw ``props_json`` values into safe strings / arrays.
 * ``asProps`` casts a typed props interface to the loose
 * ``Record<string, unknown>`` shape that ``val``/``asItems`` expect.
 * ``asTyped`` narrows a generic ``CmsSection`` to a typed variant —
 * safe because the backend ``validate_section_props`` guarantees
 * type/props alignment on write.
 */
import type { CmsSection } from "@/types/cms-v2";
import { cmsItems, cmsValue } from "@/lib/cms/heroPopup";

/** Safely read a string value from ``props_json`` with a fallback. */
export function val(props: Record<string, unknown>, key: string, fallback = "") {
  return cmsValue(props, key, fallback);
}

/** Coerce a ``props_json`` array field into ``Array<Record<string, unknown>>``. */
export function asItems(props: Record<string, unknown>): Array<Record<string, unknown>> {
  return cmsItems(props);
}

/**
 * Cast a narrow ``XxxProps`` interface to the ``Record<string, unknown>``
 * shape that ``val`` / ``asItems`` expect. TS refuses the assignment
 * directly because interfaces don't carry an implicit index signature,
 * but the cast is safe — the backend sanitiser already dropped unknown
 * keys before persisting.
 */
export const asProps = (props: object): Record<string, unknown> =>
  props as unknown as Record<string, unknown>;

/**
 * Type-only cast of a generic ``CmsSection`` to ``CmsSection<T>``.
 *
 * Safe because ``backend.schemas.cms_v2_sections.validate_section_props``
 * enforces that ``type`` and ``props_json`` are kept in sync on write.
 */
export function asTyped<T extends string>(section: CmsSection): CmsSection<T> {
  return section as unknown as CmsSection<T>;
}
