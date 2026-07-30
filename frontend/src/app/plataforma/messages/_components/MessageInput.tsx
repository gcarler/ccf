"use client";

import { AvatarInitial } from '@/components/ui/AvatarInitial';
import { apiFetch } from '@/lib/http';
import type { DirectMessageItem } from '@/types/directMessages';
import { FileText, Loader2, Music, Paperclip, Send, Video, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { SearchedUser } from '../_hooks/useUserSearch';

interface MentionCandidate {
    query: string;
    start: number;
}

interface MessageInputProps {
    token: string | null;
    disabled: boolean;
    sending: boolean;
    replyTo: DirectMessageItem | null;
    onClearReply: () => void;
    onSend: (content: string, opts: { attachment?: File; replyTo?: DirectMessageItem; mentions: string[] }) => Promise<{ error: 'upload' | 'send' | null }>;
}

function getAttachmentType(file: File) {
    if (file.type.startsWith('image/')) return 'image';
    if (file.type === 'application/pdf') return 'pdf';
    if (file.type.startsWith('video/')) return 'video';
    if (file.type.startsWith('audio/')) return 'audio';
    return 'document';
}

export function MessageInput({
    token,
    disabled,
    sending,
    replyTo,
    onClearReply,
    onSend,
}: MessageInputProps) {
    const [input, setInput] = useState('');
    const [mentions, setMentions] = useState<SearchedUser[]>([]);
    const [mentionState, setMentionState] = useState<MentionCandidate | null>(null);
    const [mentionResults, setMentionResults] = useState<SearchedUser[]>([]);
    const [attachment, setAttachment] = useState<File | null>(null);
    const [attachmentPreviewUrl, setAttachmentPreviewUrl] = useState<string | null>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (!mentionState || !token) {
            setMentionResults([]);
            return;
        }
        const { query } = mentionState;
        if (query.length < 1) {
            setMentionResults([]);
            return;
        }
        const controller = new AbortController();
        const timer = setTimeout(() => {
            apiFetch<SearchedUser[]>(`/chat/users/search?q=${encodeURIComponent(query)}`, {
                token,
                signal: controller.signal,
            })
                .then((r) => setMentionResults(Array.isArray(r) ? r.slice(0, 6) : []))
                .catch(() => {});
        }, 150);
        return () => {
            clearTimeout(timer);
            controller.abort();
        };
    }, [mentionState, token]);

    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const val = e.target.value;
        setInput(val);
        const selectionStart = e.target.selectionStart;
        const textBeforeCursor = val.slice(0, selectionStart);
        const lastAt = textBeforeCursor.lastIndexOf('@');
        if (lastAt !== -1) {
            const query = textBeforeCursor.slice(lastAt + 1);
            if (!query.includes(' ')) {
                setMentionState({ query, start: lastAt });
                return;
            }
        }
        setMentionState(null);
    };

    // Auto-resize textarea
    useEffect(() => {
        const el = inputRef.current;
        if (!el) return;
        el.style.height = 'auto';
        el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
    }, [input]);

    const selectMention = (user: SearchedUser) => {
        if (!mentionState) return;
        const before = input.slice(0, mentionState.start);
        const after = input.slice(mentionState.start + 1 + mentionState.query.length);
        const newInput = `${before}@${user.username} ${after}`;
        setInput(newInput);
        setMentions((prev) => (prev.some((m) => m.id === user.id) ? prev : [...prev, user]));
        setMentionState(null);
        setMentionResults([]);
        inputRef.current?.focus();
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const allowedTypes = [
            'image/',
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats',
            'application/vnd.ms-excel',
            'text/plain',
            'text/csv',
            'video/mp4',
            'video/webm',
            'audio/mpeg',
            'audio/ogg',
            'audio/wav',
        ];
        const isAllowed = allowedTypes.some((t) => file.type.startsWith(t) || file.type.includes(t));
        if (!isAllowed) return;
        if (file.size > 25 * 1024 * 1024) return;
        setAttachment(file);
        setAttachmentPreviewUrl(URL.createObjectURL(file));
    };

    const clearAttachment = () => {
        if (attachmentPreviewUrl) URL.revokeObjectURL(attachmentPreviewUrl);
        setAttachment(null);
        setAttachmentPreviewUrl(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const handleSend = async () => {
        if (disabled || sending) return;
        const content = input.trim();
        if (!content && !attachment) return;
        const mentionIds = mentions.map((m) => m.id);
        const result = await onSend(content, { attachment: attachment || undefined, replyTo: replyTo || undefined, mentions: mentionIds });
        if (result.error === null) {
            setInput('');
            setMentions([]);
            if (attachment) clearAttachment();
        }
    };

    const type = attachment ? getAttachmentType(attachment) : null;

    return (
        <div className="border-t border-[hsl(var(--border))] dark:border-white/[0.05] p-2 md:p-3 bg-[hsl(var(--bg-primary))] dark:bg-[#141517] relative">
            {replyTo && (
                <div className="mx-2 mb-1 flex items-center gap-2 px-3 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg border-l-2 border-[hsl(var(--primary))]">
                    <div className="flex-1 min-w-0">
                        <p className="text-2xs font-bold text-[hsl(var(--primary))]">Respondiendo a {replyTo.sender_name}</p>
                        <p className="text-xs text-[hsl(var(--text-secondary))] truncate">{replyTo.content || '📎 Adjunto'}</p>
                    </div>
                    <button onClick={onClearReply} className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger))] transition-colors">
                        <X size={13} />
                    </button>
                </div>
            )}

            {attachment && attachmentPreviewUrl && (
                <div className="mx-2 mb-1 flex items-center gap-2 px-3 py-2 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg">
                    {type === 'image' ? (
                        <img src={attachmentPreviewUrl} alt="Preview" className="h-12 w-12 rounded-md object-cover" />
                    ) : (
                        <div className="h-10 w-10 rounded-md bg-[hsl(var(--primary)/0.1)] flex items-center justify-center">
                            {type === 'pdf' ? <FileText size={18} className="text-[hsl(var(--danger))]" />
                            : type === 'video' ? <Video size={18} className="text-[hsl(var(--info))]" />
                            : type === 'audio' ? <Music size={18} className="text-[hsl(var(--success))]" />
                            : <Paperclip size={18} className="text-[hsl(var(--primary))]" />}
                        </div>
                    )}
                    <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-[hsl(var(--text-primary))] truncate">{attachment.name}</p>
                        <p className="text-2xs text-[hsl(var(--text-secondary))]">{(attachment.size / 1024).toFixed(0)} KB</p>
                    </div>
                    <button onClick={clearAttachment} className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger))] transition-colors">
                        <X size={13} />
                    </button>
                </div>
            )}

            {mentionResults.length > 0 && mentionState && (
                <div className="absolute bottom-[calc(100%+0.5rem)] left-2 right-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1d] shadow-2xl overflow-hidden z-50">
                    {mentionResults.map((u) => (
                        <button key={u.id} onClick={() => selectMention(u)} className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors">
                            <AvatarInitial name={u.username} size="sm" />
                            <div className="text-left flex-1 min-w-0">
                                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] truncate">{u.username}</p>
                                <p className="text-2xs text-[hsl(var(--text-secondary))] truncate">{u.email}</p>
                            </div>
                        </button>
                    ))}
                </div>
            )}

            <div className="flex items-end gap-2">
                <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={disabled || sending}
                    title="Adjuntar archivo"
                    className="size-9 rounded-xl flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all shrink-0"
                >
                    <Paperclip size={18} />
                </button>
                <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={handleFileSelect}
                    accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.csv,video/mp4,video/webm,audio/mpeg,audio/ogg,audio/wav"
                />
                <div className="flex-1 flex items-center gap-2 px-3 py-2 bg-[hsl(var(--surface-1))] dark:bg-white/[0.05] border border-[hsl(var(--border))] dark:border-white/10 rounded-xl focus-within:ring-2 focus-within:ring-[hsl(var(--primary))]/20 transition-all">
                    <textarea
                        ref={inputRef}
                        rows={1}
                        value={input}
                        onChange={handleInputChange}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSend();
                            }
                            if (e.key === 'Escape') setMentionState(null);
                        }}
                        disabled={disabled || sending}
                        placeholder={replyTo ? `Responder a ${replyTo.sender_name}...` : 'Escribe un mensaje... (@ para mencionar)'}
                        aria-label="Escribe un mensaje"
                        className="flex-1 text-sm bg-transparent outline-none text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] min-w-0 resize-none max-h-40 disabled:opacity-50"
                    />
                </div>
                <button
                    onClick={handleSend}
                    disabled={(!input.trim() && !attachment) || disabled || sending}
                    aria-label="Enviar mensaje"
                    className="size-9 rounded-xl bg-[hsl(var(--primary))] text-white flex items-center justify-center hover:bg-[hsl(var(--primary))] disabled:opacity-30 disabled:cursor-not-allowed active:scale-95 transition-all shadow-sm shrink-0"
                >
                    {sending ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                </button>
            </div>
        </div>
    );
}
