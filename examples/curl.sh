#!/usr/bin/env bash
# Aggregator basics with curl: one key, three modalities, one task poll.
set -euo pipefail
: "${APIMART_API_KEY:?export APIMART_API_KEY first}"
BASE="https://api.apimart.ai/v1"
AUTH=(-H "Authorization: Bearer $APIMART_API_KEY" -H 'Content-Type: application/json')
IDEMPOTENCY=(-H "Idempotency-Key: $(uuidgen)" -H 'X-APIMart-Response-Version: 2026-07-27')

echo "== text =="
curl -sS "$BASE/chat/completions" "${AUTH[@]}" \
  -d '{"model":"gpt-5.5","messages":[{"role":"user","content":"Name three retry rules."}]}' | head -c 400; echo

echo "== image (per-image route) =="
TASK=$(curl -sS "$BASE/images/generations" "${AUTH[@]}" "${IDEMPOTENCY[@]}" \
  -d '{"model":"gpt-image-2.5-ext","version":"flare","prompt":"A ceramic espresso cup on a stone pedestal","size":"1:1","resolution":"1K","n":1}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["id"])')
echo "task: $TASK"

echo "== poll =="
for _ in $(seq 1 20); do
  RESPONSE=$(curl -sS "$BASE/tasks/$TASK" "${AUTH[@]}")
  STATUS=$(printf '%s' "$RESPONSE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["status"])')
  echo "status: $STATUS"
  [ "$STATUS" = "completed" ] && break
  [ "$STATUS" = "failed" ] && { printf '%s\n' "$RESPONSE"; exit 1; }
  sleep 5
done
printf '%s' "$RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print("cost:", d.get("cost"), "urls:", d.get("result",{}).get("images",[{}])[0].get("url"))'
