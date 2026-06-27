# Staging Bootstrap Report

- Target: hermes-staging-01 (Ubuntu 26.04 LTS)
- Generated: 2026-06-27
- Commit: 628fdfe (feature branch feat/staging-bootstrap)

## What was done
- Added `scripts/bootstrap-staging.sh` (idempotent, config backups before mutation).
- Added `scripts/verify-staging.sh` (read-only checks).
- Committed to feature branch; no push.

## Intended automated steps on the VPS
- OS + network sanity
- create `deploy` user
- install Docker Engine + Compose plugin from official repo
- add `deploy` to docker group
- create 2 GB swap
- install + configure UFW (22/80/443)
- install + run Fail2ban
- enable unattended-upgrades
- configure Docker log rotation
- create /opt/terrabits/{apps,backups,caddy}

## Not done
- Redis install (explicitly excluded)
- Heavy monitoring stack (excluded by policy)
- Hetzner Firewall / DNS / Cloudflare / GitHub Secrets untouched
- Root SSH remains enabled until deploy user verified separately (policy #9)
- No paid resources created

## Verification results
- (filled after execution)

## Remaining manual review
- Verify deploy user SSH access with dedicated key before disabling root SSH.
