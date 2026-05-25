module.exports = {
  apps: [
    {
      name: "ccf-backend-staging",
      cwd: "/root/ccf",
      script: "/root/ccf/venv/bin/python3",
      args: "-m uvicorn backend.main:app --host 0.0.0.0 --port 8000",
      interpreter: "none",
      exec_mode: "fork",
      autorestart: true,
      max_restarts: 5,
    },
    {
      name: "ccf-frontend-staging",
      cwd: "/root/ccf/frontend",
      script: "node_modules/next/dist/bin/next",
      args: "start --port 3002",
      interpreter: "none",
      exec_mode: "fork",
      autorestart: true,
    },
  ],
};
