#!/bin/sh
set -eu

api_port=${AGENT_STUDIO_E2E_API_PORT:-18000}
web_port=${AGENT_STUDIO_E2E_WEB_PORT:-13000}
api_log=$(mktemp)
web_log=$(mktemp)
api_pid=""
web_pid=""

cleanup() {
  result=$?
  if [ -n "$web_pid" ]; then kill "$web_pid" 2>/dev/null || true; fi
  if [ -n "$api_pid" ]; then kill "$api_pid" 2>/dev/null || true; fi
  wait "$web_pid" 2>/dev/null || true
  wait "$api_pid" 2>/dev/null || true
  if [ "$result" -ne 0 ]; then
    sed -n '1,160p' "$api_log"
    sed -n '1,160p' "$web_log"
  fi
  rm -f "$api_log" "$web_log"
  exit "$result"
}
trap cleanup EXIT INT TERM

AGENT_STUDIO_API_URL="http://127.0.0.1:$api_port" \
  pnpm --dir frontend build >"$web_log" 2>&1

uv run --project backend uvicorn agent_studio.bootstrap.api:app \
  --host 127.0.0.1 --port "$api_port" >"$api_log" 2>&1 &
api_pid=$!

AGENT_STUDIO_API_URL="http://127.0.0.1:$api_port" \
  pnpm --dir frontend start --port "$web_port" >>"$web_log" 2>&1 &
web_pid=$!

attempt=0
until curl --fail --silent "http://127.0.0.1:$web_port/api/v1/health/live" >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    exit 1
  fi
  sleep 1
done

curl --fail --silent "http://127.0.0.1:$web_port/api/v1/health/ready" >/dev/null
curl --fail --silent "http://127.0.0.1:$web_port/api/v1/me" \
  | grep --quiet '"subject":"local-developer"'
