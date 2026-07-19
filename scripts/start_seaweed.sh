#!/usr/bin/env bash
set -euo pipefail

# Asegura que el directorio de storage existe con permisos estrictos.
# SeaweedFS mantiene todos sus datos aqui: volumenes, filer (leveldb), snapshots.
install -d -m 0750 /root/ccf/storage

# Args del subcomando `weed server`:
#   -ip=127.0.0.1     — solo escucha en loopback (Nginx u otros servicios locales
#                       haran de proxy si se necesita exponer).
#   -s3               — activa el API S3-compatible en el S3 port.
#   -dir=/root/ccf/storage — donde se guardan volumenes y filer store.
#   -s3.port=8333     — puerto HTTP del S3 API (segun MEMORY: 8333).
#   -volume.minFreeSpace=10 — exige >=10% libre antes de asignar nuevos volumenes.
#                       Previene el falso "disk free 0.00%" historico (mayo 2026):
#                       sin este flag, SeaweedFS 4.x calcula mal el free space
#                       en algunos filesystems y reporta 0%, aunque haya 300GB libres.
#                       Con 10%, el master solo crece volumenes si hay margen real.
args=(
  server
  -ip=127.0.0.1
  -s3
  -dir=/root/ccf/storage
  -s3.port=8333
  -volume.minFreeSpace=10
)

# Si existe config IAM separada (buckets/credentials/ACL), la cargamos.
# Sin este archivo, SeaweedFS S3 funciona en modo anonimo (OK en 127.0.0.1,
# NO OK si se bindea a 0.0.0.0 o se expone via Nginx).
if [[ -f /root/ccf/seaweed_s3.json ]]; then
  args+=(-s3.config=/root/ccf/seaweed_s3.json)
fi

exec /usr/local/bin/weed "${args[@]}"
