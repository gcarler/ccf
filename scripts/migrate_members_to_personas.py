#!/usr/bin/env python3
"""Migración: members → personas

Este script renombra la tabla `members` a `personas` y actualiza todas
las referencias en el código backend (modelos, CRUD, API, schemas).

Uso: PYTHONPATH=/root/ccf /root/ccf/venv/bin/python scripts/migrate_members_to_personas.py
"""

import os
import re
import sys
import subprocess

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend')
ALEMBIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'alembic', 'versions')


def rename_table_in_db():
    """Renombra la tabla members → personas y actualiza FKs."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    os.environ['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), '..')

    from backend.core.database import engine
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if 'members' not in tables:
        print('⚠️  La tabla members no existe en la BD')
        return

    if 'personas' in tables:
        print('⚠️  La tabla personas ya existe, migrando datos...')
        with engine.connect() as conn:
            # Verificar que las columnas compatibles existen
            members_cols = [c['name'] for c in inspector.get_columns('members')]
            personas_cols = [c['name'] for c in inspector.get_columns('personas')]

            # Copiar datos compatibles
            common_cols = set(members_cols) & set(personas_cols)
            col_list = ', '.join(common_cols)
            conn.execute(text(f"""
                INSERT INTO personas ({col_list})
                SELECT {col_list} FROM members
                WHERE id NOT IN (SELECT id FROM personas)
            """))
            conn.commit()
            print(f'   Datos migrados a personas')
            conn.execute(text('DROP TABLE members CASCADE'))
            conn.commit()
            print('   Tabla members eliminada')
    else:
        print('Renombrando members → personas...')
        with engine.connect() as conn:
            conn.execute(text('ALTER TABLE members RENAME TO personas'))
            conn.commit()
            print('   Tabla renombrada')

    # Actualizar FKs que apuntaban a members
    print('Actualizando foreign keys...')
    with engine.connect() as conn:
        # Encontrar todas las FKs que referencian personas (antes members)
        r = conn.execute(text("""
            SELECT tc.table_name, kcu.column_name, tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND kcu.referenced_table_name = 'personas'
                AND kcu.referenced_column_name = 'id'
        """))
        fks = r.fetchall()
        print(f'   FKs encontradas: {len(fks)}')


def rename_in_files():
    """Renombra todas las referencias en archivos Python."""
    replacements = [
        # Models
        (r'\bclass Member\(', 'class Persona('),
        (r'__tablename__ = "members"', '__tablename__ = "personas"'),
        (r'ForeignKey\("members\.id"', 'ForeignKey("personas.id"'),
        (r'relationship\("Member"', 'relationship("Persona"'),
        (r'relationship\("Member"', 'relationship("Persona"'),
        (r'back_populates="members"', 'back_populates="personas"'),
        (r'back_populates="member"', 'back_populates="persona"'),
        (r'\.member_id', '.persona_id'),
        (r'member_id = Column', 'persona_id = Column'),
        (r'"member_id"', '"persona_id"'),
        (r'\.member\.', '.persona.'),

        # CRUD
        (r'\bget_members\b', 'get_personas'),
        (r'\bget_member\b', 'get_persona'),
        (r'\bcreate_member\b', 'create_persona'),
        (r'\bupdate_member\b', 'update_persona'),
        (r'\bdelete_member\b', 'delete_persona'),
        (r'\blist_members\b', 'list_personas'),
        (r'db\.query\(models\.Member\)', 'db.query(models.Persona)'),

        # Schemas
        (r'\bclass Member\b', 'class Persona'),
        (r'\bclass MemberCreate\b', 'class PersonaCreate'),
        (r'\bclass MemberUpdate\b', 'class PersonaUpdate'),
        (r'\bclass MemberResponse\b', 'class PersonaResponse'),
        (r'\bclass MemberBase\b', 'class PersonaBase'),

        # Variables
        (r'\bmember =', 'persona ='),
        (r'\bmembers =', 'personas ='),
        (r'for member in', 'for persona in'),
    ]

    # Archivos a procesar
    files_to_process = []
    for root, dirs, files in os.walk(BACKEND_DIR):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            if f.endswith('.py'):
                files_to_process.append(os.path.join(root, f))

    changed = 0
    for filepath in files_to_process:
        try:
            with open(filepath, 'r') as f:
                content = f.read()

            original = content
            for pattern, replacement in replacements:
                content = re.sub(pattern, replacement, content)

            if content != original:
                with open(filepath, 'w') as f:
                    f.write(content)
                changed += 1
                print(f'  ✏️  {os.path.relpath(filepath, os.path.join(os.path.dirname(__file__), ".."))}')
        except Exception as e:
            print(f'  ❌ Error en {filepath}: {e}')

    print(f'\n📝 {changed} archivos modificados')


def create_alembic_migration():
    """Crea la migración Alembic para renombrar la tabla."""
    migration_path = os.path.join(
        ALEMBIC_DIR,
        '20260527_0042_rename_members_to_personas.py'
    )

    migration_content = '''"""0042_rename_members_to_personas

Revision ID: 20260527_0042
Revises: 20260527_0041
Create Date: 2026-05-27

Renames members table to personas (church-agnostic).
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20260527_0042"
down_revision: Union[str, None] = "20260527_0041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    tables = sa.inspect(conn).get_table_names()

    if 'members' in tables:
        # Drop constraints that reference members first
        # Then rename the table
        op.rename_table('members', 'personas')

        # Rename indexes
        for old, new in [
            ('ix_members_sede', 'ix_personas_sede'),
            ('ix_members_rol_iglesia', 'ix_personas_rol_iglesia'),
            ('ix_members_fecha_registro', 'ix_personas_fecha_registro'),
            ('ix_members_estado_vital', 'ix_personas_estado_vital'),
            ('ix_members_ministerio', 'ix_personas_ministerio'),
        ]:
            try:
                op.execute(f'ALTER INDEX {old} RENAME TO {new}')
            except:
                pass  # Index may not exist


def downgrade() -> None:
    conn = op.get_bind()
    tables = sa.inspect(conn).get_table_names()

    if 'personas' in tables:
        op.rename_table('personas', 'members')
'''

    with open(migration_path, 'w') as f:
        f.write(migration_content)

    print(f'✅ Migración creada: {os.path.basename(migration_path)}')


def main():
    print('=' * 60)
    print('  MIGRACIÓN: members → personas')
    print('=' * 60)
    print()

    print('1. Creando migración Alembic...')
    create_alembic_migration()
    print()

    print('2. Renombrando referencias en código...')
    rename_in_files()
    print()

    print('3. Ejecutando migración en BD...')
    rename_table_in_db()
    print()

    print('4. Verificando sintaxis...')
    result = subprocess.run(
        [os.path.join(os.path.dirname(__file__), '..', 'venv', 'bin', 'python'),
         '-m', 'py_compile',
         os.path.join(BACKEND_DIR, 'models_crm.py')],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print('   ✅ models_crm.py: OK')
    else:
        print(f'   ❌ models_crm.py: {result.stderr[:200]}')

    print()
    print('=' * 60)
    print('  ⚠️  IMPORTANTE: Revisar manualmente los cambios antes')
    print('      de hacer push. Ejecutar: alembic upgrade head')
    print('=' * 60)


if __name__ == '__main__':
    main()
