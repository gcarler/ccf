import os

# Check current directory
print(f"Current Directory: {os.getcwd()}")

path = 'models.py'
if not os.path.exists(path):
    print(f"Error: {path} not found in {os.getcwd()}")
    sys.exit(1)

with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print(f"File length: {len(content)}")
print(f"Announcement found: {'class Announcement' in content}")
print(f"Sermon found: {'class Sermon' in content}")
print(f"Book found: {'class Book' in content}")
print(f"Enrollments plural: {'__tablename__ = \"enrollments\"' in content}")
print(f"Enrollment singular: {'__tablename__ = \"enrollment\"' in content}")
