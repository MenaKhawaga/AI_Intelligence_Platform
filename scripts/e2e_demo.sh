#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
EMAIL="${DEMO_EMAIL:-demo@example.com}"
PASSWORD="${DEMO_PASSWORD:-password123}"

printf '\n1) Registering demo user...\n'
curl -sS -X POST "$BASE_URL/auth/register" -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" || true

printf '\n2) Logging in...\n'
TOKEN=$(curl -sS -X POST "$BASE_URL/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

printf '\n3) Asking the AI Agent...\n'
curl -sS -X POST "$BASE_URL/chat" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"query":"What are the current AI intelligence trends, and which stored articles support them?"}'
printf '\n'
