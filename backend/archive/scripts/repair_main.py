import os

path = 'd:/ccf/backend/main.py'
with open(path, 'rb') as f:
    lines = f.readlines()

new_lines = []
skip_until = None

for i, line in enumerate(lines):
    line_text = line.decode('utf-8', errors='ignore').strip()
    
    # Check if we are in a skip zone
    if skip_until and skip_until not in line_text:
        continue
    if skip_until and skip_until in line_text:
        skip_until = None
        continue

    # Detect the start of the corrupted block
    if '@app.post(' in line_text and ('/lessons/' in line_text or '\\' in line_text or '/' in line_text):
         if 'resources' in line_text or '\\' in line_text:
            # We found the start of the mess
            # We will manually inject the correct function and skip until the next known good line
            new_lines.append(b'@app.post(\"/lessons/{lesson_id}/resources\")\n')
            new_lines.append(b'async def upload_resource(\n')
            new_lines.append(b'    lesson_id: int,\n')
            new_lines.append(b'    title: str,\n')
            new_lines.append(b'    file: UploadFile = File(...),\n')
            new_lines.append(b'    db: Session = Depends(get_db),\n')
            new_lines.append(b'    current_user: models.User = Depends(require_staff_or_admin)\n')
            new_lines.append(b'):\n')
            new_lines.append(b'    # Save file\n')
            new_lines.append(b'    file_path = f\"uploads/res_{lesson_id}_{file.filename}\"\n')
            new_lines.append(b'    with open(file_path, \"wb\") as buffer:\n')
            new_lines.append(b'        buffer.write(await file.read())\n')
            new_lines.append(b'    \n')
            new_lines.append(b'    # Create DB entry\n')
            new_lines.append(b'    db_resource = models.Resource(\n')
            new_lines.append(b'        title=title,\n')
            new_lines.append(b'        file_url=f\"/static/res_{lesson_id}_{file.filename}\",\n')
            new_lines.append(b'        resource_type=file.content_type,\n')
            new_lines.append(b'        lesson_id=lesson_id\n')
            new_lines.append(b'    )\n')
            new_lines.append(b'    db.add(db_resource)\n')
            new_lines.append(b'    db.commit()\n')
            new_lines.append(b'    db.refresh(db_resource)\n')
            new_lines.append(b'    return db_resource\n')
            
            # Find where to stop skipping
            # The next function usually starts with @app.get(\"/learning/enrollments\")
            skip_until = '@app.get(\"/learning/enrollments\")'
            continue
    
    # Fix other common corruptions I've seen
    if '@app.post(\\' in line_text:
        line = line.replace(b'\\', b'') # Extreme measure

    new_lines.append(line)

with open(path, 'wb') as f:
    f.writelines(new_lines)
