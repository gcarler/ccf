/**
 * Semantic diff between two ``CmsPageVersion`` snapshots.
 *
 * Reuses the existing ``snapshot_json`` contract produced by
 * ``backend.crud.cms._build_page_snapshot`` — i.e.
 *
 *   snapshot_json = {
 *     page:   { id, slug, title, status, seo_json },
 *     sections: [
 *       { id, section_key, type, props_json, sort_order, is_visible, status },
 *       ...
 *     ],
 *   }
 *
 * The diff is **semantic** (not raw-string): we walk the JSON tree and
 * apply different strategies per value type:
 *
 *   - ``string``            → word-level LCS diff (highlights added/removed tokens)
 *   - ``number`` / ``bool`` → simple ``changed`` / ``unchanged`` marker
 *   - ``null`` / ``undef``  → tracked as "field removed/added" in the JSON shape
 *   - ``array``             → matched by stable key (``id`` / ``key`` / ``section_key``)
 *                             when present, else by index
 *   - ``object``            → recursive
 *
 * Sections are matched by ``section_key`` (the stable, user-facing
 * identifier) with fallback to ``id`` (uuid). This keeps the diff
 * stable across renames of section types and across server-side
 * regenerations of uuids during a rollback.
 */

// ── Types ──────────────────────────────────────────────────────────────

export type DiffTokenType = "unchanged" | "added" | "removed";

export interface DiffToken {
  type: DiffTokenType;
  value: string;
}

export type FieldDiffKind =
  | "unchanged"
  | "added"
  | "removed"
  | "changed";

export interface FieldDiff<T = unknown> {
  kind: FieldDiffKind;
  before?: T;
  after?: T;
  /** Word-level tokens when both sides are strings. */
  tokens?: DiffToken[];
}

export type SectionStatus =
  | "unchanged"
  | "added"
  | "removed"
  | "reordered"
  | "visibility-changed"
  | "status-changed"
  | "modified";

export interface SectionDiff {
  /** Stable key from snapshot — used as React key in the UI. */
  section_key: string;
  /** Section type (``hero``, ``rich_text``, ``gallery`` …) */
  type: string;
  /** Resolved semantic status of the diff. */
  status: SectionStatus;
  /** Original section payload (undefined for "added"). */
  before?: SectionSnapshot;
  /** Updated section payload (undefined for "removed"). */
  after?: SectionSnapshot;
  /** Pre-diff sort_order, if known (used by "reordered"). */
  sort_before?: number;
  /** Post-diff sort_order, if known (used by "reordered"). */
  sort_after?: number;
  /** Field-level diffs of ``props_json`` (only when status is "modified"). */
  prop_diffs?: Record<string, FieldDiff>;
}

export interface PageMetaSnapshot {
  id?: string;
  slug?: string;
  title?: string;
  status?: string;
  seo_json?: Record<string, unknown>;
}

export interface SectionSnapshot {
  id?: string;
  section_key?: string;
  type?: string;
  props_json?: Record<string, unknown>;
  sort_order?: number;
  is_visible?: boolean;
  status?: string;
}

export interface PageVersionSnapshot {
  page?: PageMetaSnapshot;
  sections?: SectionSnapshot[];
}

export interface PageMetaDiff {
  title: FieldDiff;
  slug: FieldDiff;
  status: FieldDiff;
  seo: Record<string, FieldDiff>;
}

export interface PageVersionDiff {
  /** Page-level metadata changes. */
  pageMeta: PageMetaDiff;
  /** Section-level changes in render order. */
  sections: SectionDiff[];
  /** Counts used by the summary header. */
  summary: {
    sectionsAdded: number;
    sectionsRemoved: number;
    sectionsReordered: number;
    sectionsModified: number;
    sectionsUnchanged: number;
    seoFieldsChanged: number;
    titleChanged: boolean;
  };
}

// ── Public API ─────────────────────────────────────────────────────────

/**
 * Top-level entry: compute a full diff between two ``CmsPageVersion``
 * snapshots (just the ``snapshot_json`` of each).
 */
export function diffPageVersionSnapshots(
  before: PageVersionSnapshot | null | undefined,
  after: PageVersionSnapshot | null | undefined,
): PageVersionDiff {
  const safeBefore = before ?? {};
  const safeAfter = after ?? {};
  const pageMeta = diffPageMeta(safeBefore.page, safeAfter.page);
  const sections = diffSections(safeBefore.sections, safeAfter.sections);

  return {
    pageMeta,
    sections,
    summary: {
      sectionsAdded: sections.filter((s) => s.status === "added").length,
      sectionsRemoved: sections.filter((s) => s.status === "removed").length,
      sectionsReordered: sections.filter((s) => s.status === "reordered").length,
      sectionsModified: sections.filter(
        (s) =>
          s.status === "modified" ||
          s.status === "visibility-changed" ||
          s.status === "status-changed",
      ).length,
      sectionsUnchanged: sections.filter((s) => s.status === "unchanged").length,
      seoFieldsChanged: Object.values(pageMeta.seo).filter(
        (f) => f.kind !== "unchanged",
      ).length,
      titleChanged: pageMeta.title.kind !== "unchanged",
    },
  };
}

// ── Page-level diff ────────────────────────────────────────────────────

function diffPageMeta(
  before: PageMetaSnapshot | undefined,
  after: PageMetaSnapshot | undefined,
): PageMetaDiff {
  const safeBefore = before ?? {};
  const safeAfter = after ?? {};

  const title = diffStringField(safeBefore.title, safeAfter.title);
  const slug = diffStringField(safeBefore.slug, safeAfter.slug);
  const status = diffField(safeBefore.status, safeAfter.status);

  // seo_json is a nested object — recurse.
  const seo = diffObject(
    safeBefore.seo_json ?? {},
    safeAfter.seo_json ?? {},
  );

  return { title, slug, status, seo };
}

// ── Section-level diff ─────────────────────────────────────────────────

function diffSections(
  before: SectionSnapshot[] | undefined,
  after: SectionSnapshot[] | undefined,
): SectionDiff[] {
  const aList = before ?? [];
  const bList = after ?? [];

  // Index by stable key — section_key primary, id fallback.
  const indexByKey = (list: SectionSnapshot[]) => {
    const byKey = new Map<string, SectionSnapshot>();
    for (const s of list) {
      const k = stableKey(s);
      if (!k) continue;
      byKey.set(k, s);
    }
    return byKey;
  };

  const aMap = indexByKey(aList);
  const bMap = indexByKey(bList);

  // Orphan fallback: sections with no ``section_key`` and no ``id`` on
  // either side cannot be matched by stable id. We still surface them
  // so editors see "something disappeared" or "something new appeared"
  // rather than silently dropping data. Synthesize a positional key
  // tagged with the side and a hard-to-collision sentinel prefix.
  // The prefix is intentionally long and unique (double underscore,
  // explicit "versiondiff_orphan" tag, double trailing underscore) so
  // an editor-defined ``section_key`` can never accidentally match.
  // ``diffOneSection`` will display these rows with a "(sin clave)"
  // label so the operator notices the data-integrity issue.
  const ORPHAN_PREFIX_BEFORE = "__versiondiff_orphan_before_";
  const ORPHAN_PREFIX_AFTER = "__versiondiff_orphan_after_";
  let orphanCount = 0;
  for (let i = 0; i < aList.length; i++) {
    if (stableKey(aList[i])) continue;
    const synthetic = `${ORPHAN_PREFIX_BEFORE}${i}__`;
    aMap.set(synthetic, aList[i]);
    orphanCount++;
  }
  for (let i = 0; i < bList.length; i++) {
    if (stableKey(bList[i])) continue;
    const synthetic = `${ORPHAN_PREFIX_AFTER}${i}__`;
    bMap.set(synthetic, bList[i]);
    orphanCount++;
  }
  // orphanCount sections without section_key/id use positional fallback keys

  // Preserve render order: walk B (newer) first so unchanged / modified
  // sections appear in their final position. Then append any A-only
  // (removed) sections at the end in their original order.
  const orderedKeys: string[] = [];
  const seen = new Set<string>();
  for (let i = 0; i < bList.length; i++) {
    const k = stableKey(bList[i]) || `${ORPHAN_PREFIX_AFTER}${i}__`;
    if (!seen.has(k)) {
      orderedKeys.push(k);
      seen.add(k);
    }
  }
  for (let i = 0; i < aList.length; i++) {
    const k = stableKey(aList[i]) || `${ORPHAN_PREFIX_BEFORE}${i}__`;
    if (!seen.has(k)) {
      orderedKeys.push(k);
      seen.add(k);
    }
  }

  const diffs: SectionDiff[] = [];
  for (const key of orderedKeys) {
    const a = aMap.get(key);
    const b = bMap.get(key);
    diffs.push(diffOneSection(key, a, b));
  }
  return diffs;
}

function diffOneSection(
  key: string,
  a: SectionSnapshot | undefined,
  b: SectionSnapshot | undefined,
): SectionDiff {
  // Orphan fallback rows get a synthetic key like
  // ``__versiondiff_orphan_before_0__``. We surface them in the UI
  // with a "(sin clave)" label and the side-specific index so the
  // editor can distinguish multiple orphan rows.
  let displayKey = key;
  if (key.startsWith("__versiondiff_orphan_before_")) {
    const idx = key.slice("__versiondiff_orphan_before_".length, -2);
    displayKey = `(sin clave, antes #${idx})`;
  } else if (key.startsWith("__versiondiff_orphan_after_")) {
    const idx = key.slice("__versiondiff_orphan_after_".length, -2);
    displayKey = `(sin clave, después #${idx})`;
  }

  if (a && !b) {
    return {
      section_key: displayKey,
      type: a.type || "unknown",
      status: "removed",
      before: a,
      sort_before: a.sort_order,
    };
  }
  if (!a && b) {
    return {
      section_key: displayKey,
      type: b.type || "unknown",
      status: "added",
      after: b,
      sort_after: b.sort_order,
    };
  }
  if (!a || !b) {
    // Shouldn't happen — defensive.
    return {
      section_key: displayKey,
      type: (a?.type || b?.type) ?? "unknown",
      status: "unchanged",
    };
  }

  // Both present — compute semantic status.
  const sameProps = shallowEqualJson(a.props_json, b.props_json);
  const sameVisibility = Boolean(a.is_visible) === Boolean(b.is_visible);
  const sameStatus = (a.status || "active") === (b.status || "active");
  const sameType = (a.type || "") === (b.type || "");
  const sameSort = (a.sort_order ?? 0) === (b.sort_order ?? 0);

  if (sameProps && sameVisibility && sameStatus && sameType && sameSort) {
    return {
      section_key: displayKey,
      type: b.type || a.type || "unknown",
      status: "unchanged",
      before: a,
      after: b,
    };
  }

  // Reorder-only (no content change) is its own semantic category.
  if (sameProps && sameVisibility && sameStatus && sameType && !sameSort) {
    return {
      section_key: displayKey,
      type: b.type || a.type || "unknown",
      status: "reordered",
      before: a,
      after: b,
      sort_before: a.sort_order,
      sort_after: b.sort_order,
    };
  }

  if (sameProps && !sameVisibility && sameStatus && sameType) {
    return {
      section_key: displayKey,
      type: b.type || a.type || "unknown",
      status: "visibility-changed",
      before: a,
      after: b,
    };
  }

  if (sameProps && sameVisibility && !sameStatus && sameType) {
    return {
      section_key: displayKey,
      type: b.type || a.type || "unknown",
      status: "status-changed",
      before: a,
      after: b,
    };
  }

  // Modified — produce per-field diff for props_json.
  const prop_diffs = diffObject(a.props_json ?? {}, b.props_json ?? {});
  return {
    section_key: displayKey,
    type: b.type || a.type || "unknown",
    status: "modified",
    before: a,
    after: b,
    prop_diffs,
  };
}

// ── Generic JSON diff ──────────────────────────────────────────────────

/**
 * Diff two arbitrary JSON values, choosing the right strategy by type.
 */
export function diffValue(before: unknown, after: unknown): FieldDiff {
  if (before === undefined && after === undefined) {
    return { kind: "unchanged" };
  }
  if (before === undefined) {
    return { kind: "added", after };
  }
  if (after === undefined) {
    return { kind: "removed", before };
  }
  if (typeof before === "string" && typeof after === "string") {
    return diffStringField(before, after);
  }
  if (isScalar(before) && isScalar(after)) {
    return diffField(before, after);
  }
  if (Array.isArray(before) && Array.isArray(after)) {
    return diffArray(before, after);
  }
  if (isPlainObject(before) && isPlainObject(after)) {
    // Both sides are objects: treat as a single ``changed`` unit at
    // this level. The recursion into per-field diffs is left to
    // ``diffObject`` (which the caller uses for nested objects).
    // Returning a flat ``FieldDiff`` here keeps the type contract
    // clean: ``diffValue`` always returns ``FieldDiff``.
    return shallowEqualJson(before, after)
      ? { kind: "unchanged" }
      : { kind: "changed", before, after };
  }
  // Type mismatch — treat as a full replace.
  return { kind: "changed", before, after };
}

/**
 * Diff two plain objects key-by-key. Returns a map of ``field name →
 * FieldDiff``. Only keys present on either side are included.
 */
export function diffObject(
  before: Record<string, unknown>,
  after: Record<string, unknown>,
): Record<string, FieldDiff> {
  const keys = new Set<string>([
    ...Object.keys(before ?? {}),
    ...Object.keys(after ?? {}),
  ]);
  const result: Record<string, FieldDiff> = {};
  for (const key of keys) {
    const fieldDiff = diffValue(before?.[key], after?.[key]);
    if (fieldDiff.kind !== "unchanged") {
      result[key] = fieldDiff;
    }
  }
  return result;
}

/**
 * Diff two arrays. Strategy:
 *   - When items are objects with a stable key (``id`` / ``key`` /
 *     ``section_key``), match by key and produce one FieldDiff per
 *     key. This makes a gallery re-ordering show as "moved" rather
 *     than "removed + added".
 *   - Otherwise, fall back to positional comparison.
 */
export function diffArray(before: unknown[], after: unknown[]): FieldDiff {
  const useKey = stableArrayKey(before) || stableArrayKey(after);
  if (useKey) {
    // Stable-keyed diff. Build maps keyed by the stable id, then
    // detect a single ``changed`` outcome if any item was added,
    // removed, modified, or reordered. Per-item granular highlighting
    // is intentionally NOT exposed here — for that level of detail
    // the UI should open a dedicated diff for that array's owner
    // (e.g., a gallery section). Keeping the return shape flat
    // matches the positional fallback below and avoids carrying
    // dead metadata through the rest of the pipeline.
    const beforeMap = new Map<string, unknown>();
    const afterMap = new Map<string, unknown>();
    for (const item of before) {
      const k = stableKeyOf(item, useKey);
      if (k != null) beforeMap.set(k, item);
    }
    for (const item of after) {
      const k = stableKeyOf(item, useKey);
      if (k != null) afterMap.set(k, item);
    }

    let anyChange = beforeMap.size !== afterMap.size;
    if (!anyChange) {
      for (const [k, a] of beforeMap) {
        if (!afterMap.has(k)) {
          anyChange = true;
          break;
        }
        if (!Object.is(a, afterMap.get(k))) {
          anyChange = true;
          break;
        }
      }
    }
    if (!anyChange) {
      // Even if set equality + element equality match, the order may have
      // shifted (matters semantically for ordered lists).
      for (let i = 0; i < after.length; i++) {
        const k = stableKeyOf(after[i], useKey);
        if (k == null) continue;
        if (i < before.length) {
          const beforeK = stableKeyOf(before[i], useKey);
          if (beforeK !== k) {
            anyChange = true;
            break;
          }
        }
      }
    }
    return {
      kind: anyChange ? "changed" : "unchanged",
      before,
      after,
    };
  }

  // Positional fallback: any length or value mismatch is a single
  // "changed" marker. Per-index granularity would require surfacing
  // a perIndex map through the FieldDiff type, which the UI doesn't
  // consume today. Keep the shape flat.
  const max = Math.max(before.length, after.length);
  let changed = before.length !== after.length;
  for (let i = 0; !changed && i < max; i++) {
    if (!Object.is(before[i], after[i])) changed = true;
  }
  return {
    kind: changed ? "changed" : "unchanged",
    before,
    after,
  };
}

// ── Helpers ────────────────────────────────────────────────────────────

function diffStringField(before: string | undefined, after: string | undefined): FieldDiff {
  const a = before ?? "";
  const b = after ?? "";
  if (a === b) return { kind: "unchanged" };
  // Empty-string sentinel: missing on either side.
  if (!a && b) return { kind: "added", after: b, tokens: splitTokens(b).map((t) => ({ type: "added", value: t })) };
  if (a && !b) return { kind: "removed", before: a, tokens: splitTokens(a).map((t) => ({ type: "removed", value: t })) };
  const tokens = diffWords(a, b);
  return { kind: "changed", before: a, after: b, tokens };
}

function diffField(before: unknown, after: unknown): FieldDiff {
  if (Object.is(before, after)) return { kind: "unchanged" };
  return { kind: "changed", before, after };
}

/**
 * Word-level diff. Splits on whitespace + punctuation boundaries so
 * trailing punctuation lives with its word (preserves the visible
 * structure of the source).
 *
 * Returns a list of tokens tagged ``unchanged | added | removed``.
 * Algorithm: classic LCS DP over the token arrays. O(n*m) memory —
 * fine for our payload sizes (section text is short).
 */
export function diffWords(a: string, b: string): DiffToken[] {
  const aTokens = splitTokens(a);
  const bTokens = splitTokens(b);
  const m = aTokens.length;
  const n = bTokens.length;
  if (m === 0) return bTokens.map((t) => ({ type: "added", value: t }));
  if (n === 0) return aTokens.map((t) => ({ type: "removed", value: t }));

  // Build LCS length table.
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array<number>(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (aTokens[i - 1] === bTokens[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to produce the diff.
  const out: DiffToken[] = [];
  let i = m;
  let j = n;
  while (i > 0 && j > 0) {
    if (aTokens[i - 1] === bTokens[j - 1]) {
      out.push({ type: "unchanged", value: aTokens[i - 1] });
      i--;
      j--;
    } else if (dp[i - 1][j] >= dp[i][j - 1]) {
      out.push({ type: "removed", value: aTokens[i - 1] });
      i--;
    } else {
      out.push({ type: "added", value: bTokens[j - 1] });
      j--;
    }
  }
  while (i > 0) {
    out.push({ type: "removed", value: aTokens[i - 1] });
    i--;
  }
  while (j > 0) {
    out.push({ type: "added", value: bTokens[j - 1] });
    j--;
  }
  return out.reverse();
}

/**
 * Split a string into "word" tokens suitable for diffing. We split on
 * whitespace but keep trailing punctuation glued to the preceding
 * word, so the rendered highlight looks natural.
 */
function splitTokens(s: string): string[] {
  if (!s) return [];
  // Match a run of word characters optionally followed by trailing
  // punctuation, OR a run of whitespace, OR a single punctuation
  // char by itself.
  const re = /[A-Za-zÀ-ɏ0-9_]+(?:[''\-][A-Za-zÀ-ɏ0-9_]+)*[.,;:!?)]*|\s+|[^\sA-Za-zÀ-ɏ0-9_]/gu;
  return s.match(re) ?? [];
}

function isScalar(v: unknown): boolean {
  const t = typeof v;
  return v === null || t === "string" || t === "number" || t === "boolean";
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function shallowEqualJson(a: unknown, b: unknown): boolean {
  if (Object.is(a, b)) return true;
  if (a == null || b == null) return false;
  return JSON.stringify(sortKeys(a)) === JSON.stringify(sortKeys(b));
}

function sortKeys<T>(v: T): T {
  if (Array.isArray(v)) return v.map(sortKeys) as unknown as T;
  if (isPlainObject(v)) {
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(v).sort()) {
      out[key] = sortKeys((v as Record<string, unknown>)[key]);
    }
    return out as unknown as T;
  }
  return v;
}

/**
 * Decide which key (if any) to use for stable identity on the items
 * of ``arr``. Returns the chosen key name, or null when items lack a
 * stable identifier.
 */
function stableArrayKey(arr: unknown[]): string | null {
  if (arr.length === 0) return null;
  const sample = arr.find(isPlainObject);
  if (!sample) return null;
  // Prefer an explicit identifier; fall back to ``key`` / ``section_key``
  // (the same name used in the section diff) so the two halves of the
  // UI speak the same vocabulary.
  if ("id" in sample && (typeof sample.id === "string" || typeof sample.id === "number")) return "id";
  if ("key" in sample && (typeof sample.key === "string" || typeof sample.key === "number")) return "key";
  if ("section_key" in sample && typeof sample.section_key === "string") return "section_key";
  return null;
}

/**
 * Stable key for a section: ``section_key`` is the user-facing stable
 * identifier (used by ``CmsPublicPage.blocks``), so it takes priority.
 * Falls back to the row's UUID ``id`` when ``section_key`` is missing.
 * Returns null when neither is present — callers must handle the
 * orphan case (see ``indexByKey`` above).
 */
function stableKey(s: SectionSnapshot): string | null {
  if (s.section_key) return s.section_key;
  if (s.id) return s.id;
  return null;
}

function stableKeyOf(item: unknown, key: string): string | null {
  if (!isPlainObject(item)) return null;
  const v = (item as Record<string, unknown>)[key];
  if (v == null) return null;
  return String(v);
}

// ── Field-name pretty-printing ─────────────────────────────────────────

/**
 * Convert a snake_case / kebab-case field name to a human label.
 * Used by the UI to render field rows.
 */
export function humanizeFieldName(name: string): string {
  return name
    .replace(/[_-]+/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Pick a small, curated set of "semantic" props to highlight in the
 * diff, regardless of section type. Order matters: this is the order
 * the UI renders the rows in.
 */
export const SEMANTIC_PROP_FIELDS: readonly string[] = [
  "title",
  "subtitle",
  "eyebrow",
  "body",
  "description",
  "caption",
  "image_url",
  "image_alt",
  "video_url",
  "cta_label",
  "cta_href",
  "button_label",
  "button_href",
  "author",
  "role",
];

/**
 * Return only the prop field diffs that are semantic for the UI.
 * Falls back to "show everything that changed" if the section's
 * props_json doesn't use any of the curated fields (e.g., a brand
 * new section type with custom keys).
 */
export function filterSemanticPropDiffs(
  sectionType: string,
  prop_diffs: Record<string, FieldDiff> | undefined,
): Array<{ key: string; diff: FieldDiff }> {
  if (!prop_diffs) return [];
  const curated = new Set(SEMANTIC_PROP_FIELDS);
  const curatedRows: Array<{ key: string; diff: FieldDiff }> = [];
  const extraRows: Array<{ key: string; diff: FieldDiff }> = [];
  for (const [key, diff] of Object.entries(prop_diffs)) {
    const row = { key, diff };
    if (curated.has(key)) {
      curatedRows.push(row);
    } else {
      extraRows.push(row);
    }
  }
  // Curated rows first, sorted by curated order; then any extras
  // (custom section type) alphabetically.
  const orderIndex = (k: string) => {
    const i = SEMANTIC_PROP_FIELDS.indexOf(k);
    return i === -1 ? Number.MAX_SAFE_INTEGER : i;
  };
  curatedRows.sort((a, b) => orderIndex(a.key) - orderIndex(b.key));
  extraRows.sort((a, b) => a.key.localeCompare(b.key));
  return [...curatedRows, ...extraRows];
}
