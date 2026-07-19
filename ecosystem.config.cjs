// ecosystem.config.cjs — Fuente autoritativa de procesos PM2 para CCF.
//
// Stack gestionado por PM2:
//   - ccf-backend-staging   (FastAPI/uvicorn  :8000)
//   - ccf-frontend-staging  (Next.js start    :3000)
//   - seaweedfs             (S3 compatible    :8333)
//   - fcc-server            (free-claude-code auxiliary)
//
// Defensas anti-loop EADDRINUSE (causa raíz de los 1277 restarts históricos):
//   - restart_delay          : pausa entre reintentos (sin backoff cero)
//   - exp_backoff_restart_delay: base 1000ms → → 2000 → 4000 → ... hasta 15s max
//   - max_restarts           : corto un loop declarado antes de llenar el disco
//   - min_uptime             : solo cuenta como "estable" si vive >= 10s
//   - kill_timeout           : SIGTERM → 8s de gracia → SIGKILL (deja drenar)
//
// Al editar este archivo, recargar con:
//   pm2 reload /root/ccf/ecosystem.config.cjs --env production
//   pm2 save     # persistir el dump.pm2
//
// NOTA: NO existe ecosystem.config.js (este .cjs es fuente única).

module.exports = {
  apps: [
    // ── CCF Backend (FastAPI + uvicorn) ───────────────────────
    {
      name: "ccf-backend-staging",
      cwd: "/root/ccf",
      script: "./scripts/start_backend.sh",
      interpreter: "bash",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      max_memory_restart: "500M",
      max_restarts: 10,
      min_uptime: "10s",
      restart_delay: 1000,
      exp_backoff_restart_delay: 1000,
      kill_timeout: 8000,
    },

    // ── CCF Frontend (Next.js start) ─────────────────────────
    // Importante: usa `npm run start` (alias de `next start`) y bindea solo
    // 127.0.0.1 para que Nginx siga siendo el único punto de exposición.
    {
      name: "ccf-frontend-staging",
      cwd: "/root/ccf/frontend",
      script: "npm",
      args: "run start -- -p 3000 -H 127.0.0.1",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      max_memory_restart: "700M",
      max_restarts: 10,
      min_uptime: "10s",
      restart_delay: 1000,
      exp_backoff_restart_delay: 1000,
      kill_timeout: 8000,
    },

    // ── SeaweedFS (almacenamiento S3 compatible) ────────────
    {
      name: "seaweedfs",
      script: "/root/ccf/scripts/start_seaweed.sh",
      interpreter: "bash",
      cwd: "/root/ccf",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      max_restarts: 5,
      min_uptime: "10s",
      restart_delay: 2000,
      exp_backoff_restart_delay: 1000,
      kill_timeout: 8000,
    },

    // ── Free Claude Code server ─────────────────────────────
    {
      name: "fcc-server",
      script: "/root/.local/bin/fcc-server",
      interpreter: "/root/.local/share/uv/tools/free-claude-code/bin/python",
      args: "--host 127.0.0.1",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      max_restarts: 5,
      min_uptime: "10s",
      restart_delay: 2000,
      exp_backoff_restart_delay: 1000,
      kill_timeout: 8000,
    },
  ],
};
