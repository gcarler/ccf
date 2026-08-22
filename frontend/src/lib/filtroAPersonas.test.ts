import { describe, expect, it } from 'vitest';
import { filtroAPersonas, normalizarBusquedaPersona } from './filtroAPersonas';

describe('normalizarBusquedaPersona', () => {
  it('normalizes case, accents and whitespace', () => {
    expect(normalizarBusquedaPersona('  Lúis   Ricardo  ')).toBe('luis ricardo');
  });

  it('handles null/undefined/empty input', () => {
    expect(normalizarBusquedaPersona(null)).toBe('');
    expect(normalizarBusquedaPersona(undefined)).toBe('');
    expect(normalizarBusquedaPersona('')).toBe('');
  });
});

describe('filtroAPersonas', () => {
  it('matches incremental and multi-word prefixes', () => {
    expect(filtroAPersonas('Luis Ricardo Meza', 'l')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'LU')).toBe(true);
    expect(filtroAPersonas('Luis Ricardo Meza', 'luis r')).toBe(true);
    expect(filtroAPersonas('Ana Luis Meza', 'luis')).toBe(false);
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

  it('single word only matches the start of the full name', () => {
    expect(filtroAPersonas('Luis Ricardo Meza', 'meza')).toBe(false);
    expect(filtroAPersonas('Luis Ricardo Meza', 'ricardo')).toBe(false);
  });

  it('empty query matches everything; empty name matches nothing', () => {
    expect(filtroAPersonas('Luis Meza', '')).toBe(true);
    expect(filtroAPersonas('Luis Meza', '   ')).toBe(true);
    expect(filtroAPersonas('', 'juan')).toBe(false);
    expect(filtroAPersonas(null, 'juan')).toBe(false);
    expect(filtroAPersonas(undefined, 'juan')).toBe(false);
  });
});
