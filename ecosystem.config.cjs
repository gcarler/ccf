module.exports = {
  apps: [
    {
      name: "ccf-backend-staging",
      cwd: "/root/ccf",
      script: "/root/ccf/scripts/start_backend.sh",
      interpreter: "/bin/bash",
      exec_mode: "fork",
      autorestart: true,
      max_restarts: 10,
      min_uptime: "30s",
      kill_timeout: 30000,
    },
    {
      name: "ccf-frontend-staging",
      cwd: "/root/ccf/frontend",
      script: "node_modules/next/dist/bin/next",
      args: "start --port 3000",
      interpreter: "none",
      exec_mode: "fork",
      autorestart: true,
    },
  ],
};
