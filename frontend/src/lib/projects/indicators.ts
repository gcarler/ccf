export type IndicatorSpiStatus = "optimal" | "warning" | "critical" | "unavailable";

export function getIndicatorSpiStatus(spi: number | null | undefined): IndicatorSpiStatus {
  if (spi === null || spi === undefined || !Number.isFinite(spi)) return "unavailable";
  if (spi >= 1) return "optimal";
  if (spi >= 0.8) return "warning";
  return "critical";
}
