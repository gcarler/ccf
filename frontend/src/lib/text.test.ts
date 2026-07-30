import { describe, expect, it } from 'vitest';
import { sanitizeText } from './text';

describe('sanitizeText', () => {
    it('escapes HTML tags', () => {
        expect(sanitizeText('<b>bold</b>')).toBe('&lt;b&gt;bold&lt;/b&gt;');
    });

    it('escapes ampersands', () => {
        expect(sanitizeText('a & b')).toBe('a &amp; b');
    });

    it('escapes less-than and greater-than characters', () => {
        expect(sanitizeText('if (x < 3 && y > 5)')).toBe('if (x &lt; 3 &amp;&amp; y &gt; 5)');
    });

    it('preserves plain text', () => {
        expect(sanitizeText('Hello world')).toBe('Hello world');
    });
});
