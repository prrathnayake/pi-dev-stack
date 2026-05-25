#!/bin/bash

echo "Running validation checks..."

if command -v docker >/dev/null 2>&1; then
  echo "[OK] Docker installed"
else
  echo "[ERROR] Docker missing"
fi

if docker compose version >/dev/null 2>&1; then
  echo "[OK] Docker Compose installed"
else
  echo "[ERROR] Docker Compose missing"
fi

if command -v cloudflared >/dev/null 2>&1; then
  echo "[OK] cloudflared installed"
else
  echo "[ERROR] cloudflared missing"
fi

if docker compose config >/dev/null 2>&1; then
  echo "[OK] docker-compose.yml valid"
else
  echo "[ERROR] docker-compose.yml invalid"
fi

SERVICES=$(docker compose ps --services 2>/dev/null || true)

echo ""
echo "Running services:"
echo "$SERVICES"
