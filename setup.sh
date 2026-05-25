#!/bin/bash

set -e

echo "======================================="
echo " Pi Dev Stack Installer"
echo "======================================="

echo "Updating system..."
sudo apt update && sudo apt upgrade -y

echo "Installing dependencies..."
sudo apt install -y curl git tmux ca-certificates

if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi

sudo usermod -aG docker "$USER"

DOCKER_CMD="docker"
if ! docker ps >/dev/null 2>&1; then
  echo "Current shell cannot access Docker yet. Using sudo for this run."
  DOCKER_CMD="sudo docker"
fi

if ! $DOCKER_CMD compose version >/dev/null 2>&1; then
  echo "Installing Docker Compose plugin..."
  sudo apt install -y docker-compose-plugin
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Installing cloudflared..."
  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
  sudo dpkg -i cloudflared.deb
  rm -f cloudflared.deb
fi

mkdir -p data/postgres
mkdir -p data/redis
mkdir -p data/n8n
mkdir -p data/ollama
mkdir -p data/open-webui
mkdir -p data/portainer
mkdir -p logs

echo "Fixing container data permissions..."
sudo chown -R 1000:1000 data/n8n
sudo chown -R 999:999 data/postgres || true
sudo chown -R 999:999 data/redis || true
sudo chown -R 0:0 data/ollama data/open-webui data/portainer || true

if [ ! -f .env ]; then
  cp .env.example .env
fi

echo "Starting Docker services..."
$DOCKER_CMD compose up -d

sleep 10

chmod +x tunnel.sh
chmod +x validate.sh

DOCKER_CMD="$DOCKER_CMD" ./validate.sh

nohup ./tunnel.sh > logs/tunnel-runtime.log 2>&1 &

echo ""
echo "======================================="
echo " Stack deployment complete"
echo "======================================="
echo "Use: docker compose ps"
echo "Use: docker compose logs -f"
echo "If docker permission fails, logout/login or run: newgrp docker"
echo "======================================="
