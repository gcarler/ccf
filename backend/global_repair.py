import os
import re

path = 'd:/ccf/backend/main.py'
with open(path, 'rb') as f:
    content = f.read().decode('utf-8', errors='ignore')

# 1. Fix backslashed decorators
# Example: @app.post(\n/url/\n...) -> @app.post("/url/...")
def fix_decorators(m):
    inner = m.group(1).replace('\n', '').replace('\\', '').strip()
    return f'@app.{m.group(2)}(\"{inner}\")'

# Targeted fixes for the common patterns I've seen
content = re.sub(r'@app\.(post|get|patch|delete|put)\s*\(\\\s*([^)]+)\\\s*\)', r'@app.\1(\"\2\")', content)

# 2. Fix the specific "with open" indentation and backslashes
content = content.replace('with open(file_path, \\wb\\) as buffer:', '    with open(file_path, \"wb\") as buffer:')
content = content.replace('with open(file_path, \"wb\") as buffer:', '    with open(file_path, \"wb\") as buffer:') # Ensure indent

# 3. Fix the split f-strings
# This is tricky, but let's try a common case
content = re.sub(r'f\\/static/res_\s*\nlesson_id\s*\n_\s*\nfile\.filename\s*\n\\', 'f\"/static/res_{lesson_id}_{file.filename}\"', content)
content = re.sub(r'f\\uploads/res_\s*\nlesson_id\s*\n_\s*\nfile\.filename\s*\n\\', 'f\"uploads/res_{lesson_id}_{file.filename}\"', content)

# 4. Remove all null bytes just in case
content = content.replace('\x00', '')

# 5. Fix common indentation errors for blocks that might have been shifted
# I'll just look for lines that start with 'with' and have no indent
content = re.sub(r'\nwith open\(', '\n    with open(', content)
content = re.sub(r'\nbuffer\.write\(', '\n        buffer.write(', content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
