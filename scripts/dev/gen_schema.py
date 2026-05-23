#!/usr/bin/env python3
"""Generate master_schema.sql from model definitions."""
import os


def write_schema():
    path = "/root/ccf/master_schema.sql"
    parts = []
    
    # Header
    parts.append("""-- ============================================================================
-- master_schema.sql
-- DDL completo para SQLite generado a partir de los modelos Python (models_*.py)
-- Proyecto: CCF (Church Management System)
-- Fecha: 2026-05-21
-- ============================================================================
-- NOTA: SQLite no soporta FOREIGN KEY por defecto. Se recomienda habilitar
--       PRAGMA foreign_keys = ON; al abrir la conexion.
-- ============================================================================

BEGIN TRANSACTION;
""")
    
    # Section 1
    parts.append("""
-- ============================================================================
-- 1. IDENTITY, GAMIFICATION & UI  (models_identity.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS roles (
    role_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name           VARCHAR(50) NOT NULL UNIQUE,
    permissions    TEXT
);

CREATE TABLE IF NOT EXISTS levels (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  VARCHAR(50) NOT NULL UNIQUE,
    min_xp INTEGER DEFAULT 0,
    icon_key VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS users (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    username          VARCHAR(50) NOT NULL UNIQUE,
    email             VARCHAR(100) NOT NULL UNIQUE,
    password_hash     TEXT NOT NULL,
    role_id           INTEGER REFERENCES roles(role_id),
    role              VARCHAR(20) DEFAULT 'estudiante',
    xp                INTEGER DEFAULT 0,
    current_level_id  INTEGER REFERENCES levels(id),
    is_active         INTEGER DEFAULT 1,
    is_email_verified INTEGER DEFAULT 0,
    created_at        DATETIME DEFAULT (datetime('now')),
    updated_at        DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);
CREATE INDEX IF NOT EXISTS ix_users_xp ON users(xp);
CREATE INDEX IF NOT EXISTS ix_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS ix_users_is_email_verified ON users(is_email_verified);
CREATE INDEX IF NOT EXISTS ix_users_created_at ON users(created_at);
""")
    
    with open(path, "w") as f:
        f.write("
".join(parts))
    print(f"Written {len(parts)} parts to {path}")

write_schema()
