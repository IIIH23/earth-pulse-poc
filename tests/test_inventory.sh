#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

fixture="$work_dir/fixture"
output="$work_dir/FILE_INVENTORY.md"
mkdir -p "$fixture/nested" "$fixture/excluded"
touch "$fixture/alpha.txt"
touch "$fixture/nested/bravo.json"
touch "$fixture/excluded/hidden.dat"

python3 "$repo_root/tools/inventory.py" \
  --root "$fixture" \
  --exclude excluded \
  --out "$output"

grep -q 'alpha.txt' "$output"
grep -q 'nested/bravo.json' "$output"

if grep -q 'hidden.dat' "$output"; then
  echo "Excluded file was included in inventory" >&2
  exit 1
fi

echo "Inventory test passed."
