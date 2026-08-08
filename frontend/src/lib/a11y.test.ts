import { describe, it, expect, vi } from "vitest";
import { onActivateKey } from "./a11y";

function fakeEvent(key: string) {
  return {
    key,
    preventDefault: vi.fn(),
  } as unknown as React.KeyboardEvent;
}

describe("a11y — onActivateKey", () => {
  it("Enter → dispara handler + preventDefault", () => {
    const handler = vi.fn();
    const fn = onActivateKey(handler);
    const ev = fakeEvent("Enter");
    fn(ev);
    expect(handler).toHaveBeenCalledTimes(1);
    expect(ev.preventDefault).toHaveBeenCalled();
  });
  it("Space (' ') → dispara handler + preventDefault", () => {
    const handler = vi.fn();
    const fn = onActivateKey(handler);
    const ev = fakeEvent(" ");
    fn(ev);
    expect(handler).toHaveBeenCalledTimes(1);
    expect(ev.preventDefault).toHaveBeenCalled();
  });
  it.each(["Tab", "Escape", "ArrowDown", "a", "Shift"])(
    "tecla no-activadora %s → no dispara ni previene",
    (key) => {
      const handler = vi.fn();
      const fn = onActivateKey(handler);
      const ev = fakeEvent(key);
      fn(ev);
      expect(handler).not.toHaveBeenCalled();
      expect((ev as unknown as { preventDefault: ReturnType<typeof vi.fn> }).preventDefault).not.toHaveBeenCalled();
    },
  );
  it("devuelve una función nueva cada vez (no memoizada)", () => {
    const h = vi.fn();
    const fn1 = onActivateKey(h);
    const fn2 = onActivateKey(h);
    expect(fn1).not.toBe(fn2);
  });
});
