import { describe, expect, it } from "vitest";

import {
  computeEvmCompositeIndex,
  getCremaReadinessScore,
  getIndicatorCpiStatus,
  getIndicatorSpiStatus,
} from "./indicators";

describe("getIndicatorSpiStatus", () => {
  it("classifies zero as critical instead of treating it as a missing value", () => {
    expect(getIndicatorSpiStatus(0)).toBe("critical");
  });

  it("keeps the documented warning and optimal thresholds", () => {
    expect(getIndicatorSpiStatus(0.8)).toBe("warning");
    expect(getIndicatorSpiStatus(1)).toBe("optimal");
  });

  it("marks absent or non-finite SPI as unavailable", () => {
    expect(getIndicatorSpiStatus(null)).toBe("unavailable");
    expect(getIndicatorSpiStatus(undefined)).toBe("unavailable");
    expect(getIndicatorSpiStatus(Number.NaN)).toBe("unavailable");
  });
});

describe("getIndicatorCpiStatus", () => {
  it("evaluates CPI thresholds according to PMI §7.4", () => {
    expect(getIndicatorCpiStatus(1.05)).toBe("optimal");
    expect(getIndicatorCpiStatus(0.85)).toBe("warning");
    expect(getIndicatorCpiStatus(0.75)).toBe("critical");
    expect(getIndicatorCpiStatus(null)).toBe("unavailable");
    expect(getIndicatorCpiStatus(Number.POSITIVE_INFINITY)).toBe("unavailable");
  });
});

describe("computeEvmCompositeIndex", () => {
  it("computes Critical Ratio (CPI × SPI) rounded to 2 decimal places", () => {
    expect(computeEvmCompositeIndex(1.1, 0.9)).toBe(0.99);
    expect(computeEvmCompositeIndex(1.1, 0.95)).toBe(1.04);
    expect(computeEvmCompositeIndex(0, 1)).toBe(0);
  });

  it("returns null for missing, negative or non-finite inputs", () => {
    expect(computeEvmCompositeIndex(null, 1)).toBeNull();
    expect(computeEvmCompositeIndex(1, undefined)).toBeNull();
    expect(computeEvmCompositeIndex(-0.5, 1)).toBeNull();
    expect(computeEvmCompositeIndex(1, Number.NaN)).toBeNull();
  });
});

describe("getCremaReadinessScore", () => {
  it("computes passed criteria, percentage and compliance for CREMA flags", () => {
    expect(getCremaReadinessScore(null)).toEqual({
      passed: 0,
      total: 5,
      percentage: 0,
      isCompliant: false,
    });

    expect(
      getCremaReadinessScore({
        clear: true,
        relevant: true,
        economic: true,
        monitorable: false,
        adequate: false,
      }),
    ).toEqual({
      passed: 3,
      total: 5,
      percentage: 60,
      isCompliant: false,
    });

    expect(
      getCremaReadinessScore({
        clear: true,
        relevant: true,
        economic: true,
        monitorable: true,
        adequate: true,
      }),
    ).toEqual({
      passed: 5,
      total: 5,
      percentage: 100,
      isCompliant: true,
    });
  });
});

