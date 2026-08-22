import { describe, expect, it } from 'vitest';
import { filtroAPersona, filtroAPersonas, normalizarBusquedaPersona } from './filtroAPersonas';

describe('normalizarBusquedaPersona', () => {
  it('normalizes case, accents and whitespace', () => {
    expect(normalizarBusquedaPersona('  Lúis   Ricardo  ')).toBe('luis ricardo');
  });

  it('handles null/undefined/empty input', () => {
    expect(normalizarBusquedaPersona(null)).toBe('');
    expect(normalizarBusquedaPersona(undefined)).toBe('');
    expect(normalizarBusquedaPersona('')).toBe('');
  });

  it('ignores a leading @ (messaging-style mention)', () => {
    expect(normalizarBusquedaPersona('@Luis Ricardo')).toBe('luis ricardo');
    expect(normalizarBusquedaPersona('@luisricardo')).toBe('luisricardo');
    expect(normalizarBusquedaPersona('@@juan')).toBe('juan');
    // El @ interno de un email no se toca.
    expect(normalizarBusquedaPersona('luis@ccf.org')).toBe('luis@ccf.org');
  });
});

describe('filtroAPersonas', () => {
  it('matches incremental and multi-word prefixes', () => {
    expect(filtroAPersonas('Luis Ricardo Meza', 'l')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'LU')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'luis r')).toBe(true);
  });

  it('matches compound names: first + last name across middle words', () => {
    expect(filtroAPersonas('Juan Luis Meza', 'juan meza')).toBe(true);
    expect(filtroAPersonas('María Del Carmen Gómez', 'maria gomez')).toBe(true);
    expect(filtroAPersonas('María Del Carmen Gómez', 'del carmen')).toBe(true);
  });

  it('matches initials spanning non-contiguous words', () => {
    expect(filtroAPersonas('Luis Ricardo Meza', 'l m')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'ricardo m')).toBe(true);
  });

  it('keeps word order: out-of-order query words do not match', () => {
    expect(filtroAPersonas('Luis Ricardo Meza', 'meza luis')).toBe(false);
    expect(filtroAPersonas('Luis Ricardo Meza', 'r luis')).toBe(false);
  });

  it('rejects queries with unknown words or more words than the name', () => {
    expect(filtroAPersonas('Luis Ricardo Meza', 'luis r x')).toBe(false);
    expect(filtroAPersonas('Luis Ricardo Meza', 'luis ricardo meza z')).toBe(false);
    expect(filtroAPersonas('Luis', 'luis r')).toBe(false);
  });

  it('single word matches any name or last-name word', () => {
    expect(filtroAPersonas('Luis Ricardo Meza', 'meza')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'ricardo')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'm')).toBe(true);
    expect(filtroAPersonas('Ana Luis Meza', 'luis')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'xavier')).toBe(false);
  });

  it('empty query matches everything; empty name matches nothing', () => {
    expect(filtroAPersonas('Luis Meza', '')).toBe(true);
    expect(filtroAPersonas('Luis Meza', '   ')).toBe(true);
    expect(filtroAPersonas('', 'juan')).toBe(false);
    expect(filtroAPersonas(null, 'juan')).toBe(false);
    expect(filtroAPersonas(undefined, 'juan')).toBe(false);
  });
});

describe('filtroAPersona', () => {
  const persona = {
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

  it('matches by email with partial input', () => {
    expect(filtroAPersona(persona, 'luis.meza')).toBe(true);
    expect(filtroAPersona(persona, '@ccf.org')).toBe(true);
  });

  it('matches by phone with partial input', () => {
    expect(filtroAPersona(persona, '300 123')).toBe(true);
    expect(filtroAPersona(persona, '1234567')).toBe(true);
  });

  it('matches by document number', () => {
    expect(filtroAPersona(persona, '1123456789')).toBe(true);
    expect(filtroAPersona(persona, '234567')).toBe(true);
  });

  it('matches by role', () => {
    expect(filtroAPersona(persona, 'lider')).toBe(true);
    expect(filtroAPersona(persona, 'grupo')).toBe(true);
  });

  it('normalizes accents in every field', () => {
    expect(filtroAPersona({ ...persona, church_role: 'Líder de Grupo' }, 'lider de grupo')).toBe(true);
    expect(filtroAPersona({ ...persona, nombre_completo: 'María José Fernández' }, 'maria')).toBe(true);
  });

  it('falls back to first_name + last_name when nombre_completo is absent', () => {
    const p = { first_name: 'Ana', last_name: 'Gómez', church_role: 'Pastor' };
    expect(filtroAPersona(p, 'ana gomez')).toBe(true);
    expect(filtroAPersona(p, 'gomez')).toBe(true);
  });

  it('honors the telefono alias', () => {
    expect(filtroAPersona({ nombre_completo: 'Juan Pérez', telefono: '5551234' }, '555')).toBe(true);
  });

  it('returns false when nothing matches or persona is empty', () => {
    expect(filtroAPersona(persona, 'xavier')).toBe(false);
    expect(filtroAPersona(null, 'luis')).toBe(false);
    expect(filtroAPersona(undefined, 'luis')).toBe(false);
  });

  it('empty query matches everything', () => {
    expect(filtroAPersona(persona, '')).toBe(true);
    expect(filtroAPersona(persona, '  ')).toBe(true);
  });

  it('matches with a leading @ (messaging-style)', () => {
    expect(filtroAPersona(persona, '@luis')).toBe(true);
    expect(filtroAPersona(persona, '@meza')).toBe(true);
    expect(filtroAPersona(persona, '@luis.meza@ccf.org')).toBe(true);
  });
});
