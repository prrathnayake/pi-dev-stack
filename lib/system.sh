#!/bin/bash
# lib/system.sh — OS detection and system info

OS_ID="unknown"
OS_NAME="unknown"
ARCH="$(uname -m)"

detect_system() {
  OS_ID="unknown"
  OS_NAME="unknown"
  ARCH="$(uname -m)"
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_ID="${ID:-unknown}"
    OS_NAME="${PRETTY_NAME:-unknown}"
  fi
}
detect_system

system_info() {
  if [ "$OUTPUT_FORMAT" = "json" ]; then
    printf '{"os":"%s","arch":"%s"}\n' "$(json_escape "$OS_NAME")" "$(json_escape "$ARCH")"
  else
    printf 'OS: %s\nArchitecture: %s\n' "$OS_NAME" "$ARCH"
  fi
}
