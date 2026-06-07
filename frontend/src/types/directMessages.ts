export interface ConversationRead {
  id: number;
  participants: ConversationParticipantRead[];
  last_message_content: string | null;
  last_message_at: string | null;
  last_sender_id: string | null;
  unread_count: number;
  created_at: string;
}

export interface ConversationParticipantRead {
  user_id: string;
  username: string;
  last_read_at: string | null;
}

export interface DirectMessageItem {
  id: number;
  sender_id: string;
  sender_name: string;
  content: string;
  created_at: string;
  is_read: boolean;
}
