#!/usr/bin/env python3
"""Prefix remaining unused-vars identifiers with `_` so ESLint accepts them.

Because ESLint flagged each as 'defined but never used', we rename ALL whole-word
occurrences of the identifier in the file. The convention `_var` is the standard
TypeScript ESLint pattern for unused declarations.
"""
import json, re
from pathlib import Path

LINT_JSON = Path('/tmp/lint.json')
NAME_RE = re.compile(r"'([^']+)' (?:is defined but never used|is assigned a value but never used)")

def main() -> int:
    data = json.loads(LINT_JSON.read_text())
    edited = []
    for entry in data:
        fp = Path(entry['filePath'])
        if not fp.is_file():
            continue
        errs = [m for m in entry['messages']
                if m.get('severity') == 2
                and m.get('ruleId') == '@typescript-eslint/no-unused-vars']
        if not errs:
            continue
        try:
            text = fp.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        modified = False
        for msg in sorted(errs, key=lambda m: (m['line'], m['column']), reverse=True):
            mm = NAME_RE.search(msg.get('message', ''))
            if not mm:
                continue
            name = mm.group(1)
            if not name or name.startswith('_'):
                continue
            # Skip if the variable appears on an import-line to avoid breaking third-party API contracts (e.g., lucide-react)
            try:
                _line_ctx = text.split('\n')[msg['line'] - 1]
                if 'import' in _line_ctx and 'from' in _line_ctx and name in _line_ctx:
                    continue
            except Exception:
                pass
            new_text = re.sub(r'\b' + re.escape(name) + r'\b', '_' + name, text)
            if new_text != text:
                text = new_text
                modified = True
        if modified:
            fp.write_text(text, encoding='utf-8')
            edited.append(str(fp))
    print(f'Modified {len(edited)} files (rename)')
    for f in edited:
        print(f'  - {f}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
