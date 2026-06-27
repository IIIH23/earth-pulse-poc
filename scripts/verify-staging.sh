#!/usr/bin/env bash
# hermes-staging-01 verification script
# Read-only checks, prints PASS/FAIL, exits nonzero on critical failure.
set -uo pipefail

PASS=0
FAIL=0

check() {
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf 'PASS  %s\n' "$name"
    PASS=$((PASS+1))
  else
    printf 'FAIL  %s\n' "$name"
    FAIL=$((FAIL+1))
  fi
}

report() {
  local title="$1"; shift
  printf '\n== %s ==\n' "$title"
  "$@"
}

report "Docker" docker --version
check "docker command present" docker --version
check "docker compose plugin present" docker compose version
check "docker service active" systemctl is-active docker
check "fail2ban service active" systemctl is-active fail2ban
check "swap enabled" grep -q '^/swapfile$' <(swapon --show=NAME --noheadings)
check "deploy user exists" id deploy
check "deploy in docker group" bash -c 'id -nG deploy | grep -qw docker'
check "sshd config valid" sshd -t

report "UFW" ufw status verbose
report "Swap" swapon --show
report "Deploy user" id deploy
report "cloud-init" cloud-init status --long

printf '\nSummary: %d PASS, %d FAIL\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
