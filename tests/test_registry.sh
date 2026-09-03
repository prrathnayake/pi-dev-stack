#!/bin/bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$ROOT_DIR"
OUTPUT_FORMAT=text
. "$ROOT_DIR/lib/output.sh"
. "$ROOT_DIR/lib/registry.sh"

failures=0
fail() { echo "FAIL: $*" >&2; failures=$((failures + 1)); }

mapfile -t registry_services < <(all_services | sort)
mapfile -t compose_services < <(docker compose --project-directory "$ROOT_DIR" --profile extras config --services | sort)

[ "${#registry_services[@]}" -eq "${#compose_services[@]}" ] || \
  fail "registry has ${#registry_services[@]} services; Compose has ${#compose_services[@]}"

for service in "${registry_services[@]}"; do
  printf '%s\n' "${compose_services[@]}" | grep -qx "$service" || fail "$service is missing from Compose"

  profile=$(registry_profile "$service")
  case "$profile" in core|extras) ;; *) fail "$service has invalid profile '$profile'" ;; esac

  tunnel=$(registry_tunnel "$service")
  case "$tunnel" in yes|no) ;; *) fail "$service has invalid tunnel flag '$tunnel'" ;; esac

  port=$(registry_port "$service")
  scheme=$(registry_scheme "$service")
  if [ "$tunnel" = yes ]; then
    [ -n "$port" ] || fail "$service is tunnelable without a port"
    case "$scheme" in http|https) ;; *) fail "$service has invalid tunnel scheme '$scheme'" ;; esac
  fi

  resolve_alias "$service" >/dev/null || fail "$service does not resolve by its canonical name"
done

for service in "${compose_services[@]}"; do
  printf '%s\n' "${registry_services[@]}" | grep -qx "$service" || fail "$service is missing from registry"
done

for group in $(tunnel_groups_list); do
  [ -n "$(tunnel_group_services "$group")" ] || fail "tunnel group '$group' is empty"
done

if [ "$failures" -ne 0 ]; then
  echo "$failures registry test(s) failed" >&2
  exit 1
fi
echo "Registry tests passed (${#registry_services[@]} services)"
