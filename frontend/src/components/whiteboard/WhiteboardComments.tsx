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
        <div className="absolute right-4 top-20 z-50 w-80 rounded-xl border border-slate-200 bg-white shadow-2xl flex flex-col max-h-[60vh]">
            <div className="flex items-center justify-between p-4 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                    <MessageSquare className="w-5 h-5 text-slate-500" />
                    <h3 className="font-semibold text-slate-800">Comentarios</h3>
                </div>
                <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
                    <X className="w-5 h-5" />
                </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {comments.length === 0 ? (
                    <div className="text-center text-slate-500 text-sm">No hay comentarios aún.</div>
                ) : (
                    comments.map(c => (
                        <div key={c.id} className="bg-slate-50 rounded-lg p-3">
                            <div className="flex justify-between items-baseline mb-1">
                                <span className="font-semibold text-sm">{c.author}</span>
                                <span className="text-xs text-slate-400">{new Date(c.timestamp).toLocaleTimeString()}</span>
                            </div>
                            <p className="text-sm text-slate-700">{c.text}</p>
                        </div>
                    ))
                )}
            </div>
            
            <form onSubmit={handleSubmit} className="p-4 border-t border-slate-100">
                <div className="flex space-x-2">
                    <input 
                        type="text" 
                        value={text}
                        onChange={e => setText(e.target.value)}
                        placeholder="Escribe un comentario..."
                        className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button 
                        type="submit"
                        disabled={!text.trim()}
                        className="bg-blue-600 text-white rounded-lg p-2 hover:bg-blue-700 disabled:opacity-50"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
            </form>
        </div>
    );
}
