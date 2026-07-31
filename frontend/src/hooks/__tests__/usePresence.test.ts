import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { usePresence } from "../usePresence";

// Mock WebSocket class for vitest environment
class MockWebSocket {
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((error: unknown) => void) | null = null;
  onclose: (() => void) | null = null;
  closed = false;

  static instances: MockWebSocket[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  close() {
    this.closed = true;
    if (this.onclose) {
      this.onclose();
    }
  }

  // Helper for test triggers
  triggerOpen() {
    if (this.onopen) this.onopen();
  }

  triggerMessage(data: unknown) {
    if (this.onmessage) {
      this.onmessage({ data: typeof data === "string" ? data : JSON.stringify(data) });
    }
  }

  triggerError(err: unknown) {
    if (this.onerror) this.onerror(err);
  }

  triggerClose() {
    if (this.onclose) this.onclose();
  }
}

describe("usePresence Hook", () => {
  const originalWebSocket = global.WebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.instances = [];
    global.WebSocket = MockWebSocket as unknown as typeof WebSocket;
  });

  afterEach(() => {
    global.WebSocket = originalWebSocket;
    vi.useRealTimers();
  });

  it("returns empty presenceUsers and isConnected false when siteKey or slug is missing", () => {
    const { result } = renderHook(() =>
      usePresence({ siteKey: null, slug: null })
    );

    expect(result.current.presenceUsers).toEqual([]);
    expect(result.current.isConnected).toBe(false);
    expect(MockWebSocket.instances.length).toBe(0);
  });

  it("establishes WebSocket connection with correct URL and query token", () => {
    const { result } = renderHook(() =>
      usePresence({
        siteKey: "main",
        slug: "home",
        token: "user-token-123",
      })
    );

    expect(MockWebSocket.instances.length).toBe(1);
    const socket = MockWebSocket.instances[0];
    expect(socket.url).toContain("/api/cms/v2/ws/presence/main/home?token=user-token-123");
    expect(result.current.isConnected).toBe(false);

    // Trigger open
    act(() => {
      socket.triggerOpen();
    });
    expect(result.current.isConnected).toBe(true);
  });

  it("parses presence_update message and updates presenceUsers state", () => {
    const { result } = renderHook(() =>
      usePresence({ siteKey: "main", slug: "home", token: "tok" })
    );

    const socket = MockWebSocket.instances[0];
    act(() => {
      socket.triggerOpen();
    });

    const mockPayload = {
      type: "presence_update",
      presence_users: [
        { id: "usr-1", name: "Ana Perez", color: "#3B82F6", initials: "AP" },
        { id: "usr-2", name: "Bruno Diaz", color: "#10B981", initials: "BD" },
      ],
    };

    act(() => {
      socket.triggerMessage(mockPayload);
    });

    expect(result.current.presenceUsers).toHaveLength(2);
    expect(result.current.presenceUsers[0]).toEqual({
      id: "usr-1",
      name: "Ana Perez",
      color: "#3B82F6",
      initials: "AP",
      avatar_initials: "AP",
    });
    expect(result.current.presenceUsers[1].name).toBe("Bruno Diaz");
  });

  it("reconnects automatically on connection drop with backoff delays", () => {
    renderHook(() =>
      usePresence({ siteKey: "main", slug: "home", token: "tok" })
    );

    expect(MockWebSocket.instances.length).toBe(1);
    const socket1 = MockWebSocket.instances[0];

    // Trigger socket1 close -> should schedule reconnect after 1000ms
    act(() => {
      socket1.triggerClose();
    });
    expect(MockWebSocket.instances.length).toBe(1);

    // Advance timer 1000ms
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(MockWebSocket.instances.length).toBe(2);

    const socket2 = MockWebSocket.instances[1];
    // Trigger socket2 close -> next backoff delay is 2000ms
    act(() => {
      socket2.triggerClose();
    });
    expect(MockWebSocket.instances.length).toBe(2);

    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(MockWebSocket.instances.length).toBe(3);
  });

  it("cleans up WebSocket connection and timer on unmount", () => {
    const { unmount } = renderHook(() =>
      usePresence({ siteKey: "main", slug: "home", token: "tok" })
    );

    expect(MockWebSocket.instances.length).toBe(1);
    const socket = MockWebSocket.instances[0];

    unmount();
    expect(socket.closed).toBe(true);
  });
});
