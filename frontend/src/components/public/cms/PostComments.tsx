"use client";

import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { MessageSquare, CornerDownRight, Send, X, Loader2 } from "lucide-react";
import { createPublicPostComment, getPublicPostComments } from "@/lib/cms/v2";
import { CmsPublicPostComment } from "@/types/cms-v2";

interface PostCommentsProps {
  postId: string;
}

export function PostComments({ postId }: PostCommentsProps) {
  const [comments, setComments] = useState<CmsPublicPostComment[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // New root comment form state
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Inline reply form state
  const [activeReplyId, setActiveReplyId] = useState<string | null>(null);
  const [replyName, setReplyName] = useState("");
  const [replyEmail, setReplyEmail] = useState("");
  const [replyContent, setReplyContent] = useState("");
  const [replySubmitting, setReplySubmitting] = useState(false);

  const fetchComments = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getPublicPostComments(postId);
      setComments(data);
    } catch (err: unknown) {
      console.error("Error fetching comments:", err);
    } finally {
      setLoading(false);
    }
  }, [postId]);

  useEffect(() => {
    if (postId) {
      fetchComments();
    }
  }, [fetchComments, postId]);

  const countTotalComments = (items: CmsPublicPostComment[]): number => {
    let count = items.length;
    for (const item of items) {
      if (item.replies && item.replies.length > 0) {
        count += item.replies.length;
      }
    }
    return count;
  };

  const totalCount = countTotalComments(comments);

  const handleCreateRootComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !content.trim()) {
      toast.error("Por favor completa todos los campos.");
      return;
    }
    setSubmitting(true);
    try {
      await createPublicPostComment(postId, {
        author_name: name.trim(),
        author_email: email.trim(),
        content: content.trim(),
      });
      toast.success("Comentario enviado con éxito. Pendiente de moderación.");
      setName("");
      setEmail("");
      setContent("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al enviar el comentario.";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateReply = async (parentId: string, e: React.FormEvent) => {
    e.preventDefault();
    if (!replyName.trim() || !replyEmail.trim() || !replyContent.trim()) {
      toast.error("Por favor completa todos los campos para responder.");
      return;
    }
    setReplySubmitting(true);
    try {
      await createPublicPostComment(postId, {
        author_name: replyName.trim(),
        author_email: replyEmail.trim(),
        content: replyContent.trim(),
        parent_id: parentId,
      });
      toast.success("Respuesta enviada con éxito. Pendiente de moderación.");
      setReplyName("");
      setReplyEmail("");
      setReplyContent("");
      setActiveReplyId(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al enviar la respuesta.";
      toast.error(msg);
    } finally {
      setReplySubmitting(false);
    }
  };

  return (
    <div className="w-full space-y-8 py-6" data-testid="post-comments-component">
      {/* Header Badge */}
      <div className="flex items-center gap-3 border-b border-[hsl(var(--border))] pb-4">
        <MessageSquare className="h-6 w-6 text-primary" />
        <h3 className="text-xl font-bold text-[hsl(var(--text-primary))]">Comentarios</h3>
        <span
          className="rounded-full bg-primary/10 px-3 py-0.5 text-xs font-semibold text-primary"
          data-testid="comments-count-badge"
        >
          {totalCount}
        </span>
      </div>

      {/* Main Comment Form */}
      <form onSubmit={handleCreateRootComment} className="space-y-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-5">
        <h4 className="text-sm font-semibold text-[hsl(var(--text-primary))]">Deja un comentario</h4>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-xs font-medium text-[hsl(var(--text-secondary))]">Nombre</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Tu nombre"
              className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[hsl(var(--text-secondary))]">Correo Electrónico</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="tu@email.com"
              className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-[hsl(var(--text-secondary))]">Comentario</label>
          <textarea
            required
            rows={3}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Escribe tu comentario aquí..."
            className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90 disabled:opacity-50"
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          Enviar Comentario
        </button>
      </form>

      {/* Comments List */}
      {loading ? (
        <div className="space-y-4" data-testid="comments-loading">
          <div className="h-16 animate-pulse rounded-lg bg-[hsl(var(--surface-3))]" />
          <div className="h-16 animate-pulse rounded-lg bg-[hsl(var(--surface-3))]" />
        </div>
      ) : comments.length === 0 ? (
        <div className="py-8 text-center text-sm text-[hsl(var(--text-secondary))]">
          No hay comentarios aprobados aún. ¡Sé el primero en comentar!
        </div>
      ) : (
        <div className="space-y-6" data-testid="comments-tree">
          {comments.map((comment) => (
            <div key={comment.id} className="space-y-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm">
              {/* Root Comment Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold text-xs">
                    {comment.author_name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h5 className="text-sm font-semibold text-[hsl(var(--text-primary))]">{comment.author_name}</h5>
                    <span className="text-2xs text-[hsl(var(--text-secondary))]">
                      {new Date(comment.created_at).toLocaleDateString("es-ES", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => {
                    if (activeReplyId === comment.id) {
                      setActiveReplyId(null);
                    } else {
                      setActiveReplyId(comment.id);
                      setReplyName("");
                      setReplyEmail("");
                      setReplyContent("");
                    }
                  }}
                  className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]"
                >
                  <CornerDownRight className="h-3.5 w-3.5" />
                  Responder
                </button>
              </div>

              {/* Comment Content */}
              <p className="text-sm text-[hsl(var(--text-primary))] whitespace-pre-wrap pl-10">
                {comment.content}
              </p>

              {/* Inline Reply Form */}
              {activeReplyId === comment.id && (
                <form
                  onSubmit={(e) => handleCreateReply(comment.id, e)}
                  className="mt-4 ml-10 space-y-3 rounded-lg border border-primary/20 bg-primary/5 p-4"
                  data-testid="inline-reply-form"
                >
                  <div className="flex items-center justify-between">
                    <h5 className="text-xs font-semibold text-primary">Responder a {comment.author_name}</h5>
                    <button
                      type="button"
                      onClick={() => setActiveReplyId(null)}
                      className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <input
                      type="text"
                      required
                      value={replyName}
                      onChange={(e) => setReplyName(e.target.value)}
                      placeholder="Tu nombre"
                      className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-1.5 text-xs text-[hsl(var(--text-primary))]"
                    />
                    <input
                      type="email"
                      required
                      value={replyEmail}
                      onChange={(e) => setReplyEmail(e.target.value)}
                      placeholder="Tu correo"
                      className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-1.5 text-xs text-[hsl(var(--text-primary))]"
                    />
                  </div>
                  <textarea
                    required
                    rows={2}
                    value={replyContent}
                    onChange={(e) => setReplyContent(e.target.value)}
                    placeholder="Escribe tu respuesta..."
                    className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-1.5 text-xs text-[hsl(var(--text-primary))]"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setActiveReplyId(null)}
                      className="rounded-md border border-[hsl(var(--border))] px-3 py-1 text-xs font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={replySubmitting}
                      className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1 text-xs font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
                    >
                      {replySubmitting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
                      Enviar Respuesta
                    </button>
                  </div>
                </form>
              )}

              {/* Nested Replies */}
              {comment.replies && comment.replies.length > 0 && (
                <div className="ml-6 space-y-3 border-l-2 border-[hsl(var(--border))] pl-4">
                  {comment.replies.map((reply) => (
                    <div key={reply.id} className="space-y-1 rounded-lg bg-[hsl(var(--surface-2))] p-3">
                      <div className="flex items-center gap-2">
                        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[hsl(var(--surface-3))] text-[hsl(var(--text-primary))] font-bold text-2xs">
                          {reply.author_name.charAt(0).toUpperCase()}
                        </div>
                        <span className="text-xs font-semibold text-[hsl(var(--text-primary))]">{reply.author_name}</span>
                        <span className="text-2xs text-[hsl(var(--text-secondary))]">
                          {new Date(reply.created_at).toLocaleDateString("es-ES", {
                            day: "numeric",
                            month: "short",
                          })}
                        </span>
                      </div>
                      <p className="text-xs text-[hsl(var(--text-primary))] whitespace-pre-wrap pl-8">
                        {reply.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
