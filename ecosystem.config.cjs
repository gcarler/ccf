module.exports = {
  apps: [
    {
      name: "ccf-backend-staging",
      cwd: "/root/ccf",
      script: "/root/ccf/venv/bin/uvicorn",
      interpreter: "/root/ccf/venv/bin/python3",
      args: "backend.main:app --host 0.0.0.0 --port 8000 --reload",
    },
    {
      name: "ccf-frontend-staging",
      cwd: "/root/ccf/frontend",
      script: "/root/ccf/frontend/node_modules/next/dist/bin/next",
      args: "start --port 3002",
    },
  ],
};
