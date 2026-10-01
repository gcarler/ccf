import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import PushNotificationManager from "./PushNotificationManager";

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { apiFetch } from "@/lib/http";

describe("PushNotificationManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock browser APIs
    Object.defineProperty(window, "Notification", {
      value: {
        permission: "default",
        requestPermission: vi.fn().mockResolvedValue("granted"),
      },
      writable: true,
      configurable: true,
    });

    Object.defineProperty(navigator, "serviceWorker", {
      value: {
        register: vi.fn().mockResolvedValue({
          pushManager: {
            subscribe: vi.fn().mockResolvedValue({
              toJSON: () => ({
                endpoint: "https://fcm.googleapis.com/fcm/send/test-device",
                keys: {
                  p256dh: "test_p256dh",
                  auth: "test_auth",
                },
              }),
            }),
          },
        }),
        ready: Promise.resolve(),
      },
      writable: true,
      configurable: true,
    });

    Object.defineProperty(window, "PushManager", {
      value: {},
      writable: true,
      configurable: true,
    });
  });

  it("renders status banner and activation button when permission is default", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      subscriptions: [],
      count: 0,
    });

    render(<PushNotificationManager />);

    expect(screen.getByText(/Notificaciones Web Push \(VAPID\)/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Activar Ahora/i })).toBeInTheDocument();
  });

  it("renders registered devices list when subscriptions exist", async () => {
    Object.defineProperty(window, "Notification", {
      value: { permission: "granted" },
      writable: true,
      configurable: true,
    });

    vi.mocked(apiFetch).mockResolvedValueOnce({
      subscriptions: [
        {
          id: "sub-1",
          user_id: "user-1",
          endpoint: "https://fcm.googleapis.com/fcm/send/device-desktop",
          device_name: "Linux Desktop",
          created_at: new Date().toISOString(),
        },
      ],
      count: 1,
    });

    render(<PushNotificationManager />);

    await waitFor(() => {
      expect(screen.getByText("Linux Desktop")).toBeInTheDocument();
      expect(screen.getByText(/Dispositivos Registrados \(1\)/i)).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /Probar/i })).toBeInTheDocument();
  });

  it("calls test push endpoint when clicking test button", async () => {
    Object.defineProperty(window, "Notification", {
      value: { permission: "granted" },
      writable: true,
      configurable: true,
    });

    vi.mocked(apiFetch)
      .mockResolvedValueOnce({
        subscriptions: [
          {
            id: "sub-1",
            user_id: "user-1",
            endpoint: "https://fcm.googleapis.com/fcm/send/device-desktop",
            device_name: "Linux Desktop",
            created_at: new Date().toISOString(),
          },
        ],
        count: 1,
      })
      .mockResolvedValueOnce({
        status: "success",
        sent_count: 1,
      });

    render(<PushNotificationManager />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Probar/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Probar/i }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/messaging/push/test",
        expect.objectContaining({ method: "POST" })
      );
    });
  });
});
