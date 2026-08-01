import { redirect } from 'next/navigation';

/**
 * @note This redirect exists for backward compatibility.
 * The canonical messaging page is now at /plataforma/messages.
 * 
 * Consolidation (2026-07-31): All messaging functionality has been
 * consolidated into the /plataforma/messages route which uses the
 * new Conversation + ChatMessage model with WebSocket support,
 * @mentions, file attachments, and reply-to functionality.
 */
export default function RedirectToMessages() {
    redirect('/plataforma/messages');
}
