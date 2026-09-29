"use client";

import React, { FormEvent, useEffect, useState } from 'react';
import { GraduationCap, HeartHandshake } from 'lucide-react';
import { DSButton } from '@/design';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { MentorProfile, MentorshipRequest } from '@/types/academy';

interface MentorshipRequestDrawerProps {
  open: boolean;
  onClose: () => void;
  mentor: MentorProfile | null;
  token: string | null;
  onRequested: (request: MentorshipRequest) => Promise<void>;
}

function mentorName(mentor: MentorProfile | null): string {
  return mentor?.mentor_name ?? mentor?.name ?? mentor?.full_name ?? 'Mentor académico';
}

export default function MentorshipRequestDrawer({ open, onClose, mentor, token, onRequested }: MentorshipRequestDrawerProps) {
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (open) setMessage('');
  }, [open, mentor?.id]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!mentor || !token || sending) return;
    setSending(true);
    try {
      const request = await apiFetch<MentorshipRequest>('/academy/mentorship/request', {
        method: 'POST',
        token,
        body: {
          mentor_persona_id: mentor.mentor_persona_id ?? mentor.persona_id ?? mentor.id,
          message: message.trim(),
        },
      });
      toast.success('Solicitud de mentoría enviada');
      await onRequested(request);
      onClose();
    } catch (error: unknown) {
      toast.error(extractErrorMessage(error, 'No pudimos enviar la solicitud de mentoría'));
    } finally {
      setSending(false);
    }
  };

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={<span className="flex items-center gap-2"><HeartHandshake className="size-4 text-[hsl(var(--primary))]" /> Solicitar mentoría</span>}
      subtitle={mentorName(mentor)}
      width="w-full sm:max-w-xl"
    >
      {mentor ? (
        <form onSubmit={handleSubmit} className="flex h-full flex-col bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
          <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
            <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
              <div className="flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-full bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"><GraduationCap className="size-5" /></span>
                <div>
                  <p className="text-xs text-[hsl(var(--text-secondary))]">Mentor seleccionado</p>
                  <p className="font-semibold">{mentorName(mentor)}</p>
                </div>
              </div>
              {(mentor.expertise || mentor.availability_summary) && (
                <p className="mt-3 text-sm text-[hsl(var(--text-secondary))]">
                  {Array.isArray(mentor.expertise) ? mentor.expertise.join(', ') : mentor.expertise}
                  {mentor.availability_summary ? ` · ${mentor.availability_summary}` : ''}
                </p>
              )}
            </div>
            <label className="block space-y-1.5 text-sm font-medium">
              <span>Cuéntale qué acompañamiento buscas</span>
              <textarea
                rows={5}
                maxLength={1200}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Describe brevemente tus objetivos o preguntas académicas."
                className="w-full resize-y rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm outline-none focus:border-[hsl(var(--primary))] focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
              />
            </label>
          </div>
          <div className="flex justify-end gap-2 border-t border-[hsl(var(--border))] p-4">
            <DSButton type="button" variant="secondary" onClick={onClose}>Cancelar</DSButton>
            <DSButton type="submit" loading={sending} disabled={!token}>Enviar solicitud</DSButton>
          </div>
        </form>
      ) : (
        <div className="p-6 text-sm text-[hsl(var(--text-secondary))]">Selecciona un mentor para continuar.</div>
      )}
    </RightPanel>
  );
}
