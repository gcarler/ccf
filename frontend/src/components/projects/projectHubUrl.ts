/**
 * Serialización del estado del Hub de herramientas en la query string (H-PROJ-UI-02).
 *
 * La página del detalle usa estos helpers para que el hub sea deep-linkable:
 * `?tool=evm&tool=risks&toolActive=risks` abre ambos módulos con Riesgos
 * activo; al quitarlos (router.replace) el hub se cierra y el botón Atrás
 * restaura el estado anterior, porque la URL es la fuente de verdad.
 */

export const HUB_TOOL_PARAM = "tool";
export const HUB_ACTIVE_PARAM = "toolActive";

export interface ProjectHubUrlState {
  open: string[];
  active: string | null;
}

export function readHubState(params: URLSearchParams): ProjectHubUrlState {
  const open: string[] = [];
  const activeExplicit = params.get(HUB_ACTIVE_PARAM);
  for (const key of params.getAll(HUB_TOOL_PARAM)) {
    if (key && !open.includes(key)) open.push(key);
  }
  const active =
    activeExplicit && open.includes(activeExplicit) ? activeExplicit : open[open.length - 1] ?? null;
  return { open, active };
}

export function writeHubParams(
  base: URLSearchParams,
  hub: ProjectHubUrlState
): URLSearchParams {
  const next = new URLSearchParams(base);
  next.delete(HUB_TOOL_PARAM);
  next.delete(HUB_ACTIVE_PARAM);
  for (const key of hub.open) {
    if (key) next.append(HUB_TOOL_PARAM, key);
  }
  if (hub.active) next.set(HUB_ACTIVE_PARAM, hub.active);
  return next;
}

export function hubStateChanged(a: ProjectHubUrlState, b: ProjectHubUrlState): boolean {
  return (
    a.active !== b.active ||
    a.open.length !== b.open.length ||
    a.open.some((key, index) => key !== b.open[index])
  );
}
