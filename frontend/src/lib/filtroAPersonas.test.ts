import { describe, expect, it } from 'vitest';
import { filtroAPersona, filtroAPersonaMultiCampo, filtroAPersonas, normalizarBusquedaPersona } from './filtroAPersonas';

describe('normalizarBusquedaPersona', () => {
  it('normalizes case, accents and whitespace', () => {
    expect(normalizarBusquedaPersona('  Lúis   Ricardo  ')).toBe('luis ricardo');
  });
  it('handles null/undefined/empty input', () => {
    expect(normalizarBusquedaPersona(null)).toBe('');
    expect(normalizarBusquedaPersona(undefined)).toBe('');
    expect(normalizarBusquedaPersona('')).toBe('');
  });
  it('keeps a leading @', () => {
    expect(normalizarBusquedaPersona('@luisricardo')).toBe('@luisricardo');
    expect(normalizarBusquedaPersona('luis@ccf.org')).toBe('luis@ccf.org');
  });
});

describe('filtroAPersonas', () => {
  it('matches incremental and multi-word prefixes', () => {
    expect(filtroAPersonas('Luis Ricardo Meza', 'l')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'LU')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'luis r')).toBe(true);
  });
  it('matches compound names across middle words', () => {
    expect(filtroAPersonas('Juan Luis Meza', 'juan meza')).toBe(true);
    expect(filtroAPersonas('María Del Carmen Gómez', 'maria gomez')).toBe(true);
    expect(filtroAPersonas('María Del Carmen Gómez', 'del carmen')).toBe(true);
  });
  it('matches initials spanning non-contiguous words', () => {
    expect(filtroAPersonas('Luis Ricardo Meza', 'l m')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'ricardo m')).toBe(true);
  });
  it('keeps word order and rejects unknown words', () => {
    expect(filtroAPersonas('Luis Ricardo Meza', 'meza luis')).toBe(false);
    expect(filtroAPersonas('Luis Ricardo Meza', 'luis r x')).toBe(false);
    expect(filtroAPersonas('Luis', 'luis r')).toBe(false);
  });
  it('single word matches any name or last-name word', () => {
    expect(filtroAPersonas('Luis Ricardo Meza', 'meza')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'm')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'xavier')).toBe(false);
  });
  it('empty query matches everything; empty name matches nothing', () => {
    expect(filtroAPersonas('Luis Meza', '')).toBe(true);
    expect(filtroAPersonas('', 'juan')).toBe(false);
    expect(filtroAPersonas(null, 'juan')).toBe(false);
  });
});

describe('filtroAPersona', () => {
  const persona = {
    id: 'p1',
    username: 'gscarlosernesto',
    nombre_completo: 'Luis Ricardo Meza',
    email: 'luis.meza@ccf.org',
    phone: '+57 300 123 4567',
    id_number: '1123456789',
    church_role: 'Líder de Grupo',
  };

  it('matches by name, including last name', () => {
    expect(filtroAPersona(persona, 'luis')).toBe(true);
    expect(filtroAPersona(persona, 'meza')).toBe(true);
    expect(filtroAPersona(persona, 'luis m')).toBe(true);
  });
  it('keeps multi-field searches explicit', () => {
    expect(filtroAPersonaMultiCampo(persona, 'luis.meza')).toBe(true);
    expect(filtroAPersonaMultiCampo(persona, 'ccf.org')).toBe(true);
    expect(filtroAPersonaMultiCampo(persona, '300123')).toBe(true);
    expect(filtroAPersonaMultiCampo(persona, '1123456789')).toBe(true);
    expect(filtroAPersonaMultiCampo(persona, 'lider')).toBe(true);
  });
  it('falls back to first_name + last_name', () => {
    expect(filtroAPersona({ first_name: 'Ana', last_name: 'Gómez' }, 'ana gomez')).toBe(true);
  });
  it('returns false when nothing matches or persona is empty', () => {
    expect(filtroAPersona(persona, 'xavier')).toBe(false);
    expect(filtroAPersona(null, 'luis')).toBe(false);
    expect(filtroAPersona(undefined, 'luis')).toBe(false);
  });
  it('does not return false positives from non-name fields', () => {
    expect(filtroAPersona({ nombre_completo: 'Carlos Pérez', email: 'contacto@lau-car.example' }, 'lau')).toBe(false);
    expect(filtroAPersona({ nombre_completo: 'Ana Gómez', email: 'contacto@lau-car.example' }, 'car')).toBe(false);
    expect(filtroAPersona({ nombre_completo: 'Laura Méndez' }, 'lau')).toBe(true);
    expect(filtroAPersona({ nombre_completo: 'Carlos Pérez' }, 'car')).toBe(true);
  });
  it('empty query matches everything', () => {
    expect(filtroAPersona(persona, '')).toBe(true);
  });
  it('with @ matches the username only', () => {
    expect(filtroAPersona(persona, '@gscarlos')).toBe(true);
    expect(filtroAPersona(persona, '@luis')).toBe(false);
    expect(filtroAPersona({ nombre_completo: 'Luis Ricardo Meza' }, '@luis')).toBe(false);
  });
  it('without @ never searches username', () => {
    expect(filtroAPersona(persona, 'gscarlosernesto')).toBe(false);
  });
});
