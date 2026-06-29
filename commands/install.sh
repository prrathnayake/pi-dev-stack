#!/bin/bash
# commands/install.sh — homelab install [--global]

cmd_install() {
  local global=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --global) global=1 ;;
      --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab install [--global]

Install system dependencies, create data directories, fix permissions,
copy .env from example, and start core stack.

  --global    Symlink homelab to /usr/local/bin/homelab
EOF
      *) log_error "Unknown option: $1"; return 1 ;;
    esac
    shift
  done

  if [ -n "$global" ]; then
    chmod +x "$ROOT_DIR/homelab"
    sudo ln -sf "$ROOT_DIR/homelab" /usr/local/bin/homelab
    echo "Installed global command: homelab"
    return 0
  fi

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

  local dc="docker"
  if ! docker ps >/dev/null 2>&1; then
    echo "Current shell cannot access Docker yet. Using sudo for this run."
    dc="sudo docker"
  fi

  if ! $dc compose version >/dev/null 2>&1; then
    echo "Installing Docker Compose plugin..."
    sudo apt install -y docker-compose-plugin
  fi

  if ! command -v cloudflared >/dev/null 2>&1; then
    echo "Installing cloudflared..."
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
    sudo dpkg -i cloudflared.deb
    rm -f cloudflared.deb
  fi

  echo "Creating data directories..."
  mkdir -p data/postgres data/redis data/n8n data/ollama data/open-webui data/portainer
  mkdir -p data/plex/config data/dockge data/dockge/stacks
  mkdir -p data/pihole/etc-pihole data/pihole/etc-dnsmasq.d
  mkdir -p data/home-assistant data/uptime-kuma
  mkdir -p media logs state .local-state

  echo "Fixing container data permissions..."
  sudo chown -R 1000:1000 data/n8n data/plex/config data/dockge media 2>/dev/null || true
  sudo chown -R 999:999 data/postgres data/redis 2>/dev/null || true
  sudo chown -R 0:0 data/ollama data/open-webui data/portainer 2>/dev/null || true

  if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example — edit secrets before exposing services"
  fi

  ensure_executable

  echo "Starting Docker services..."
  $dc compose up -d

  sleep 10

  echo ""
  echo "======================================="
  echo " Stack deployment complete"
  echo "======================================="
  echo "Use: homelab status"
  echo "Use: homelab logs"
  echo "If docker permission fails, logout/login or run: newgrp docker"
  echo "======================================="
}
