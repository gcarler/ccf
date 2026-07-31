import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePresence } from "./usePresence";

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  url: string;
  readyState: number = 0; // CONNECTING
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  open() {
    this.readyState = 1; // OPEN
    if (this.onopen) {
      this.onopen(new Event("open"));
    }
  }

  emitMessage(data: unknown) {
    if (this.onmessage) {
      this.onmessage(
        new MessageEvent("message", {
          data: typeof data === "string" ? data : JSON.stringify(data),
        })
      );
    }
  }

  emitError() {
    if (this.onerror) {
      this.onerror(new Event("error"));
    }
  }

  close() {
    this.readyState = 3; // CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent("close"));
    }
  }
}

describe("usePresence Hook", () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("should not connect when siteKey or slug is missing", () => {
    const { result } = renderHook(() =>
      usePresence({ siteKey: null, slug: "home", token: "jwt-token" })
    );

    expect(result.current.isConnected).toBe(false);
    expect(result.current.presenceUsers).toEqual([]);
    expect(MockWebSocket.instances.length).toBe(0);
  });

  it("should open WebSocket connection with JWT token and subscribe to room (siteKey, slug)", () => {
    const { result } = renderHook(() =>
      usePresence({ siteKey: "main", slug: "home-page", token: "jwt-12345" })
    );

    expect(MockWebSocket.instances.length).toBe(1);
    const ws = MockWebSocket.instances[0];
    expect(ws.url).toContain("/api/cms/v2/ws/presence/main/home-page?token=jwt-12345");

    act(() => {
      ws.open();
    });

    expect(result.current.isConnected).toBe(true);
  });

  it("should correctly encode URI parameters for siteKey and slug room payload", () => {
    renderHook(() =>
      usePresence({
        siteKey: "site/with/slash",
        slug: "page with space & symbol",
        token: "test-token",
      })
    );

    expect(MockWebSocket.instances.length).toBe(1);
    const ws = MockWebSocket.instances[0];
    expect(ws.url).toContain(
      `/api/cms/v2/ws/presence/${encodeURIComponent("site/with/slash")}/${encodeURIComponent("page with space & symbol")}`
    );
  });

  it("should calculate user initials and construct token payload when fallback user object is provided", () => {
    renderHook(() =>
      usePresence({
        siteKey: "main",
        slug: "dashboard",
        token: null,
        user: {
          id: "usr-99",
          nombre_completo: "Carlos Gomez",
          avatar_initials: "CG",
          color: "#10B981",
        },
      })
    );

    expect(MockWebSocket.instances.length).toBe(1);
    const ws = MockWebSocket.instances[0];
    const urlObj = new URL(ws.url, "http://localhost:8000");
    const tokenParam = urlObj.searchParams.get("token");
    expect(tokenParam).not.toBeNull();

    const parsedToken = JSON.parse(tokenParam!);
    expect(parsedToken.id).toBe("usr-99");
    expect(parsedToken.name).toBe("Carlos Gomez");
    expect(parsedToken.initials).toBe("CG");
    expect(parsedToken.color).toBe("#10B981");
  });

  it("should update active users avatar state on incoming WebSocket presence broadcast message", () => {
    const { result } = renderHook(() =>
      usePresence({ siteKey: "main", slug: "home", token: "jwt-token" })
    );

    const ws = MockWebSocket.instances[0];

    act(() => {
      ws.open();
    });

    // 1. Array format
    act(() => {
      ws.emitMessage([
        {
          id: "u1",
          name: "Maria Lopez",
          color: "#EF4444",
          initials: "ML",
        },
        {
          id: "u2",
          name: "Roberto Sanchez",
          color: "#3B82F6",
          // missing initials -> should fallback to first 2 letters uppercase "RO"
        },
      ]);
    });

    expect(result.current.presenceUsers).toEqual([
      {
        id: "u1",
        name: "Maria Lopez",
        color: "#EF4444",
        initials: "ML",
        avatar_initials: "ML",
      },
      {
        id: "u2",
        name: "Roberto Sanchez",
        color: "#3B82F6",
        initials: "RO",
        avatar_initials: "RO",
      },
    ]);

    // 2. Object with presence_users format
    act(() => {
      ws.emitMessage({
        presence_users: [
          {
            auth_user_id: "u3",
            full_name: "Elena Diaz",
            avatar_initials: "ED",
            color: "#8B5CF6",
          },
        ],
      });
    });

    expect(result.current.presenceUsers).toEqual([
      {
        id: "u3",
        name: "Elena Diaz",
        color: "#8B5CF6",
        initials: "ED",
        avatar_initials: "ED",
      },
    ]);

    // 3. Object with users format
    act(() => {
      ws.emitMessage({
        users: [
          {
            identifier: "u4",
            nombre_completo: "Santiago Torres",
            color: "#F59E0B",
          },
        ],
      });
    });

    expect(result.current.presenceUsers).toEqual([
      {
        id: "u4",
        name: "Santiago Torres",
        color: "#F59E0B",
        initials: "SA",
        avatar_initials: "SA",
      },
    ]);
  });

  it("should handle exponential backoff reconnection logic (1000ms, 2000ms, 4000ms) on disconnect", () => {
    const { result } = renderHook(() =>
      usePresence({ siteKey: "main", slug: "home", token: "jwt-token" })
    );

    expect(MockWebSocket.instances.length).toBe(1);
    const ws1 = MockWebSocket.instances[0];

    act(() => {
      ws1.open();
    });
    expect(result.current.isConnected).toBe(true);

    // First disconnect -> schedules reconnect in 1000ms
    act(() => {
      ws1.close();
    });
    expect(result.current.isConnected).toBe(false);
    expect(MockWebSocket.instances.length).toBe(1);

    // Fast-forward 999ms -> not reconnected yet
    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(MockWebSocket.instances.length).toBe(1);

    // Advance 1ms (total 1000ms) -> reconnects
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(MockWebSocket.instances.length).toBe(2);
    const ws2 = MockWebSocket.instances[1];

    // Second disconnect -> schedules reconnect in 2000ms
    act(() => {
      ws2.close();
    });
    expect(MockWebSocket.instances.length).toBe(2);

    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(MockWebSocket.instances.length).toBe(3);
    const ws3 = MockWebSocket.instances[2];

    // Third disconnect -> schedules reconnect in 4000ms
    act(() => {
      ws3.close();
    });
    expect(MockWebSocket.instances.length).toBe(3);

    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(MockWebSocket.instances.length).toBe(4);
    const ws4 = MockWebSocket.instances[3];

    // Fourth disconnect -> capped at 4000ms
    act(() => {
      ws4.close();
    });
    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(MockWebSocket.instances.length).toBe(5);
  });

  it("should handle error state and clean up resources on unmount", () => {
    const { result, unmount } = renderHook(() =>
      usePresence({ siteKey: "main", slug: "home", token: "jwt-token" })
    );

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.open();
    });
    expect(result.current.isConnected).toBe(true);

    act(() => {
      ws.emitError();
    });
    expect(result.current.isConnected).toBe(false);

    unmount();
    expect(ws.readyState).toBe(3); // CLOSED
  });
});
