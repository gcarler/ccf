"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { useWorkspaceSocket } from "@/hooks/useWorkspaceSocket";
import { MessageCircle, Send, Plus, ChevronLeft, Users } from "lucide-react";
import type { ConversationRead, DirectMessageItem } from "@/types/directMessages";

export default function MessagesPage() {
  const { token, user } = useAuth();
  const [conversations, setConversations] = useState<ConversationRead[]>([]);
  const [activeConv, setActiveConv] = useState<ConversationRead | null>(null);
  const [messages, setMessages] = useState<DirectMessageItem[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [showSidebar, setShowSidebar] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const userId = user?.id;

  // Load conversations
  useEffect(() => {
    if (!token) return;
    apiFetch<ConversationRead[]>("/chat/conversations", { token })
      .then((data) => {
        if (Array.isArray(data)) setConversations(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token]);

  // Load messages for active conversation
  useEffect(() => {
    if (!token || !activeConv) return;
    setMessages([]);
    apiFetch<DirectMessageItem[]>(
      `/chat/conversations/${activeConv.id}/messages`,
      { token, query: { limit: "100" } }
    )
      .then((data) => {
        if (Array.isArray(data)) setMessages(data.reverse());
      })
      .catch(() => {});
    // Mark as read
    apiFetch(`/chat/conversations/${activeConv.id}/read`, {
      method: "POST",
      token,
    }).catch(() => {});
  }, [activeConv?.id, token]);

  // WebSocket real-time
  const handleSocketEvent = useCallback(
    (payload: any) => {
      if (payload?.event === "direct_message" && payload?.conversation_id === activeConv?.id) {
        setMessages((prev) => [...prev, payload.message]);
        // Update conversation preview
        setConversations((prev) =>
          prev.map((c) =>
            c.id === activeConv?.id
              ? {
                  ...c,
                  last_message_content: payload.message.content,
                  last_message_at: payload.message.created_at,
                  last_sender_id: payload.message.sender_id,
                  unread_count: 0,
                }
              : c
          )
        );
      } else if (payload?.event === "direct_message") {
        // Update the conversation list
        setConversations((prev) =>
          prev.map((c) =>
            c.id === payload.conversation_id
              ? {
                  ...c,
                  last_message_content: payload.message.content,
                  last_message_at: payload.message.created_at,
                  last_sender_id: payload.message.sender_id,
                }
              : c
          )
        );
      }
    },
    [activeConv?.id]
  );

  useWorkspaceSocket({
    rooms: activeConv ? [`dm_${activeConv.id}`] : [],
    enabled: !!token && !!activeConv,
    onEvent: handleSocketEvent,
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !token || !activeConv) return;
    try {
      const msg = await apiFetch<DirectMessageItem>(
        `/chat/conversations/${activeConv.id}/messages`,
        { method: "POST", token, body: { content: input.trim() } }
      );
      setMessages((prev) => [...prev, msg]);
      setInput("");
    } catch (err) {
      console.error("Failed to send", err);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getOtherParticipant = (conv: ConversationRead) => {
    return conv.participants.find((p) => p.user_id !== userId);
  };

  return (
    <div className="flex h-full bg-white dark:bg-[#1e1f21] font-display overflow-hidden">
      {/* Sidebar — conversation list */}
      <div
        className={`${
          showSidebar ? "flex" : "hidden"
        } md:flex flex-col w-72 border-r border-gray-200 dark:border-gray-700 shrink-0`}
      >
        <div className="p-3 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
            <MessageCircle className="w-4 h-4" />
            Mensajes
          </h2>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-sm text-gray-400 text-center">Cargando...</div>
          ) : conversations.length === 0 ? (
            <div className="p-4 text-sm text-gray-400 text-center">
              No hay conversaciones
            </div>
          ) : (
            conversations.map((conv) => {
              const other = getOtherParticipant(conv);
              return (
                <button
                  key={conv.id}
                  onClick={() => {
                    setActiveConv(conv);
                    setShowSidebar(false);
                  }}
                  className={`w-full text-left px-3 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors border-b border-gray-100 dark:border-gray-800 ${
                    activeConv?.id === conv.id
                      ? "bg-blue-50 dark:bg-blue-900/20"
                      : ""
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-800 flex items-center justify-center shrink-0">
                      <Users className="w-4 h-4 text-blue-600 dark:text-blue-300" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {other?.username || "Usuario"}
                      </p>
                      {conv.last_message_content && (
                        <p className="text-xs text-gray-500 truncate mt-0.5">
                          {conv.last_message_content}
                        </p>
                      )}
                    </div>
                    {conv.unread_count > 0 && (
                      <span className="bg-blue-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
                        {conv.unread_count}
                      </span>
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Main — message thread */}
      <div
        className={`${
          !showSidebar ? "flex" : "hidden"
        } md:flex flex-col flex-1`}
      >
        {!activeConv ? (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400 gap-2">
            <MessageCircle className="w-12 h-12 opacity-40" />
            <p className="text-sm">Selecciona una conversación</p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setShowSidebar(true)}
                className="md:hidden p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <div className="w-7 h-7 rounded-full bg-blue-100 dark:bg-blue-800 flex items-center justify-center">
                <Users className="w-3.5 h-3.5 text-blue-600 dark:text-blue-300" />
              </div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {getOtherParticipant(activeConv)?.username || "Usuario"}
              </span>
            </div>

            {/* Messages */}
            <div
              ref={scrollRef}
              className="flex-1 overflow-y-auto p-4 space-y-3"
            >
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-2">
                  <MessageCircle className="w-8 h-8 opacity-40" />
                  <p className="text-sm">No hay mensajes aún</p>
                </div>
              ) : (
                messages.map((msg) => {
                  const isOwn = msg.sender_id === userId;
                  return (
                    <div
                      key={msg.id}
                      className={`flex ${
                        isOwn ? "justify-end" : "justify-start"
                      }`}
                    >
                      <div
                        className={`max-w-[75%] rounded-2xl px-4 py-2 ${
                          isOwn
                            ? "bg-blue-500 text-white rounded-br-md"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-md"
                        }`}
                      >
                        {!isOwn && (
                          <p className="text-xs font-semibold mb-1 opacity-70">
                            {msg.sender_name}
                          </p>
                        )}
                        <p className="text-sm whitespace-pre-wrap break-words">
                          {msg.content}
                        </p>
                        <p
                          className={`text-[10px] mt-1 ${
                            isOwn ? "text-blue-200" : "text-gray-400"
                          }`}
                        >
                          {new Date(msg.created_at).toLocaleTimeString("es-CO", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Input */}
            <div className="border-t border-gray-200 dark:border-gray-700 p-3">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Escribe un mensaje..."
                  className="flex-1 px-4 py-2 rounded-full border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 dark:text-white"
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim()}
                  className="p-2 rounded-full bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
