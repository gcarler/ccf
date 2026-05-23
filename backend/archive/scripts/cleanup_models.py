import os

path = r'd:\ccf\backend\models.py'
with open(path, 'rb') as f:
    content = f.read()

clean_content = content.replace(b'\x00', b'')

with open(path, 'wb') as f:
    f.write(clean_content)

print(f"Original size: {len(content)}")
print(f"Cleaned size: {len(clean_content)}")
print(f"Null bytes removed: {content.count(b'\x00')}")
