"use client";

import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Check,
  ShieldAlert,
  Trash2,
  MessageCircle,
  Inbox,
  Loader2,
  Calendar,
  Mail,
  User,
  FileText,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { canEditCms } from "@/lib/cms/permissions";
import { listCmsPostComments, patchCmsPostCommentStatus } from "@/lib/cms/v2";
import { SITE_KEY } from "@/lib/site-config";
import { CmsCommentStatus, CmsPostComment } from "@/types/cms-v2";

const TABS: { id: CmsCommentStatus; label: string }[] = [
  { id: "pending", label: "Pendientes" },
  { id: "approved", label: "Aprobados" },
  { id: "spam", label: "Spam" },
];

export default function CmsCommentsManagementPage() {
  const { token, user } = useAuth();
  const canEdit = canEditCms(user?.role);

  const [activeTab, setActiveTab] = useState<CmsCommentStatus>("pending");
  const [comments, setComments] = useState<CmsPostComment[]>([]);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});

  const fetchComments = useCallback(async () => {
    if (!token || !canEdit) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await listCmsPostComments(
        SITE_KEY,
        { status: activeTab, skip: 0, limit: 100 },
        token
      );
      setComments(res.items);
      setPendingCount(res.pending_count);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error al cargar comentarios";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [activeTab, canEdit, token]);

  useEffect(() => {
    fetchComments();
  }, [fetchComments]);

  const handleUpdateStatus = async (commentId: string, newStatus: CmsCommentStatus) => {
    if (!token) return;
    setActionLoading((prev) => ({ ...prev, [commentId]: true }));
    try {
      await patchCmsPostCommentStatus(SITE_KEY, commentId, newStatus, token);
      if (newStatus === "approved") {
        toast.success("Comentario aprobado correctamente");
      } else if (newStatus === "spam") {
        toast.info("Comentario marcado como spam");
      } else if (newStatus === "deleted") {
        toast.success("Comentario eliminado");
      }
      await fetchComments();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error al actualizar estado";
      toast.error(message);
    } finally {
      setActionLoading((prev) => ({ ...prev, [commentId]: false }));
    }
  };

  return (
    <div className="min-h-screen bg-[hsl(var(--bg-primary))] p-6 text-[hsl(var(--text-primary))]">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
              <MessageCircle className="h-6 w-6 text-primary" />
              Moderación de Comentarios
            </h1>
            <p className="text-sm text-[hsl(var(--text-secondary))]">
              Gestiona y modera los comentarios enviados por los lectores en las publicaciones del blog.
            </p>
          </div>
          <button
            onClick={fetchComments}
            disabled={loading}
            className="flex items-center gap-1.5 self-start rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-1.5 text-xs font-medium hover:bg-[hsl(var(--surface-2))] disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Actualizar
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-[hsl(var(--border))]">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`relative flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "border-primary text-primary"
                    : "border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                }`}
              >
                {tab.label}
                {tab.id === "pending" && pendingCount > 0 && (
                  <span className="rounded-full bg-amber-500 px-2 py-0.5 text-2xs font-bold text-white">
                    {pendingCount}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Content list */}
        {loading ? (
          <div className="space-y-4" data-testid="comments-skeleton">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="animate-pulse rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <div className="h-4 w-40 rounded bg-[hsl(var(--surface-3))]" />
                  <div className="h-4 w-24 rounded bg-[hsl(var(--surface-3))]" />
                </div>
                <div className="mt-3 h-12 rounded bg-[hsl(var(--surface-3))]" />
              </div>
            ))}
          </div>
        ) : comments.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] py-12 text-center"
            data-testid="comments-empty-state"
          >
            <Inbox className="h-10 w-10 text-[hsl(var(--text-secondary))]" />
            <h3 className="mt-3 text-base font-semibold">No hay comentarios {activeTab === "pending" ? "pendientes" : activeTab === "approved" ? "aprobados" : "en spam"}</h3>
            <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
              {activeTab === "pending"
                ? "Todos los comentarios han sido moderados."
                : "No se encontraron registros en esta categoría."}
            </p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="comments-list">
            {comments.map((comment) => (
              <div
                key={comment.id}
                className="flex flex-col gap-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm sm:flex-row sm:items-start sm:justify-between"
              >
                <div className="space-y-2 flex-1">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="flex items-center gap-1 text-sm font-semibold text-[hsl(var(--text-primary))]">
                      <User className="h-3.5 w-3.5 text-[hsl(var(--text-secondary))]" />
                      {comment.author_name}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-[hsl(var(--text-secondary))]">
                      <Mail className="h-3.5 w-3.5" />
                      {comment.author_email}
                    </span>
                    {comment.post_title && (
                      <span className="flex items-center gap-1 rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-950/50 dark:text-blue-300">
                        <FileText className="h-3 w-3" />
                        {comment.post_title}
                      </span>
                    )}
                    <span className="flex items-center gap-1 text-xs text-[hsl(var(--text-secondary))]">
                      <Calendar className="h-3 w-3" />
                      {new Date(comment.created_at).toLocaleDateString("es-ES", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>

                  <p className="text-sm text-[hsl(var(--text-primary))] whitespace-pre-wrap rounded-lg bg-[hsl(var(--surface-2))] p-3 border border-[hsl(var(--border))]">
                    {comment.content}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0 self-end sm:self-start">
                  {comment.status !== "approved" && (
                    <button
                      onClick={() => handleUpdateStatus(comment.id, "approved")}
                      disabled={actionLoading[comment.id]}
                      aria-label="Aprobar comentario"
                      title="Aprobar"
                      className="flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                      {actionLoading[comment.id] ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Check className="h-3.5 w-3.5" />
                      )}
                      Aprobar
                    </button>
                  )}

                  {comment.status !== "spam" && (
                    <button
                      onClick={() => handleUpdateStatus(comment.id, "spam")}
                      disabled={actionLoading[comment.id]}
                      aria-label="Marcar como spam"
                      title="Marcar Spam"
                      className="flex items-center gap-1 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50"
                    >
                      {actionLoading[comment.id] ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <ShieldAlert className="h-3.5 w-3.5" />
                      )}
                      Spam
                    </button>
                  )}

                  {comment.status !== "deleted" && (
                    <button
                      onClick={() => handleUpdateStatus(comment.id, "deleted")}
                      disabled={actionLoading[comment.id]}
                      aria-label="Eliminar comentario"
                      title="Eliminar"
                      className="flex items-center gap-1 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-700 disabled:opacity-50"
                    >
                      {actionLoading[comment.id] ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                      Eliminar
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
