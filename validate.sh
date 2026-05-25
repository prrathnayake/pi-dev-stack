#!/bin/bash

DOCKER_CMD="${DOCKER_CMD:-docker}"

echo "Running validation checks..."

if command -v docker >/dev/null 2>&1; then
  echo "[OK] Docker installed"
else
  echo "[ERROR] Docker missing"
fi

if ! $DOCKER_CMD ps >/dev/null 2>&1; then
  if sudo docker ps >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
    echo "[WARN] Using sudo docker because current shell has no Docker group access"
  else
    echo "[ERROR] Docker daemon not accessible"
  fi
fi

if $DOCKER_CMD compose version >/dev/null 2>&1; then
  echo "[OK] Docker Compose installed"
else
  echo "[ERROR] Docker Compose missing"
fi

if command -v cloudflared >/dev/null 2>&1; then
  echo "[OK] cloudflared installed"
else
  echo "[ERROR] cloudflared missing"
fi

if $DOCKER_CMD compose config >/dev/null 2>&1; then
  echo "[OK] docker-compose.yml valid"
else
  echo "[ERROR] docker-compose.yml invalid"
fi

SERVICES=$($DOCKER_CMD compose ps --services 2>/dev/null || true)

echo ""
echo "Running services:"
echo "$SERVICES"
