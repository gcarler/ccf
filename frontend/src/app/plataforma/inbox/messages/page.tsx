import { redirect } from "next/navigation";

/**
 * @deprecated This page is a redirect stub.
 *
 * Consolidation (2026-07-31): The inbox/messages route now redirects
 * to /plataforma/messages which is the canonical messaging page using
 * the new Conversation + ChatMessage system.
 *
 * All messaging functionality (DMs, @mentions, file attachments,
 * reply-to, WebSocket real-time) is now unified in one module.
 */
export default function InboxMessagesRedirect() {
    redirect("/plataforma/messages");
}
