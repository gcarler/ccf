#!/usr/bin/env bash
set -euo pipefail

install -d -m 0750 /root/ccf/storage

args=(
  server
  -ip=127.0.0.1
  -s3
  -dir=/root/ccf/storage
  -s3.port=8333
)

if [[ -f /root/ccf/seaweed_s3.json ]]; then
  args+=(-s3.config=/root/ccf/seaweed_s3.json)
fi

exec /usr/local/bin/weed "${args[@]}"
