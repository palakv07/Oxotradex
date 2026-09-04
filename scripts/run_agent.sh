#!/usr/bin/env bash
# ==============================================================================
# Oxotradex: Autonomous Options Alpha Agent - Unix/Linux/macOS Runner
# ==============================================================================

set -e

echo "[INFO] Starting Oxotradex Autonomous Options Alpha Agent..."

if [ ! -f .env ]; then
    echo "[WARNING] .env file not found. Copying .env.example to .env..."
    cp .env.example .env
    echo "[IMPORTANT] Please update .env with your Alpaca Paper API keys."
fi

python src/main.py "$@"
