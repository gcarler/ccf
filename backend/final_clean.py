import os

path = 'd:/ccf/backend/main.py'
with open(path, 'rb') as f:
    data = f.read()

# Remove all null bytes
cleaned_data = data.replace(b'\x00', b'')

# Also fix the specific indentation issue at line 716
# and any remaining messy backslashes
text = cleaned_data.decode('utf-8', errors='ignore')
text = text.replace('with open(file_path, \"wb\") as buffer:\n        buffer.write(await file.read())', '    with open(file_path, \"wb\") as buffer:\n        buffer.write(await file.read())')

with open(path, 'wb') as f:
    f.write(text.encode('utf-8'))
