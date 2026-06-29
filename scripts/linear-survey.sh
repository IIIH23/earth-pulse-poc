#!/usr/bin/env bash
# Analyze Linear workspace for Pulse of Earth integration
# Requires: LINEAR_API_KEY env var
set -euo pipefail

: "${LINEAR_API_KEY:?Usage: LINEAR_API_KEY=... bash scripts/linear-survey.sh}"

echo "=== Linear Workspace Survey ==="
echo ""

# Query user
echo "1. Current user:"
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ viewer { id name email } }"}' | python3 -c "import sys,json; r=json.load(sys.stdin); v=r['data']['viewer']; print(f\"   UUID: {v['id']}\n   Name: {v['name']}\n   Email: {v['email']}\")"

echo ""
echo "2. Workspaces:"
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ workspaces { nodes { id name slug } } }"}' | python3 -c "import sys,json; r=json.load(sys.stdin); [print(f\"   {w['name']} ({w['slug']})\") for w in r['data']['workspaces']['nodes']]"

echo ""
echo "3. Pulse of Earth project:"
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ project(id: \"\") { id name description } }"}' 2>/dev/null || echo "   (search by name needed)"

echo ""
echo "4. Existing labels (if any):"
echo "   (will be queried after project selection)"

echo ""
echo "Done. Provide the workspace details for further analysis."
