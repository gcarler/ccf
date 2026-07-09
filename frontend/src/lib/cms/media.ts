/**
 * Return a publicly reachable URL for a CMS media asset.
 *
 * StorageService persists assets under `uploads/` and records their public
 * path as `/static/...`, but the frontend serves (and proxies) them through
 * `/api/static/...`. This helper normalises either form so CMS images work
 * in both public pages and the admin dashboard.
 */
export function getCmsMediaUrl(url: string | undefined | null): string {
  if (!url) return "";
  if (url.startsWith("/api/static/")) return url;
  if (url.startsWith("/static/")) return `/api/static/${url.slice(8)}`;
  return url;
}
