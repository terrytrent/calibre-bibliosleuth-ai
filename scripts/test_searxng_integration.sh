#!/usr/bin/env bash
set -euo pipefail

readonly IMAGE="searxng/searxng@sha256:b36af7984b87191b595bc5301418ed6432c047668a4547ab531a7439b816fac3"
readonly CONTAINER="bibliosleuth-searxng-test-${$}"
readonly TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/bibliosleuth-searxng.XXXXXX")"
readonly DEBUG="${BIBLIOSLEUTH_TEST_DEBUG:-0}"

debug() {
  if [[ "$DEBUG" == "1" ]]; then
    echo "[SearXNG test] $*"
  fi
}

cleanup() {
  debug "Stopping and removing container: $CONTAINER"
  docker exec "$CONTAINER" sh -c 'chmod -R a+rwX /etc/searxng' >/dev/null 2>&1 || true
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  rm -rf "$TEMP_DIR"
  debug "Removed temporary configuration: $TEMP_DIR"
}
trap cleanup EXIT INT TERM

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for the SearXNG integration test." >&2
  exit 2
fi

mkdir -p "$TEMP_DIR/searxng"
debug "Writing temporary configuration: $TEMP_DIR/searxng/settings.yml"
cat >"$TEMP_DIR/searxng/settings.yml" <<'EOF'
use_default_settings: true
server:
  secret_key: "bibliosleuth-disposable-integration-test"
  bind_address: "0.0.0.0"
  port: 8080
  limiter: false
  image_proxy: false
search:
  safe_search: 1
  formats:
    - html
    - json
EOF

debug "Starting container: $CONTAINER"
docker run --detach --rm \
  --name "$CONTAINER" \
  --publish 127.0.0.1::8080 \
  --volume "$TEMP_DIR/searxng:/etc/searxng:rw" \
  "$IMAGE" >/dev/null

port="$(docker port "$CONTAINER" 8080/tcp | sed -n '1s/.*://p')"
if [[ ! "$port" =~ ^[0-9]+$ ]]; then
  echo "Docker did not publish the SearXNG test port." >&2
  docker logs "$CONTAINER" >&2 || true
  exit 1
fi
readonly url="http://127.0.0.1:${port}"
debug "Published endpoint: $url"

ready=false
for _ in {1..60}; do
  if curl --fail --silent --show-error \
      --get --data-urlencode 'q=BiblioSleuth readiness' \
      --data-urlencode 'format=json' "$url/search" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  echo "SearXNG did not become ready within 60 seconds." >&2
  docker logs "$CONTAINER" >&2 || true
  exit 1
fi
debug "JSON search endpoint is ready"

pytest_args=(-q)
if [[ "$DEBUG" == "1" ]]; then
  pytest_args=(-vv -s)
fi
BIBLIOSLEUTH_TEST_SEARXNG_URL="$url" \
  BIBLIOSLEUTH_TEST_DEBUG="$DEBUG" \
  "${PYTHON:-python3}" -m pytest "${pytest_args[@]}" \
  tests/integration/test_searxng_live.py
