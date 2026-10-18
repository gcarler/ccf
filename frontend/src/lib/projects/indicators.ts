export type IndicatorSpiStatus = "optimal" | "warning" | "critical" | "unavailable";

export function getIndicatorSpiStatus(spi: number | null | undefined): IndicatorSpiStatus {
  if (spi === null || spi === undefined || !Number.isFinite(spi)) return "unavailable";
  if (spi >= 1) return "optimal";
  if (spi >= 0.8) return "warning";
  return "critical";
}

export function getIndicatorCpiStatus(cpi: number | null | undefined): IndicatorSpiStatus {
  if (cpi === null || cpi === undefined || !Number.isFinite(cpi)) return "unavailable";
  if (cpi >= 1) return "optimal";
  if (cpi >= 0.8) return "warning";
  return "critical";
}

export function computeEvmCompositeIndex(
  cpi: number | null | undefined,
  spi: number | null | undefined,
): number | null {
  if (
    cpi === null ||
    cpi === undefined ||
    spi === null ||
    spi === undefined ||
    !Number.isFinite(cpi) ||
    !Number.isFinite(spi) ||
    cpi < 0 ||
    spi < 0
  ) {
    return null;
  }
  return Number((cpi * spi).toFixed(2));
}

export interface CremaFlags {
  clear?: boolean;
  relevant?: boolean;
  economic?: boolean;
  monitorable?: boolean;
  adequate?: boolean;
}

export function getCremaReadinessScore(flags: CremaFlags | null | undefined): {
  passed: number;
  total: 5;
  percentage: number;
  isCompliant: boolean;
} {
  if (!flags) {
    return { passed: 0, total: 5, percentage: 0, isCompliant: false };
  }
  const keys: Array<keyof CremaFlags> = [
    "clear",
    "relevant",
    "economic",
    "monitorable",
    "adequate",
  ];
  const passed = keys.filter((key) => Boolean(flags[key])).length;
  return {
    passed,
    total: 5,
    percentage: Math.round((passed / 5) * 100),
    isCompliant: passed === 5,
  };
}

