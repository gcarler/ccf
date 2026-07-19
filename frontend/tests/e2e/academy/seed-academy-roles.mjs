// TKT-202 — Seed 4 distinct academy users into the Auth v3 backend so
// the multi-role Playwright suite can authenticate each persona.
// Reuses pattern from frontend/tests/e2e/seed-auth-user.mjs but loops over
// a role table instead of seeding a single admin.
//
// Persona → Platform role mapping (canonical DEFAULT_ROLES):
//   e2e.lector@ccf.local       → LECTOR           (seeded by seed_rol_plataforma; academy:read)
//   e2e.estudiante@ccf.local   → MIEMBRO          (seeded; academy:study — enroll+submit)
//   e2e.maestro@ccf.local      → DOCENTE          (created idempotently here; academy:read+edit)
//   e2e.admin@ccf.local        → ADMINISTRADOR    (seeded; academy:manage)
//
// DOCENTE is the only custom role. We create it idempotently because
// backend/management/seed_user_permissions.py::build_roles_config only seeds
// 5 canonical roles (ADMINISTRADOR/GESTOR/EDITOR/LECTOR/MIEMBRO), and the
// Maestro persona represents an academy-specific editor who must be able
// to write academy:edit without inheriting crm:edit/projects:edit that the
// generic EDITOR platform role carries.
//
// Env vars honoured: E2E_API_URL or NEXT_PUBLIC_API_URL (apiBase),
// ACADEMY_SEED_PASSWORD (default "E2E-Academy-2026!"),
// E2E_AUTH_ENABLED=1 enables login verification after seeding.

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../..',
);

const apiBase = (
  process.env.E2E_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  ''
).replace(/\/$/, '');

const password =
  process.env.ACADEMY_SEED_PASSWORD || 'E2E-Academy-2026!';

const ACADEMY_USERS = [
  {
    role: 'LECTOR',
    email: 'e2e.lector@ccf.local',
    firstName: 'E2E',
    lastName: 'Lector',
    description: 'read-only viewport, no edit/submit permissions',
  },
  {
    role: 'MIEMBRO',
    email: 'e2e.estudiante@ccf.local',
    firstName: 'E2E',
    lastName: 'Estudiante',
    description:
      'student viewport (enroll + submit assessment + forum reply). ' +
      'MIEMBRO is the canonical seeded role with academy:study privileges.',
  },
  {
    role: 'DOCENTE',
    email: 'e2e.maestro@ccf.local',
    firstName: 'E2E',
    lastName: 'Maestro',
    description:
      'editor/Maestro viewport: academy:read + academy:edit (created ' +
      'idempotently because canonical seed only ships 5 roles).',
  },
  {
    role: 'ADMINISTRADOR',
    email: 'e2e.admin@ccf.local',
    firstName: 'E2E',
    lastName: 'Administrador',
    description:
      'admin viewport: full academy manage + archive + audit lifecycle.',
  },
];

if (!apiBase) {
  console.log(
    '[seed-academy-roles] Missing E2E_API_URL/NEXT_PUBLIC_API_URL — skipping seed.',
  );
  process.exit(0);
}

function seedViaPython() {
  const preferred =
    process.env.PYTHON_BIN || path.join(repoRoot, 'venv', 'bin', 'python');
  const pythonBin = fs.existsSync(preferred) ? preferred : 'python3';

  const usersJson = JSON.stringify(ACADEMY_USERS);
  const script = String.raw`
import json
import os
import sys
import uuid

repo_root = os.environ["REPO_ROOT"]
sys.path.insert(0, repo_root)

from backend import models as _models
from backend.core.database import SessionLocal
from backend.core.security import get_password_hash
from backend.management.seed_user_permissions import seed_rol_plataforma
from backend.models_auth import RolPlataforma, Usuario
from backend.models_crm import Persona

users = json.loads(os.environ["ACADEMY_USERS_JSON"])
password = os.environ["ACADEMY_SEED_PASSWORD"]

def ensure_docente(session):
    """Idempotent creation of DOCENTE for the Maestro persona.

    Canonical seed_rol_plataforma only creates 5 roles (ADMINISTRADOR,
    GESTOR, EDITOR, LECTOR, MIEMBRO). DOCENTE is an academy-specific
    editor tier (academy:read + academy:edit) without inheriting crm/edit
    or projects/edit that the generic EDITOR platform role carries.
    Re-running this script is a no-op when DOCENTE already exists.
    """
    existing = (
        session.query(RolPlataforma)
        .filter(RolPlataforma.nombre == "DOCENTE")
        .first()
    )
    if existing is not None:
        return existing
    role = RolPlataforma(
        nombre="DOCENTE",
        permisos={"academy:read": "allow", "academy:edit": "allow"},
    )
    session.add(role)
    session.flush()
    return role


session = SessionLocal()
try:
    seed_rol_plataforma(session)
    ensure_docente(session)

    sede = session.query(_models.Sede).first()
    if sede is None:
        sede = _models.Sede(
            id=uuid.uuid4(),
            nombre="Sede E2E Academy",
            ciudad="Bogota",
            es_activa=True,
        )
        session.add(sede)
        session.flush()

    summary = []
    for u in users:
        role = (
            session.query(RolPlataforma)
            .filter(RolPlataforma.nombre == u["role"])
            .first()
        )
        if role is None:
            raise RuntimeError(
                f"Role {u['role']} not available after ensure_docente/seed_rol_plataforma"
            )

        existing = (
            session.query(Usuario)
            .filter(Usuario.email == u["email"])
            .first()
        )

        if existing is not None:
            persona = (
                session.query(Persona)
                .filter(Persona.id == existing.id)
                .first()
            )
            if persona is None:
                persona = Persona(
                    id=existing.id,
                    first_name=u["firstName"],
                    last_name=u["lastName"],
                    email=u["email"],
                    sede_id=sede.id,
                )
                session.add(persona)
            else:
                persona.first_name = u["firstName"]
                persona.last_name = u["lastName"]
                persona.sede_id = sede.id

            existing.sede_id = sede.id
            existing.rol_plataforma_id = role.id
            existing.password_hash = get_password_hash(password)
            existing.is_active = True
            existing.is_email_verified = True
            session.commit()
            summary.append(f"updated {u['role']} -> {existing.id}")
        else:
            persona = Persona(
                id=uuid.uuid4(),
                first_name=u["firstName"],
                last_name=u["lastName"],
                email=u["email"],
                sede_id=sede.id,
            )
            session.add(persona)
            session.flush()

            user = Usuario(
                id=persona.id,
                sede_id=sede.id,
                username=u["email"].split("@")[0],
                email=u["email"],
                password_hash=get_password_hash(password),
                rol_plataforma_id=role.id,
                is_active=True,
                is_email_verified=True,
            )
            session.add(user)
            session.commit()
            summary.append(f"created {u['role']} -> {user.id}")

    # Audit: confirm the global admin seeded by seed-auth-user.mjs is
    # untouched ("wipe-and-rebuild" regression would be loud).
    # assert count == 1 — a regression that wipes the global admin
    # would surface as SystemExit(1) and fail the pytest gate.
    global_admin_count = (
        session.query(Usuario)
        .filter(Usuario.email == "e2e.admin@ccf.local")
        .count()
    )
    if global_admin_count != 1:
        raise RuntimeError(
            "Audit FAILED: e2e.admin@ccf.local count="
            + str(global_admin_count)
            + ", expected 1 (seed-academy-roles must not wipe global admin)."
        )
    print("[seed-academy-roles] audit: e2e.admin count=" + str(global_admin_count) + " (PASS)")

    print("[seed-academy-roles] " + "; ".join(summary))
finally:
    session.close()
`;

  const result = spawnSync(pythonBin, ['-c', script], {
    cwd: repoRoot,
    env: {
      ...process.env,
      REPO_ROOT: repoRoot,
      ACADEMY_USERS_JSON: usersJson,
      ACADEMY_SEED_PASSWORD: password,
    },
    encoding: 'utf8',
  });

  if (result.status !== 0) {
    throw new Error(
      `[seed-academy-roles] Python seed failed: ${result.stderr || result.stdout || 'unknown error'}`,
    );
  }
  return result.stdout;
}

async function verifyLogin() {
  const probes = [
    { email: 'e2e.lector@ccf.local' },
    { email: 'e2e.estudiante@ccf.local' },
    { email: 'e2e.maestro@ccf.local' },
    { email: 'e2e.admin@ccf.local' },
  ];
  const failures = [];
  for (const probe of probes) {
    const response = await fetch(`${apiBase}/v3/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ email: probe.email, password }),
    });
    if (!response.ok) {
      failures.push(`${probe.email} -> HTTP ${response.status}`);
    }
  }
  if (failures.length > 0) {
    throw new Error(
      `[seed-academy-roles] Login verification failed: ${failures.join('; ')}`,
    );
  }
}

async function main() {
  try {
    const seedOutput = seedViaPython();
    process.stdout.write(seedOutput || '');
    await verifyLogin();
    console.log('[seed-academy-roles] 4 academy users seeded and validated.');
  } catch (error) {
    console.error(error);
    process.exit(1);
  }
}

await main();
