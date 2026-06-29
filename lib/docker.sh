#!/bin/bash
# lib/docker.sh — Docker command detection and compose helpers

: "${DOCKER_CMD:=}"

_detect_docker() {
  [ -n "$DOCKER_CMD" ] && return 0
  if docker ps >/dev/null 2>&1; then
    DOCKER_CMD="docker"
  elif sudo docker ps >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
  else
    DOCKER_CMD="docker"
  fi
}
_detect_docker

compose_for_service() {
  local profile
  profile=$(registry_profile "$1" 2>/dev/null) || profile="core"
  if [ "$profile" = "extras" ]; then
    echo "$DOCKER_CMD compose --profile extras"
  else
    echo "$DOCKER_CMD compose"
  fi
}

container_name() { echo "pi-$1"; }

docker_available() { $DOCKER_CMD ps >/dev/null 2>&1; }
compose_available() { $DOCKER_CMD compose version >/dev/null 2>&1; }
