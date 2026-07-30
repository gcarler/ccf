export interface ConversationRead {
  id: string;
  participants: ConversationParticipantRead[];
  last_message_content: string | null;
  last_message_at: string | null;
  last_sender_id: string | null;
  unread_count: number;
  created_at: string;
}

export interface ConversationParticipantRead {
  persona_id: string;
  username: string;
  last_read_at: string | null;
}

export interface DirectMessageItem {
    id: string;
    sender_id: string;
    sender_name: string;
    content: string;
    created_at: string;
    is_read: boolean;
    attachment_url?: string | null;
    attachment_type?: string | null;
    attachment_name?: string | null;
    attachment_size?: number | null;
    reply_to_id?: string | null;
    reply_preview?: { id: string; sender_name: string; content: string; attachment_type?: string | null } | null;
    mentions?: string[] | null;
}

export interface WsDirectMessageEvent {
  event: "direct_message";
  conversation_id: string;
  message: DirectMessageItem;
}

export interface WsRawEvent {
  event: string;
  [key: string]: unknown;
}

export type WsEvent = WsDirectMessageEvent | WsRawEvent;
