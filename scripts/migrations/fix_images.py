import os
import re

count = 0
for root, dirs, files in os.walk("frontend/src"):
    if "node_modules" in root or ".next" in root:
        continue
    for file in files:
        if file.endswith((".tsx", ".ts")):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Replace https://images.unsplash.com/photo-UUID?w=XXX&q=XX
            # with https://picsum.photos/seed/UUID/800/600
            new_content = re.sub(
                r'https://images\.unsplash\.com/photo-([a-zA-Z0-9\-]+)(?:\?[^"\'\s]+)?',
                r"https://picsum.photos/seed/\1/800/600",
                content,
            )

            if new_content != content:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                count += 1

print(f"Replaced Unsplash images in {count} files.")
