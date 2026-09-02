#!/usr/bin/env bash
set -euo pipefail

readonly MODE="${1:-}"
readonly DEBUG="${BIBLIOSLEUTH_TEST_DEBUG:-0}"
readonly CONTAINER="bibliosleuth-${MODE:-unknown}-test-${$}"
readonly TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/bibliosleuth-${MODE:-local}.XXXXXX")"
readonly OLLAMA_IMAGE="ollama/ollama@sha256:020e4134285e2ef4d8fd801234176de3b4faadc992a3eb06c8e66a2f9d4c4ba2"
readonly LLAMA_IMAGE="ghcr.io/ggml-org/llama.cpp@sha256:bdce328e7152af01fc8724ef63ebefa1f39639fb6250731ca4fa6af04e1690b6"
readonly GGUF_REVISION="9217f5db79a29953eb74d5343926648285ec7e67"
readonly GGUF_FILE="qwen2.5-0.5b-instruct-q4_k_m.gguf"
readonly GGUF_SHA256="74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"

debug() {
  if [[ "$DEBUG" == "1" ]]; then
    echo "[Local model test] $*"
  fi
}

cleanup() {
  debug "Stopping and removing container: $CONTAINER"
  if [[ "$MODE" == "ollama" ]]; then
    docker exec "$CONTAINER" sh -c 'chmod -R a+rwX /root/.ollama' >/dev/null 2>&1 || true
  fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  rm -rf "$TEMP_DIR"
  debug "Removed temporary model storage: $TEMP_DIR"
}
trap cleanup EXIT INT TERM

if [[ "$MODE" != "ollama" && "$MODE" != "openai-compatible" ]]; then
  echo "Usage: $0 ollama|openai-compatible" >&2
  exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for the local-model integration test." >&2
  exit 2
fi

if [[ "$MODE" == "ollama" ]]; then
  model="qwen3:0.6b"
  provider="ollama"
  debug "Starting pinned Ollama container: $CONTAINER"
  docker run --detach --rm \
    --name "$CONTAINER" \
    --publish 127.0.0.1::11434 \
    --volume "$TEMP_DIR:/root/.ollama" \
    "$OLLAMA_IMAGE" >/dev/null
  internal_port="11434"
else
  model="bibliosleuth-test"
  provider="lmstudio"
  mkdir -p "$TEMP_DIR/models"
  debug "Downloading pinned 0.5B Qwen GGUF model"
  curl --fail --location --silent --show-error \
    "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/$GGUF_REVISION/$GGUF_FILE" \
    --output "$TEMP_DIR/models/$GGUF_FILE"
  printf '%s  %s\n' "$GGUF_SHA256" "$TEMP_DIR/models/$GGUF_FILE" | shasum -a 256 -c -
  debug "Starting pinned llama.cpp OpenAI-compatible server: $CONTAINER"
  docker run --detach --rm \
    --name "$CONTAINER" \
    --publish 127.0.0.1::8080 \
    --volume "$TEMP_DIR/models:/models:ro" \
    "$LLAMA_IMAGE" \
    -m "/models/$GGUF_FILE" --host 0.0.0.0 --port 8080 \
    --alias "$model" --ctx-size 2048 >/dev/null
  internal_port="8080"
fi

port="$(docker port "$CONTAINER" "$internal_port/tcp" | sed -n '1s/.*://p')"
if [[ ! "$port" =~ ^[0-9]+$ ]]; then
  echo "Docker did not publish the local-model test port." >&2
  docker logs "$CONTAINER" >&2 || true
  exit 1
fi
readonly url="http://127.0.0.1:${port}"
debug "Published endpoint: $url"

ready=false
for _ in {1..120}; do
  if curl --fail --silent --show-error "$url/v1/models" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  echo "The local inference server did not become ready within 120 seconds." >&2
  docker logs "$CONTAINER" >&2 || true
  exit 1
fi

if [[ "$MODE" == "ollama" ]]; then
  debug "Pulling lightweight model: $model"
  pull_response="$(curl --fail --silent --show-error \
    --header 'Content-Type: application/json' \
    --data "{\"model\":\"$model\",\"stream\":false}" \
    "$url/api/pull")"
  debug "Model pull response: $pull_response"
fi
debug "Model server is ready"

pytest_args=(-q)
if [[ "$DEBUG" == "1" ]]; then
  pytest_args=(-vv -s)
fi
BIBLIOSLEUTH_TEST_LOCAL_URL="$url/v1" \
  BIBLIOSLEUTH_TEST_LOCAL_MODEL="$model" \
  BIBLIOSLEUTH_TEST_LOCAL_PROVIDER="$provider" \
  BIBLIOSLEUTH_TEST_DEBUG="$DEBUG" \
  "${PYTHON:-python3}" -m pytest "${pytest_args[@]}" \
  tests/integration/test_local_model_live.py
