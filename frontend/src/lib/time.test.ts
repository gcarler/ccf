import { describe, it, expect } from "vitest";
import { parseAndValidateTime } from "./time";

describe("time — parseAndValidateTime (24h)", () => {
  it.each([
    ["0:00", { valid: true, minutes: 0, normalized: "00:00" }],
    ["00:00", { valid: true, minutes: 0, normalized: "00:00" }],
    ["9:30", { valid: true, minutes: 570, normalized: "09:30" }],
    ["09:30", { valid: true, minutes: 570, normalized: "09:30" }],
    ["23:59", { valid: true, minutes: 1439, normalized: "23:59" }],
    ["7:05", { valid: true, minutes: 425, normalized: "07:05" }],
  ])("24h válido: '%s'", (input, expected) => {
    expect(parseAndValidateTime(input)).toEqual(expected);
  });

  it.each(["24:00", "25:00", "12:60", "12:99", "-1:00", "abc"])("24h inválido: '%s'", (input) => {
    const out = parseAndValidateTime(input);
    if (input === "abc") expect(out.valid).toBe(false);
    else expect(out.valid).toBe(false);
  });
});

describe("time — parseAndValidateTime (AM/PM)", () => {
  it.each([
    ["12:00 AM", { valid: true, minutes: 0, normalized: "00:00" }],
    ["12:00 am", { valid: true, minutes: 0, normalized: "00:00" }],
    ["12:00 a.m.", { valid: true, minutes: 0, normalized: "00:00" }],
    ["12:00 a. m.", { valid: true, minutes: 0, normalized: "00:00" }],
    ["1:30 PM", { valid: true, minutes: 810, normalized: "13:30" }],
    ["1:30 pm", { valid: true, minutes: 810, normalized: "13:30" }],
    ["1:30 p.m.", { valid: true, minutes: 810, normalized: "13:30" }],
    ["11:59 PM", { valid: true, minutes: 1439, normalized: "23:59" }],
    ["12:30 PM", { valid: true, minutes: 750, normalized: "12:30" }],
    ["7:00 AM", { valid: true, minutes: 420, normalized: "07:00" }],
  ])("AM/PM válido: '%s'", (input, expected) => {
    expect(parseAndValidateTime(input)).toEqual(expected);
  });

  it.each(["13:00 PM", "0:00 AM", "12:60 PM", "10:00 XM"])(
    "AM/PM inválido: '%s'",
    (input) => {
      expect(parseAndValidateTime(input).valid).toBe(false);
    },
  );
});

describe("time — parseAndValidateTime (edge cases)", () => {
  it("string vacío → invalid", () => {
    expect(parseAndValidateTime("")).toEqual({ valid: false, minutes: 0, normalized: "" });
  });
  it("trim y colapso de espacios", () => {
    expect(parseAndValidateTime("  9:30  ")).toEqual({
      valid: true,
      minutes: 570,
      normalized: "09:30",
    });
  });
  it("case-insensitive (mayúsculas)", () => {
    expect(parseAndValidateTime("1:30 Pm")).toEqual({
      valid: true,
      minutes: 810,
      normalized: "13:30",
    });
  });
  it("formato no reconocido → invalid", () => {
    expect(parseAndValidateTime("mediodía").valid).toBe(false);
    expect(parseAndValidateTime("25:30").valid).toBe(false);
  });
});
