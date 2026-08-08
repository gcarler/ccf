import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { notifyPreviewSync, subscribePreviewSync, type PreviewSyncMessage } from "./preview-sync";

describe("preview-sync", () => {
  beforeEach(() => {
    // Cada test arranca con un canal fresco: reset del módulo cacheado.
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("notifyPreviewSync posts a message with a numeric timestamp", () => {
    const postSpy = vi.spyOn(BroadcastChannel.prototype, "postMessage");
    notifyPreviewSync({ type: "section-saved", siteKey: "faro", slug: "landing", sectionId: "s1" });
    expect(postSpy).toHaveBeenCalledTimes(1);
    const payload = postSpy.mock.calls[0]?.[0] as PreviewSyncMessage;
    expect(payload.type).toBe("section-saved");
    expect(payload.siteKey).toBe("faro");
    expect(payload.slug).toBe("landing");
    expect(payload.sectionId).toBe("s1");
    expect(typeof payload.timestamp).toBe("number");
  });

  it("notifyPreviewSync works without sectionId (optional)", () => {
    const postSpy = vi.spyOn(BroadcastChannel.prototype, "postMessage");
    notifyPreviewSync({ type: "section-reordered", siteKey: "faro", slug: "landing" });
    const payload = postSpy.mock.calls[0]?.[0] as PreviewSyncMessage;
    expect(payload.type).toBe("section-reordered");
    expect(payload.sectionId).toBeUndefined();
  });

  it("subscribePreviewSync invokes the handler on message events and unsub unsubscribes", () => {
    const addSpy = vi.spyOn(BroadcastChannel.prototype, "addEventListener");
    const removeSpy = vi.spyOn(BroadcastChannel.prototype, "removeEventListener");

    const received: PreviewSyncMessage[] = [];
    const unsubscribe = subscribePreviewSync((msg) => received.push(msg));

    expect(addSpy).toHaveBeenCalledWith("message", expect.any(Function));
    const listener = addSpy.mock.calls[0]?.[1] as (e: MessageEvent<PreviewSyncMessage>) => void;

    const msg: PreviewSyncMessage = {
      type: "section-created",
      siteKey: "faro",
      slug: "landing",
      sectionId: "s2",
      timestamp: 123456,
    };
    listener(new MessageEvent("message", { data: msg }));
    expect(received).toEqual([msg]);

    unsubscribe();
    expect(removeSpy).toHaveBeenCalledWith("message", listener);
  });

  it("subscribePreviewSync returns a no-op unsubscribe when channel is unavailable", () => {
    const original = globalThis.BroadcastChannel;
    // @ts-expect-error simulate absence of BroadcastChannel (SSR-like)
    delete globalThis.BroadcastChannel;
    vi.resetModules();

    // Re-import after deleting the global so getChannel() sees no BroadcastChannel.
    return import("./preview-sync").then(({ subscribePreviewSync, notifyPreviewSync }) => {
      const handler = vi.fn();
      const unsub = subscribePreviewSync(handler);
      expect(typeof unsub).toBe("function");
      expect(() => unsub()).not.toThrow();
      // notify is also a no-op (no channel)
      expect(() => notifyPreviewSync({ type: "section-deleted", siteKey: "faro", slug: "landing" })).not.toThrow();
      expect(handler).not.toHaveBeenCalled();

      globalThis.BroadcastChannel = original;
    });
  });
});
