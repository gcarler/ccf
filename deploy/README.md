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
ENVIRONMENT=production
ACCESS_TOKEN_COOKIE_SECURE=true
CORS_ORIGINS=["https://app.example.com"]
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

`.github/workflows/deploy.yml` runs after `CI` succeeds on `main`, builds both images, pushes to GHCR and performs a `helm upgrade` with rollout verification. The Helm release includes a pre-install/pre-upgrade migration Job that runs `alembic upgrade head` before the backend rollout. Required secrets:

- `KUBE_CONFIG` (base64 kubeconfig)
- Optional `HELM_EXTRA_ARGS`

Notes:

- GHCR auth uses GitHub Actions `GITHUB_TOKEN` with `packages: write` permission.
- Deploy jobs are skipped automatically when commits do not touch deploy-relevant paths.

## Helm Chart

Located at `deploy/helm/ccf`. Values to set:

- `backend.image`, `frontend.image`
- `backend.env.DATABASE_URL`, etc.
- `backend.secrets.existingSecret` pointing to a Kubernetes Secret with `SECRET_KEY` and optionally `ENCRYPTION_KEY`
- `ingress.hosts.frontend/backend`

Example secret:

```bash
kubectl create secret generic ccf-backend-secrets -n ccf \
  --from-literal=SECRET_KEY='<strong-random-secret>' \
  --from-literal=ENCRYPTION_KEY='<optional-second-strong-secret>'
```

If you prefer Helm-managed secrets for non-production environments, set:

```yaml
backend:
  secrets:
    create: true
    existingSecret: ""
    secretKey: "<strong-random-secret>"
    encryptionKey: "<optional-second-strong-secret>"
```

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
