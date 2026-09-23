#!/usr/bin/env bash
set -euo pipefail

# Credential-free smoke for an immutable user venv running the pinned Agents SDK.
spike_image='python:3.13-alpine@sha256:7415fbc3c9e4979cc717d92377ab2bc7b2b4a2af1ac03cc52b5f3f88efedaf3a'
spike_dir=$(mktemp -d "${TMPDIR:-/tmp}/agent-studio-sdk-spike.XXXXXX")
install_name="agent-studio-sdk-install-$$"
missing_name="agent-studio-sdk-missing-$$"
runtime_name="agent-studio-sdk-runtime-$$"
setup_one_name="$runtime_name-one"
setup_two_name="$runtime_name-two"

cleanup() {
  docker rm -f "$install_name" "$missing_name" "$runtime_name" \
    "$setup_one_name" "$setup_two_name" >/dev/null 2>&1 || true
  rm -rf "$spike_dir"
}
trap cleanup EXIT
chmod 777 "$spike_dir"
mkdir -m 777 "$spike_dir/result"

cat > "$spike_dir/.env.weather" <<'EOF'
OPENAI_API_KEY=fake-user-key
OWNER_MARKER=owner-a
EOF
cat > "$spike_dir/tool.py" <<'PY'
import os
from pathlib import Path
from agents import function_tool

assert os.environ["OPENAI_API_KEY"] == "fake-user-key"
assert os.environ["OWNER_MARKER"] == "owner-a"
assert "AGENT_STUDIO_DATABASE_URL" not in os.environ
assert not Path("/work/.git").exists()
assert not Path("/work/other-owner-secret").exists()

@function_tool
async def weather(latitude: float, longitude: float) -> str:
    """Get the weather for coordinates."""
    return f"{latitude},{longitude}: 20 C"

tool = weather
PY
cat > "$spike_dir/prompt.py" <<'PY'
import os

system_prompt = f"weather assistant for {os.environ['OWNER_MARKER']}"
PY
cat > "$spike_dir/contract.json" <<'JSON'
{
  "description": "Get the weather for coordinates.",
  "input_schema": {
    "additionalProperties": false,
    "properties": {
      "latitude": {"title": "Latitude", "type": "number"},
      "longitude": {"title": "Longitude", "type": "number"}
    },
    "required": ["latitude", "longitude"],
    "title": "weather_args",
    "type": "object"
  },
  "name": "weather"
}
JSON
cat > "$spike_dir/wrong-contract.json" <<'JSON'
{"description":"drifted","input_schema":{"type":"object"},"name":"weather"}
JSON

runner_path=$(cd "$(dirname "$0")" && pwd)/container_sdk_runner.py
contract_path=$(cd "$(dirname "$0")/../src/agent_studio/spikes" && pwd)/user_tool_contract.py

docker run --rm --name "$missing_name" --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 32 --memory 128m \
  --user 65534:65534 --tmpfs /tmp:rw,nosuid,nodev,size=16m \
  -v "$runner_path:/runner.py:ro" \
  -v "$contract_path:/user_tool_contract.py:ro" \
  -v "$spike_dir/prompt.py:/work/prompt.py:ro" \
  -v "$spike_dir/tool.py:/work/tool.py:ro" \
  -v "$spike_dir/contract.json:/work/contract.json:ro" \
  -v "$spike_dir/result:/result:rw" \
  "$spike_image" python -I /runner.py \
  /work/prompt.py /work/tool.py /work/contract.json missing /result/missing.json

python3 - "$spike_dir/result/missing.json" <<'PY'
import json
import sys
from pathlib import Path

assert json.loads(Path(sys.argv[1]).read_text()) == {"error": "sdk_unavailable"}
PY

docker run --rm --name "$install_name" --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 64 --memory 512m \
  --user 65534:65534 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  -v "$spike_dir:/user:rw" "$spike_image" sh -c \
  'python -m venv /user/sdk-venv && /user/sdk-venv/bin/pip install --no-cache-dir openai-agents==0.22.2'

docker run --rm --name "$runtime_name" --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 32 --memory 256m \
  --user 65534:65534 --tmpfs /tmp:rw,nosuid,nodev,size=16m \
  --env-file "$spike_dir/.env.weather" \
  -v "$spike_dir/sdk-venv:/venv:ro" \
  -v "$runner_path:/runner.py:ro" \
  -v "$contract_path:/user_tool_contract.py:ro" \
  -v "$spike_dir/prompt.py:/work/prompt.py:ro" \
  -v "$spike_dir/tool.py:/work/tool.py:ro" \
  -v "$spike_dir/wrong-contract.json:/work/contract.json:ro" \
  -v "$spike_dir/result:/result:rw" \
  "$spike_image" /venv/bin/python -I /runner.py \
  /work/prompt.py /work/tool.py /work/contract.json drifted /result/mismatch.json

python3 - "$spike_dir/result/mismatch.json" <<'PY'
import json
import sys
from pathlib import Path

assert json.loads(Path(sys.argv[1]).read_text()) == {"error": "tool_contract_mismatch"}
PY

run_setup() {
  setup_name=$1
  setup_description=$2
  result_name=$3
  docker run --rm --name "$setup_name" --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 32 --memory 256m \
  --user 65534:65534 --tmpfs /tmp:rw,nosuid,nodev,size=16m \
  --env-file "$spike_dir/.env.weather" \
  -v "$spike_dir/sdk-venv:/venv:ro" \
  -v "$runner_path:/runner.py:ro" \
  -v "$contract_path:/user_tool_contract.py:ro" \
  -v "$spike_dir/prompt.py:/work/prompt.py:ro" \
  -v "$spike_dir/tool.py:/work/tool.py:ro" \
  -v "$spike_dir/contract.json:/work/contract.json:ro" \
  -v "$spike_dir/result:/result:rw" \
  "$spike_image" /venv/bin/python -I /runner.py \
  /work/prompt.py /work/tool.py /work/contract.json "$setup_description" \
  "/result/$result_name"
}

run_setup "$setup_one_name" 'setup one description' setup-one.json &
setup_one_pid=$!
run_setup "$setup_two_name" 'setup two description' setup-two.json &
setup_two_pid=$!
wait "$setup_one_pid"
wait "$setup_two_pid"

python3 - "$spike_dir/result/setup-one.json" "$spike_dir/result/setup-two.json" <<'PY'
import json
import sys
from pathlib import Path

results = [json.loads(Path(path).read_text()) for path in sys.argv[1:]]
assert [result["tool_description"] for result in results] == [
    "setup one description",
    "setup two description",
]
for result in results:
    assert result["final_output"] == "weather complete"
    assert result["sdk_version"] == "0.22.2"
    assert result["system_prompt"] == "weather assistant for owner-a"
    assert result["tool_name"] == "weather"
    assert result["events"] == ["model", "tool:weather:37.5,127.0: 20 C", "model"]
    assert result["tool_schema"]["properties"]["latitude"]["type"] == "number"
PY

if docker inspect "$missing_name" "$install_name" "$runtime_name" \
  "$setup_one_name" "$setup_two_name" >/dev/null 2>&1; then
  echo 'container cleanup failed' >&2
  exit 1
fi

printf 'container SDK environment smoke passed\n'
