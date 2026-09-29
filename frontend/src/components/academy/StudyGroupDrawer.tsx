"use client";

import React, { FormEvent, useEffect, useState } from 'react';
import { UsersRound } from 'lucide-react';
import { DSButton } from '@/design';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { StudyGroup } from '@/types/academy';

interface StudyGroupDrawerProps {
  open: boolean;
  onClose: () => void;
  offeringId: string | null;
  offeringName?: string;
  token: string | null;
  onCreated: (group: StudyGroup) => Promise<void>;
}

export default function StudyGroupDrawer({ open, onClose, offeringId, offeringName, token, onCreated }: StudyGroupDrawerProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [maxMembers, setMaxMembers] = useState('5');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setName('');
      setDescription('');
      setMaxMembers('5');
    }
  }, [open]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !offeringId || saving) return;
    setSaving(true);
    try {
      const group = await apiFetch<StudyGroup>('/academy/study-groups', {
        method: 'POST',
        token,
        body: {
          offering_id: offeringId,
          name: name.trim(),
          description: description.trim() || null,
          max_members: Number(maxMembers),
        },
      });
      toast.success('Grupo de estudio creado');
      await onCreated(group);
      onClose();
    } catch (error: unknown) {
      toast.error(extractErrorMessage(error, 'No pudimos crear el grupo de estudio'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={<span className="flex items-center gap-2"><UsersRound className="size-4 text-[hsl(var(--primary))]" /> Crear grupo de estudio</span>}
      subtitle={offeringName ?? 'Invita a otros estudiantes a aprender en equipo'}
      width="w-full sm:max-w-xl"
    >
      <form onSubmit={handleSubmit} className="flex h-full flex-col bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
        <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
          <label className="block space-y-1.5 text-sm font-medium">
            <span>Nombre del grupo</span>
            <input
              required
              minLength={3}
              maxLength={255}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Ej. Laboratorio de conceptos"
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm outline-none focus:border-[hsl(var(--primary))] focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
            />
          </label>
          <label className="block space-y-1.5 text-sm font-medium">
            <span>Descripción <span className="font-normal text-[hsl(var(--text-secondary))]">(opcional)</span></span>
            <textarea
              rows={4}
              maxLength={1500}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="¿Qué van a estudiar o practicar juntos?"
              className="w-full resize-y rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm outline-none focus:border-[hsl(var(--primary))] focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
            />
          </label>
          <label className="block max-w-xs space-y-1.5 text-sm font-medium">
            <span>Capacidad máxima</span>
            <input
              required
              type="number"
              min={2}
              max={50}
              value={maxMembers}
              onChange={(event) => setMaxMembers(event.target.value)}
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm outline-none focus:border-[hsl(var(--primary))] focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
            />
          </label>
          {!offeringId && <p role="alert" className="text-sm text-[hsl(var(--destructive))]">Selecciona una comisión antes de crear un grupo.</p>}
        </div>
        <div className="flex justify-end gap-2 border-t border-[hsl(var(--border))] p-4">
          <DSButton type="button" variant="secondary" onClick={onClose}>Cancelar</DSButton>
          <DSButton type="submit" loading={saving} disabled={!offeringId || !token || name.trim().length < 3}>Crear grupo</DSButton>
        </div>
      </form>
    </RightPanel>
  );
}
