'use client';

import { Calendar, Clock, MapPin, Users } from 'lucide-react';
import React from 'react';
import {
  FORM_INPUT_CLASS,
  type Grupo,
  type Persona,
} from '../useGroupsPage';

interface GroupFormProps {
  formData: Partial<Grupo>;
  setFormData: React.Dispatch<React.SetStateAction<Partial<Grupo>>>;
  personas: Persona[];
  onSubmit: (e: React.FormEvent) => void;
  formId: string;
}

const DAYS_OF_WEEK = [
  'Lunes',
  'Martes',
  'Miércoles',
  'Jueves',
  'Viernes',
  'Sábado',
  'Domingo',
];

export function GroupForm({
  formData,
  setFormData,
  personas,
  onSubmit,
  formId,
}: GroupFormProps) {
  return (
    <form id={formId} onSubmit={onSubmit} className="space-y-4 w-full">
      {/* Identidad */}
      <div className="space-y-4">
        <div>
          <label htmlFor="group-code" className="block text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
            Código del Grupo
          </label>
          <input
            id="group-code"
            value={formData.code || ''}
            onChange={e =>
              setFormData({
                ...formData,
                code: e.target.value,
              } as Partial<Grupo>)
            }
            className={FORM_INPUT_CLASS}
            placeholder="CCF-001 o dejar vacío"
          />
        </div>
        <div>
          <label htmlFor="group-name" className="block text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
            Nombre o Número del Grupo
          </label>
          <input
            id="group-name"
            value={formData.name || ''}
            onChange={e =>
              setFormData({ ...formData, name: e.target.value })
            }
            className={FORM_INPUT_CLASS}
            placeholder="Ej. Casa Bethel, Grupo 12 o dejar pendiente"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="group-zone" className="block text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2 flex items-center gap-1">
              <MapPin size={11} /> Zona/Barrio
            </label>
            <input
              id="group-zone"
              value={formData.zone || ''}
              onChange={e =>
                setFormData({ ...formData, zone: e.target.value })
              }
              className={FORM_INPUT_CLASS}
              placeholder="Norte, Centro..."
            />
          </div>
          <div>
            <label htmlFor="group-address" className="block text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2 flex items-center gap-1">
              <MapPin size={11} /> Dirección
            </label>
            <input
              id="group-address"
              value={formData.address || ''}
              onChange={e =>
                setFormData({ ...formData, address: e.target.value })
              }
              className={FORM_INPUT_CLASS}
              placeholder="Calle, número..."
            />
          </div>
        </div>
      </div>

      {/* Roles */}
      <div>
        <h3 className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-4 flex items-center gap-2">
          <Users size={12} className="text-[hsl(var(--primary))]" /> Roles del
          Grupo
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { key: 'leader_id', label: 'Líder' },
            { key: 'assistant_id', label: 'Asistente de Líder' },
            { key: 'host_id', label: 'Anfitrión' },
          ].map(({ key, label }) => (
            <div key={key}>
              <label htmlFor={`group-role-${key}`} className="block text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
                {label}
              </label>
              <select
                id={`group-role-${key}`}
                value={
                  formData[
                  key as 'leader_id' | 'assistant_id' | 'host_id'
                  ] ?? ''
                }
                onChange={e =>
                  setFormData({
                    ...formData,
                    [key]: e.target.value || undefined,
                  })
                }
                className={FORM_INPUT_CLASS}
              >
                <option value="">Seleccionar...</option>
                {personas.map(m => (
                  <option key={m.id} value={m.id}>
                    {m.nombre_completo}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      </div>

      {/* Logística */}
      <div>
        <h3 className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-4 flex items-center gap-2">
          <Calendar size={12} className="text-[hsl(var(--primary))]" /> Logística
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="col-span-2">
            <label htmlFor="group-day" className="block text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2 flex items-center gap-1">
              <Clock size={11} /> Día de Reunión
            </label>
            <select
              id="group-day"
              value={formData.day_of_week || ''}
              onChange={e =>
                setFormData({
                  ...formData,
                  day_of_week: e.target.value,
                })
              }
              className={FORM_INPUT_CLASS}
            >
              <option value="">Seleccionar...</option>
              {DAYS_OF_WEEK.map(d => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="group-start-time" className="block text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
              Hora Inicio
            </label>
            <input
              id="group-start-time"
              type="time"
              value={formData.start_time || ''}
              onChange={e =>
                setFormData({
                  ...formData,
                  start_time: e.target.value,
                })
              }
              className={FORM_INPUT_CLASS}
            />
          </div>
          <div>
            <label htmlFor="group-end-time" className="block text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
              Hora Fin
            </label>
            <input
              id="group-end-time"
              type="time"
              value={formData.end_time || ''}
              onChange={e =>
                setFormData({ ...formData, end_time: e.target.value })
              }
              className={FORM_INPUT_CLASS}
            />
          </div>
          <div>
            <label htmlFor="group-capacity" className="block text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
              Capacidad
            </label>
            <input
              id="group-capacity"
              type="number"
              value={formData.capacity || ''}
              onChange={e =>
                setFormData({
                  ...formData,
                  capacity: Number(e.target.value),
                })
              }
              className={FORM_INPUT_CLASS}
            />
          </div>
        </div>
      </div>
    </form>
  );
}

export default GroupForm;
