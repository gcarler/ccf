import { describe, expect, it } from "vitest";

import { getIndicatorSpiStatus } from "./indicators";

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
