import React, { useState } from "react";
import type { FabricObject } from "fabric";
import { MessageSquare, X, Send } from "lucide-react";

export interface Comment {
    id: string;
    text: string;
    author: string;
    timestamp: number;
}

interface WhiteboardCommentsProps {
    object: FabricObject | null;
    onClose: () => void;
    onAddComment: (text: string) => void;
}

export function WhiteboardComments({ object, onClose, onAddComment }: WhiteboardCommentsProps) {
    const [text, setText] = useState("");

    if (!object) return null;

    const comments: Comment[] = (object as any).data?.comments || [];

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (text.trim()) {
            onAddComment(text);
            setText("");
        }
    };

    return (
        <div className="absolute right-4 top-28 z-50 w-80 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-2xl flex flex-col max-h-[60vh]">
            <div className="flex items-center justify-between p-4 border-b border-[hsl(var(--border))]">
                <div className="flex items-center space-x-2">
                    <MessageSquare className="w-5 h-5 text-[hsl(var(--text-secondary))]" />
                    <h3 className="font-semibold text-[hsl(var(--text-primary))]">Comentarios</h3>
                </div>
                <button onClick={onClose} className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]">
                    <X className="w-5 h-5" />
                </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {comments.length === 0 ? (
                    <div className="text-center text-[hsl(var(--text-secondary))] text-sm">No hay comentarios aún.</div>
                ) : (
                    comments.map(c => (
                        <div key={c.id} className="bg-[hsl(var(--surface-2))] rounded-lg p-3">
                            <div className="flex justify-between items-baseline mb-1">
                                <span className="font-semibold text-sm text-[hsl(var(--text-primary))]">{c.author}</span>
                                <span className="text-xs text-[hsl(var(--text-secondary))]">{new Date(c.timestamp).toLocaleTimeString()}</span>
                            </div>
                            <p className="text-sm text-[hsl(var(--text-secondary))]">{c.text}</p>
                        </div>
                    ))
                )}
            </div>
            
            <form onSubmit={handleSubmit} className="p-4 border-t border-[hsl(var(--border))]">
                <div className="flex space-x-2">
                    <input 
                        type="text" 
                        value={text}
                        onChange={e => setText(e.target.value)}
                        placeholder="Escribe un comentario..."
                        className="flex-1 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2]"
                    />
                    <button 
                        type="submit"
                        disabled={!text.trim()}
                        className="bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg p-2 hover:bg-[hsl(var(--primary))/0.9] disabled:opacity-50"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
            </form>
        </div>
    );
}
