module.exports = {
  apps: [
    // ── CCF Backend ─────────────────────────────────────────
    {
      name: "ccf-backend-staging",
      cwd: "/root/ccf",
      script: "bash",
      args: "-c PYTHONPATH=. /root/ccf/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      max_memory_restart: "500M",
      env: {
        PYTHONPATH: ".",
        ENV_FILE: "backend/.env",
        NODE_ENV: "production",
      },
    },

    // ── CCF Frontend ────────────────────────────────────────
    {
      name: "ccf-frontend-staging",
      cwd: "/root/ccf/frontend",
      script: "npm",
      args: "run start -- -p 3002 -H 127.0.0.1",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
    },

    // ── SeaweedFS ───────────────────────────────────────────
    {
      name: "seaweedfs",
      script: "/root/ccf/start_seaweed.sh",
      interpreter: "bash",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
    },

    // ── Free Claude Code ────────────────────────────────────
    {
      name: "fcc-server",
      script: "/root/.local/bin/fcc-server",
      args: "--host 127.0.0.1",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
    },
  ],
};
