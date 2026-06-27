# Staging Bootstrap Report

- Target: hermes-staging-01 (Ubuntu 26.04 LTS)
- Generated: 2026-06-27
- Commit: 482dcf3c0 + 628fdfe (feature branch feat/staging-bootstrap)
- IPv4: 157.180.125.174
- Hostname: hermes-staging-01
- Kernel: 7.0.0-15-generic
- cloud-init: done (DataSourceHetzner)

## What was done
- Added `scripts/bootstrap-staging.sh` (idempotent, config backups before mutation).
- Added `scripts/verify-staging.sh` (read-only checks).
- SSH access confirmed via `~/.ssh/staging_admin_ed25519` as root.
- Executed `bootstrap-staging.sh` on the VPS successfully.
- Verified with `verify-staging.sh` — 8 PASS, 0 FAIL.

## Automated steps completed on VPS
- OS + network sanity (Ubuntu 26.04 LTS, cloud-init done)
- Created `deploy` user (uid=1000, bash, locked password, docker group)
- Installed Docker Engine 29.6.1 + Compose plugin from official repo
- Created 2 GB swap at /swapfile
- Installed + configured UFW (22/80/443 allowed, default deny incoming)
- Installed + ran Fail2ban (sshd jail)
- Enabled unattended-upgrades
- Configured Docker log rotation (json-file, 10m/5)
- Created /opt/terrabits/{apps,backups,caddy} owned by deploy

## Verification results
| Check | Result |
| --- | --- |
| docker --version | PASS |
| docker compose version | PASS |
| docker service active | PASS |
| fail2ban service active | PASS |
| swap enabled | PASS |
| deploy user exists | PASS |
| deploy in docker group | PASS |
| sshd config valid | PASS |
| UFW active, 22/80/443 allowed | PASS |
| cloud-init done | PASS |

## Not done
- Redis install (excluded by policy)
- Heavy monitoring stack (excluded by policy)
- Hetzner Firewall / DNS / Cloudflare / GitHub Secrets untouched
- Root SSH remains enabled (policy #9 — kept until deploy user verified separately)
- No paid resources created
- No push to remote

## Remaining manual review
- Verify deploy user SSH access with dedicated key before disabling root SSH.
- Confirm Hetzner Firewall mirrors UFW rules (policy #8).
