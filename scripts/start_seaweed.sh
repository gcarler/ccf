#!/usr/bin/env bash
/usr/local/bin/weed server \
  -ip=127.0.0.1 \
  -s3 \
  -dir=/root/ccf/storage \
  -s3.port=8333 \
  -s3.config=/root/ccf/seaweed_s3.json
