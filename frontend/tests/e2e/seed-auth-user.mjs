import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const apiBase = (process.env.E2E_API_URL || process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');
const email = process.env.E2E_EMAIL || '';
const password = process.env.E2E_PASSWORD || '';
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');

if (!apiBase || !email || !password) {
  console.log('[seed-auth-user] Missing env vars, skipping seed.');
  process.exit(0);
}

async function tryLogin() {
  const response = await fetch(`${apiBase}/v3/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  return response.ok;
}

function seedViaPython() {
  const script = String.raw`
import os
import sys
import uuid

repo_root = os.environ["REPO_ROOT"]
sys.path.insert(0, repo_root)

from backend import models as _models
from backend.core.database import SessionLocal
from backend.core.security import get_password_hash
from backend.models_auth import RolPlataforma, Usuario
from backend.models_crm import Persona

email = os.environ["E2E_EMAIL"]
password = os.environ["E2E_PASSWORD"]

session = SessionLocal()
try:
    existing = session.query(Usuario).filter(Usuario.email == email).first()
    if existing is not None:
        print("already-seeded")
    else:
        persona = Persona(id=uuid.uuid4(), first_name="E2E", last_name="User", email=email)
        session.add(persona)
        session.flush()

        role = session.query(RolPlataforma).filter(RolPlataforma.nombre == "ADMIN").first()
        if role is None:
            role = RolPlataforma(id=uuid.uuid4(), nombre="ADMIN", permisos={"*": "allow"})
            session.add(role)
            session.flush()

        sede = session.query(_models.Sede).first()
        if sede is None:
            sede = _models.Sede(id=uuid.uuid4(), nombre="Sede E2E", ciudad="Bogota", es_activa=True)
            session.add(sede)
            session.flush()

        persona.sede_id = sede.id
        user = Usuario(
            id=persona.id,
            sede_id=sede.id,
            username=email.split("@")[0],
            email=email,
            password_hash=get_password_hash(password),
            rol_plataforma_id=role.id,
            is_active=True,
            is_email_verified=True,
        )
        session.add(user)
        session.commit()
        print("seeded", user.id)
finally:
    session.close()
`;

  const result = spawnSync('python3', ['-c', script], {
    cwd: repoRoot,
    env: {
      ...process.env,
      REPO_ROOT: repoRoot,
      E2E_EMAIL: email,
      E2E_PASSWORD: password,
    },
    encoding: 'utf8',
  });

  if (result.status !== 0) {
    throw new Error(`[seed-auth-user] Python seed failed: ${result.stderr || result.stdout || 'unknown error'}`);
  }
}

async function main() {
  try {
    const loginOk = await tryLogin();
    if (loginOk) {
      console.log('[seed-auth-user] User already valid.');
      return;
    }

    seedViaPython();
    const loginAfterSeed = await tryLogin();
    if (!loginAfterSeed) {
      throw new Error('[seed-auth-user] Login still failing after local seed.');
    }
    console.log('[seed-auth-user] User created and validated.');
  } catch (error) {
    console.error(error);
    process.exit(1);
  }
}

await main();
