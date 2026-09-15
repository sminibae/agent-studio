#!/bin/sh
set -eu

temporary_directory=$(mktemp -d)
cleanup() {
  rm -r "$temporary_directory"
}
trap cleanup EXIT INT TERM

uv run --project backend python backend/scripts/export_openapi.py \
  "$temporary_directory/openapi.json"
pnpm --dir frontend exec openapi-typescript \
  "$temporary_directory/openapi.json" \
  -o "$temporary_directory/schema.ts"
pnpm --dir frontend exec prettier \
  --config .prettierrc.json \
  --write "$temporary_directory/openapi.json" "$temporary_directory/schema.ts" >/dev/null

cmp frontend/openapi.json "$temporary_directory/openapi.json"
cmp frontend/lib/api/generated/schema.ts "$temporary_directory/schema.ts"
