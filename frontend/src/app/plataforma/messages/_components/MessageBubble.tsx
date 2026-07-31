"use client";

import { AvatarInitial } from '@/components/ui/AvatarInitial';
import { sanitizeText } from '@/lib/text';
import type { DirectMessageItem } from '@/types/directMessages';
import clsx from 'clsx';
import { FileText, Reply } from 'lucide-react';

interface MessageBubbleProps {
    message: DirectMessageItem;
    isOwn: boolean;
    showSender: boolean;
    onReply: (msg: DirectMessageItem) => void;
}

function MentionSpan({ children }: { children: React.ReactNode }) {
    return (
        <span className="font-bold text-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.1)] px-0.5 rounded">
            {children}
        </span>
    );
}

function parseContent(content: string): Array<{ type: 'text' | 'mention'; value: string }> {
    // A-11: unified mention regex with MessageInput's detection logic.
    // A mention is `@username` where the char before `@` is start-of-string
    // or whitespace (same word-boundary rule used in the composer).
    const tokens: Array<{ type: 'text' | 'mention'; value: string }> = [];
    const regex = /@\S+/g;
    let lastIndex = 0;
    content.replace(regex, (match, offset) => {
        const isAtStart = offset === 0;
        const prevChar = content[offset - 1];
        if (isAtStart || /\s/.test(prevChar)) {
            if (offset > lastIndex) {
                tokens.push({ type: 'text', value: content.slice(lastIndex, offset) });
            }
            tokens.push({ type: 'mention', value: match });
            lastIndex = offset + match.length;
        }
        return match;
    });
    if (lastIndex < content.length) {
        tokens.push({ type: 'text', value: content.slice(lastIndex) });
    }
    return tokens;
}

function renderContent(content: string) {
    const tokens = parseContent(content);
    return (
        <p className="whitespace-pre-wrap break-words">
            {tokens.map((token, i) =>
                token.type === 'mention' ? <MentionSpan key={i}>{token.value}</MentionSpan> : <span key={i}>{sanitizeText(token.value)}</span>
            )}
        </p>
    );
}

export function MessageBubble({ message, isOwn, showSender, onReply }: MessageBubbleProps) {
    const time = new Date(message.created_at).toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
    });

    return (
        <div className={clsx('flex group', isOwn ? 'justify-end' : 'justify-start')}>
            {!isOwn && (
                <button
                    onClick={() => onReply(message)}
                    className="self-end mb-1 mr-1 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-md hover:bg-[hsl(var(--surface-2))]"
                    aria-label="Responder"
                >
                    <Reply size={13} className="text-[hsl(var(--text-secondary))]" />
                </button>
            )}
            {!isOwn && (
                <div className="mr-2 mt-1 shrink-0 hidden xs:block">
                    <AvatarInitial name={message.sender_name || 'U'} size="sm" />
                </div>
            )}
            <div className={clsx('space-y-0.5', isOwn ? 'max-w-[80%] md:max-w-[68%]' : 'max-w-[85%] md:max-w-[68%]')}>
                {!isOwn && showSender && (
                    <p className="text-2xs font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] px-1">
                        {message.sender_name}
                    </p>
                )}
                <div
                    className={clsx(
                        'px-3 md:px-3.5 py-2 rounded-2xl text-base md:text-sm leading-relaxed',
                        isOwn
                            ? 'bg-[hsl(var(--primary))] text-white rounded-br-md'
                            : 'bg-[hsl(var(--bg-primary))] dark:bg-white/[0.07] border border-[hsl(var(--border))] dark:border-white/[0.06] text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] rounded-bl-md shadow-sm'
                    )}
                >
                    {message.reply_preview && (
                        <div className="mb-1 px-2 py-1 rounded-md bg-black/5 dark:bg-white/5 border-l-2 border-[hsl(var(--primary))] text-2xs text-[hsl(var(--text-secondary))]">
                            <span className="font-bold">{message.reply_preview.sender_name}: </span>
                            {message.reply_preview.content || '📎 Adjunto'}
                        </div>
                    )}
                    {renderContent(message.content)}
                    {message.attachment_url && (
                        <div className="mt-1">
                            {message.attachment_type === 'image' ? (
                                <img
                                    src={message.attachment_url}
                                    alt={message.attachment_name || 'imagen'}
                                    className="max-w-[240px] max-h-[240px] rounded-xl object-cover cursor-pointer"
                                    onClick={() => window.open(message.attachment_url!, '_blank')}
                                />
                            ) : (
                                <a
                                    href={message.attachment_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-black/5 dark:bg-white/10 hover:bg-black/10 transition-colors"
                                >
                                    <FileText size={16} />
                                    <span className="text-xs font-medium truncate max-w-[180px]">
                                        {message.attachment_name || 'archivo'}
                                    </span>
                                </a>
                            )}
                        </div>
                    )}
                </div>
                <div className={clsx('flex items-center gap-1', isOwn ? 'justify-end pr-1' : 'pl-1')}>
                    <span className={clsx('text-2xs', isOwn ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-secondary))]')}>
                        {time}
                    </span>
                    {isOwn && <span className="text-2xs text-[hsl(var(--primary))]">{message.is_read ? '✓✓' : '✓'}</span>}
                </div>
            </div>
            {isOwn && (
                <button
                    onClick={() => onReply(message)}
                    className="self-end mb-1 ml-1 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-md hover:bg-[hsl(var(--surface-2))]"
                    aria-label="Responder"
                >
                    <Reply size={13} className="text-[hsl(var(--text-secondary))]" />
                </button>
            )}
        </div>
    );
}
