#!/usr/bin/env python3
"""
Migrate hardcoded Tailwind colors to semantic CSS tokens.
Rules based on the project's semantic token mapping.
"""
import re
from pathlib import Path

# Paths
SRC_DIR = Path('/root/ccf/frontend/src')
EXCLUDE_FILES = {
    'tailwind.config.ts',
    'tailwind.config.js',
    'globals.css',
}

# Regex patterns: (regex, replacement)
# Order matters — more specific first.
# We use negative lookahead to avoid opacity variants (e.g. bg-white/5)
RULES = [
    # text-gray-100 to text-gray-400 -> text-secondary
    (r'\btext-gray-(100|200|300|400)\b(?!/)', r'text-[hsl(var(--text-secondary))]'),
    # text-gray-500 to text-gray-700 -> text-primary
    (r'\btext-gray-(500|600|700)\b(?!/)', r'text-[hsl(var(--text-primary))]'),
    # text-gray-900 / text-black -> text-primary
    (r'\btext-gray-900\b(?!/)', r'text-[hsl(var(--text-primary))]'),
    (r'\btext-black\b(?!/)', r'text-[hsl(var(--text-primary))]'),
    # bg-gray-50 to bg-gray-200 -> bg-muted
    (r'\bbg-gray-(50|100|200)\b(?!/)', r'bg-[hsl(var(--bg-muted))]'),
    # bg-gray-800 to bg-gray-950 -> bg-primary
    (r'\bbg-gray-(800|900|950)\b(?!/)', r'bg-[hsl(var(--bg-primary))]'),
    # bg-white -> bg-primary
    (r'\bbg-white\b(?!/)', r'bg-[hsl(var(--bg-primary))]'),
    # text-blue-400 to text-blue-700 -> primary
    (r'\btext-blue-(400|500|600|700)\b(?!/)', r'text-[hsl(var(--primary))]'),
    # bg-blue-400 to bg-blue-700 -> primary
    (r'\bbg-blue-(400|500|600|700)\b(?!/)', r'bg-[hsl(var(--primary))]'),
    # text-red-400 to text-red-700 -> destructive
    (r'\btext-red-(400|500|600|700)\b(?!/)', r'text-[hsl(var(--destructive))]'),
    # bg-red-400 to bg-red-700 -> destructive
    (r'\bbg-red-(400|500|600|700)\b(?!/)', r'bg-[hsl(var(--destructive))]'),
    # text-green-400 to text-green-700 -> secondary
    (r'\btext-green-(400|500|600|700)\b(?!/)', r'text-[hsl(var(--secondary))]'),
    # bg-green-400 to bg-green-700 -> secondary
    (r'\bbg-green-(400|500|600|700)\b(?!/)', r'bg-[hsl(var(--secondary))]'),
    # border-gray-200 to border-gray-400 -> border-primary
    (r'\bborder-gray-(200|300|400)\b(?!/)', r'border-[hsl(var(--border-primary))]'),
]

def migrate_file(path: Path) -> int:
    original = path.read_text(encoding='utf-8')
    text = original
    changes = 0
    for pattern, repl in RULES:
        new_text, count = re.subn(pattern, repl, text)
        if count:
            text = new_text
            changes += count
    if changes:
        path.write_text(text, encoding='utf-8')
    return changes

def main():
    total_changes = 0
    files_changed = 0
    for ext in ('*.tsx', '*.ts', '*.css'):
        for path in SRC_DIR.rglob(ext):
            if path.name in EXCLUDE_FILES:
                continue
            changes = migrate_file(path)
            if changes:
                total_changes += changes
                files_changed += 1
                print(f'  +{changes:4d}  {path.relative_to(SRC_DIR)}')
    print(f'\nDone. {total_changes} replacements in {files_changed} files.')

if __name__ == '__main__':
    main()
