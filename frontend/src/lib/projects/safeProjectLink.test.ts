import { describe, expect, it } from 'vitest';
import { getSafeProjectLink } from './safeProjectLink';

describe('getSafeProjectLink', () => {
  it.each([
    ['HTTPS receipt', 'https://files.example.org/receipt.pdf', 'https://files.example.org/receipt.pdf'],
    ['HTTP legacy receipt', 'http://files.example.org/receipt.pdf', 'http://files.example.org/receipt.pdf'],
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
