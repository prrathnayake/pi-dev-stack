#!/bin/bash
# lib/output.sh — output formatting helpers (text + JSON)

: "${OUTPUT_FORMAT:=text}"

json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}

kv() {
  if [ "$OUTPUT_FORMAT" = "json" ]; then
    printf '"%s": "%s"\n' "$(json_escape "$1")" "$(json_escape "$2")"
  else
    printf '%s: %s\n' "$1" "$2"
  fi
}

json_string_array() {
  local first=1 line
  printf '['
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    [ $first -eq 0 ] && printf ','
    first=0
    printf '"%s"' "$(json_escape "$line")"
  done
  printf ']\n'
}

json_kv_array() {
  local first=1 key val
  printf '['
  while IFS=$'\t' read -r key val; do
    [ -z "$key" ] && continue
    [ $first -eq 0 ] && printf ','
    first=0
    printf '{"%s":"%s"}' "$(json_escape "$key")" "$(json_escape "$val")"
  done
  printf ']\n'
}

log_info()  { printf '%s\n' "$*" >&2; }
log_warn()  { printf '[WARN] %s\n' "$*" >&2; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }
log_ok()    { printf '[OK] %s\n' "$*"; }
log_fail()  { printf '[FAIL] %s\n' "$*" >&2; }

section() {
  if [ "$OUTPUT_FORMAT" != "json" ]; then
    printf '\n=== %s ===\n' "$1"
  fi
}

ensure_executable() {
  chmod +x "$ROOT_DIR/homelab" 2>/dev/null || true
}
