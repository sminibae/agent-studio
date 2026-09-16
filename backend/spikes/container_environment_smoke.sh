#!/usr/bin/env bash
set -euo pipefail

# Manual, credential-free Linux container smoke for a named user venv and dotenv.
# The image digest is pinned so the executable environment does not drift.
spike_image='python:3.13-alpine@sha256:7415fbc3c9e4979cc717d92377ab2bc7b2b4a2af1ac03cc52b5f3f88efedaf3a'
spike_dir=$(mktemp -d "${TMPDIR:-/tmp}/agent-studio-container-spike.XXXXXX")
trap 'rm -rf "$spike_dir"' EXIT
chmod 777 "$spike_dir"

cat > "$spike_dir/.env.weather" <<'EOF'
OPENAI_API_KEY=fake-user-key
EOF
cat > "$spike_dir/asset.py" <<'PY'
import os
import socket
from pathlib import Path

assert os.environ["OPENAI_API_KEY"] == "fake-user-key"
assert "AGENT_STUDIO_DATABASE_URL" not in os.environ
assert not Path("/work/.git").exists()
assert not Path("/work/other-owner-secret").exists()
try:
    socket.create_connection(("1.1.1.1", 53), timeout=1)
except OSError:
    pass
else:
    raise AssertionError("network unexpectedly available")
system_prompt = "isolated prompt"
PY
echo 'other-owner-secret' > "$spike_dir/other-owner-secret"
chmod 600 "$spike_dir/.env.weather"
chmod 644 "$spike_dir/asset.py"

docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 32 --memory 256m \
  --user 65534:65534 --tmpfs /tmp:rw,nosuid,nodev,size=16m \
  -v "$spike_dir:/user:rw" "$spike_image" \
  python -m venv /user/weather-py

result=$(docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 32 --memory 128m \
  --user 65534:65534 --tmpfs /tmp:rw,nosuid,nodev,size=16m \
  --env-file "$spike_dir/.env.weather" \
  -v "$spike_dir/weather-py:/venv:ro" \
  -v "$spike_dir/asset.py:/work/asset.py:ro" \
  "$spike_image" /venv/bin/python -I -c \
  'import runpy; print(runpy.run_path("/work/asset.py")["system_prompt"])')
test "$result" = 'isolated prompt'
printf 'container environment smoke passed\n'
