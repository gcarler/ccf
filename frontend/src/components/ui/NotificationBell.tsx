"use client";

import { Bell } from "lucide-react";
import { useNotifications } from "@/hooks/useNotifications";
import { useRouter } from "next/navigation";

interface NotificationBellProps {
    /** Override click behaviour. Defaults to navigating to /plataforma/community/notifications. */
    onClick?: () => void;
}

export default function NotificationBell({ onClick }: NotificationBellProps) {
    const router = useRouter();
    const { notifications } = useNotifications();

    const unread = notifications.filter((n) => !n.read).length;

    const handleClick = onClick ?? (() => router.push("/plataforma/community/notifications"));

    return (
        <button
            onClick={handleClick}
            className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] relative rounded-md hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all"
            aria-label={`Notificaciones${unread > 0 ? ` (${unread} sin leer)` : ""}`}
            title={`Notificaciones${unread > 0 ? ` — ${unread} sin leer` : ""}`}
        >
            <Bell size={14} />
            {unread > 0 && (
                <span className="absolute -top-0.5 -right-0.5 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-[hsl(var(--danger))] text-white text-2xs font-bold ring-2 ring-[hsl(var(--bg-primary))] dark:ring-[hsl(var(--bg-primary))]">
                    {unread > 99 ? "99+" : unread}
                </span>
            )}
        </button>
    );
}
