import os
import re

path = "d:/ccf/backend/main.py"
with open(path, "rb") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    line_text = line.decode("utf-8", errors="ignore")

    # 1. Fix backslashed decorators (multi-line or single line)
    # If a line contains @app. and Ends with \
    if "@app." in line_text and line_text.strip().endswith("\\"):
        line_text = line_text.replace("\\", "").strip() + " "  # Keep merging

    # 2. Fix 'with open' indentation
    if "with open(" in line_text:
        line_text = "    " + line_text.strip() + "\n"

    # 3. Fix 'buffer.write' indentation
    if "buffer.write(" in line_text:
        line_text = "        " + line_text.strip() + "\n"

    # 4. Remove null bytes
    line_text = line_text.replace("\x00", "")

    # 5. Fix common corrupted f-strings if they appear on one line
    line_text = line_text.replace("f\\/static/res_", 'f"/static/res_')
    line_text = line_text.replace("f\\uploads/res_", 'f"uploads/res_')

    new_lines.append(line_text.encode("utf-8"))

# Final pass on the whole string for multi-line patterns
full_text = b"".join(new_lines).decode("utf-8")
full_text = re.sub(
    r"@app\.(post|get|patch|delete|put)\s*\(\s*\\\s*([^)]+)\s*\\\s*\)",
    r"@app.\1(\"\2\")",
    full_text,
)

with open(path, "w", encoding="utf-8") as f:
    f.write(full_text)
