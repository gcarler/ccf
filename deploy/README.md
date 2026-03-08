# Deployment Overview

## Docker Images

### Backend

Build from repo root:

```bash
docker build -f backend.Dockerfile -t ghcr.io/ccf/backend:latest .
```

Environment variables (example):

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/ccf_db
REDIS_URL=redis://redis:6379/0
KAFKA_BOOTSTRAP_SERVERS=redpanda:9092
SECRET_KEY=replace-me
ENABLE_OTEL=true
OTEL_ENDPOINT=http://otel-collector:4317
```

### Frontend

```
```

Vars:

```
NEXT_PUBLIC_GRAPHQL_URL=https://api.example.com/graphql
```

## GitHub Actions

`.github/workflows/deploy.yml` builds both images, pushes to GHCR and performs a `helm upgrade`. Required secrets:

- `GHCR_USERNAME`, `GHCR_TOKEN`
- `KUBE_CONFIG` (base64 kubeconfig)
- Optional `HELM_ARGS`

## Helm Chart

Located at `deploy/helm/ccf`. Values to set:

- `backend.image`, `frontend.image`
- `backend.env.SECRET_KEY`, `backend.env.DATABASE_URL`, etc.
- `ingress.hosts.frontend/backend`

Install/upgrade:

```bash
helm upgrade --install ccf deploy/helm/ccf -n ccf --create-namespace \
  --set backend.image=ghcr.io/ccf/backend:v1 \
  --set frontend.image=ghcr.io/ccf/frontend:v1
```

## Backups

Run the management script inside the backend image:

```bash
python -m backend.management.backup_db --dest /var/backups
```

Schedule as a Kubernetes CronJob mounting a PVC for `/var/backups`.
