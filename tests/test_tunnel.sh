#!/bin/bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/bin" "$TMP_DIR/work/logs" "$TMP_DIR/work/state" "$TMP_DIR/work/.local-state"

cat > "$TMP_DIR/bin/docker" <<'EOF'
#!/bin/bash
exit 0
EOF

cat > "$TMP_DIR/bin/curl" <<'EOF'
#!/bin/bash
exit "${MOCK_CURL_EXIT:-0}"
EOF

cat > "$TMP_DIR/bin/cloudflared" <<'EOF'
#!/bin/bash
if [ "${MOCK_CLOUDFLARED_FAIL:-0}" = 1 ]; then
  echo "failed to connect"
  exit 1
fi
echo "https://test-tunnel.trycloudflare.com"
echo "Registered tunnel connection"
trap 'exit 0' TERM INT
while :; do sleep 1; done
EOF

chmod +x "$TMP_DIR/bin/"*
export PATH="$TMP_DIR/bin:$PATH"
export REGISTRY_FILE="$ROOT_DIR/config/services.tsv"
export STATE_FILE="$TMP_DIR/work/state/tunnels.env"
export URL_FILE="$TMP_DIR/work/.local-state/current-urls.txt"
export TUNNEL_PID_DIR="$TMP_DIR/work/state/tunnel-pids"
export OUTPUT_FORMAT=text
export DOCKER_CMD=docker

cd "$TMP_DIR/work" || exit 1
. "$ROOT_DIR/lib/output.sh"
. "$ROOT_DIR/lib/registry.sh"
. "$ROOT_DIR/lib/docker.sh"
. "$ROOT_DIR/commands/tunnel.sh"

failures=0
assert_success() { "$@" || { echo "FAIL: expected success: $*" >&2; failures=$((failures + 1)); }; }
assert_failure() { "$@" && { echo "FAIL: expected failure: $*" >&2; failures=$((failures + 1)); }; return 0; }
assert_contains() {
  case "$1" in *"$2"*) ;; *) echo "FAIL: expected '$2' in '$1'" >&2; failures=$((failures + 1)) ;; esac
}

# Registry coverage: every tunnelable service must have a usable HTTP origin.
while IFS= read -r service; do
  [ -n "$(registry_port "$service")" ] || { echo "FAIL: missing port for $service" >&2; failures=$((failures + 1)); }
  case "$(registry_scheme "$service")" in
    http|https) ;;
    *) echo "FAIL: invalid scheme for $service" >&2; failures=$((failures + 1)) ;;
  esac
done < <(tunnelable)

assert_failure _tunnel_resolve_target postgres
assert_contains "$(_tunnel_resolve_target code)" "service:code-server"

assert_success _tunnel_start_one code-server
assert_contains "$(cat "$STATE_FILE")" "CODE_SERVER_URL=https://test-tunnel.trycloudflare.com"
assert_success _tunnel_pid_running code-server

OUTPUT_FORMAT=json
urls=$(_tunnel_show_urls)
assert_contains "$urls" '"CODE_SERVER_URL":"https://test-tunnel.trycloudflare.com"'
OUTPUT_FORMAT=text

assert_success _tunnel_stop_one code-server quiet
[ ! -s "$STATE_FILE" ] || { echo "FAIL: stop retained stale URL" >&2; failures=$((failures + 1)); }
assert_failure _tunnel_pid_running code-server

MOCK_CLOUDFLARED_FAIL=1
export MOCK_CLOUDFLARED_FAIL
assert_failure _tunnel_start_one n8n
[ ! -s "$STATE_FILE" ] || { echo "FAIL: failed start saved a URL" >&2; failures=$((failures + 1)); }

if [ "$failures" -ne 0 ]; then
  echo "$failures tunnel test(s) failed" >&2
  exit 1
fi
echo "Tunnel tests passed"
