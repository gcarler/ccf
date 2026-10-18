import { describe, expect, it } from 'vitest';
import { getSafeProjectLink, isInternalPlatformProjectLink } from './safeProjectLink';

describe('getSafeProjectLink', () => {
  it.each([
    ['HTTPS receipt', 'https://files.example.org/receipt.pdf', 'https://files.example.org/receipt.pdf'],
    ['HTTP plain receipt', 'http://files.example.org/receipt.pdf', 'http://files.example.org/receipt.pdf'],
    ['project file path', '/api/static/projects/receipt.pdf', '/api/static/projects/receipt.pdf'],
  ])('preserves allowed %s links', (_label, input, expected) => {
    expect(getSafeProjectLink(input)).toBe(expected);
  });

  it.each([
    'javascript:alert(1)',
    'data:text/html,<script>alert(1)</script>',
    '//evil.example/receipt.pdf',
    'https://user:password@example.org/receipt.pdf',
    '\\\\evil.example\\receipt.pdf',
  ])('rejects unsafe link %s', (input) => {
    expect(getSafeProjectLink(input)).toBeNull();
  });
});

describe('isInternalPlatformProjectLink — guarda de enlaces internos PMI', () => {
  it.each([
    '/plataforma/projects/550e8400-e29b-41d4-a716-446655440000?view=list',
    '/plataforma/projects',
    '/api/static/projects/receipt.pdf',
    ' /plataforma/projects/inbox ',
  ])('acepta el enlace interno seguro %s', (input) => {
    expect(isInternalPlatformProjectLink(input)).toBe(true);
  });

  it.each([
    'https://files.example.org/receipt.pdf',
    'http://files.example.org/receipt.pdf',
    '/api/static/evangelism/receipt.pdf',
    '/api/static/documents/receipt.pdf',
  ])('rechaza el enlace no-interno %s', (input) => {
    expect(isInternalPlatformProjectLink(input)).toBe(false);
  });

  it.each([
    'javascript:alert(1)',
    'data:text/html,<script>alert(1)</script>',
    '//evil.example/receipt.pdf',
    'https://user:password@example.org/receipt.pdf',
    null,
    undefined,
    '',
  ])('rechaza el enlace inseguro o nulo %s', (input) => {
    expect(isInternalPlatformProjectLink(input as string | null)).toBe(false);
  });
});
