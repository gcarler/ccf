#!/bin/bash
cd /root/ccf
export PYTHONPATH=.
export ENV_FILE=backend/.env
exec /root/ccf/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
