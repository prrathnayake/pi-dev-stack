#!/bin/bash

set -e

DOCKER_CMD="${DOCKER_CMD:-docker}"

if ! $DOCKER_CMD ps >/dev/null 2>&1; then
  if sudo docker ps >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
  else
    echo "Docker is not available. Skipping Docker shutdown."
  fi
fi

echo "======================================="
echo " Stopping Pi Dev Stack"
echo "======================================="

echo "Stopping Cloudflare quick tunnels..."
pkill -f 'cloudflared tunnel --url' || true
pkill -f './tunnel.sh' || true

echo "Stopping Docker services..."
if $DOCKER_CMD ps >/dev/null 2>&1; then
  $DOCKER_CMD compose down --remove-orphans
fi

echo ""
echo "Stack stopped."
echo ""
echo "To remove containers + volumes created by Compose, run:"
echo "  ./stop.sh --volumes"
echo ""
echo "To wipe all local app data, run:"
echo "  ./stop.sh --wipe-data"
echo "======================================="

if [ "${1:-}" = "--volumes" ]; then
  echo "Removing Compose volumes..."
  $DOCKER_CMD compose down -v --remove-orphans || true
fi

if [ "${1:-}" = "--wipe-data" ]; then
  echo "WARNING: wiping ./data and ./logs"
  $DOCKER_CMD compose down -v --remove-orphans || true
  sudo rm -rf data logs
  echo "Local data wiped."
fi
