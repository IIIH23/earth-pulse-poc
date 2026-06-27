#!/usr/bin/env bash
# hermes-staging-01 bootstrap script
# Idempotent, sectioned, backs up configs before mutation.
# Run as root on the target VPS.
set -euo pipefail

LOG() { printf '\n[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"; }

BACKUP_DIR="/root/bootstrap-backups/$(date -u +'%Y%m%dT%H%M%SZ')"
mkdir -p "$BACKUP_DIR"

backup_path() {
  if [ -e "$1" ]; then
    cp -a "$1" "$BACKUP_DIR/" || true
  fi
}

LOG "Backing up configuration directories"
for p in /etc/ssh /etc/ufw /etc/fail2ban /etc/docker /etc/apt /etc/sysctl.d; do
  backup_path "$p"
done
tar -czf "$BACKUP_DIR.tar.gz" -C "$BACKUP_DIR" . || true
LOG "Backup archive: $BACKUP_DIR.tar.gz"

LOG "OS + network sanity"
. /etc/os-release
if [ "${ID:-}" != "ubuntu" ]; then
  LOG "ERROR: expected ubuntu, got ${ID:-unknown}"; exit 1
fi
LOG "OS: ${PRETTY_NAME:-$VERSION}"
LOG "Kernel: $(uname -r)"
LOG "Public IPv4: $(curl -fsS --max-time 5 https://ifconfig.me || echo 'unknown')"
LOG "cloud-init status: $(cloud-init status --long 2>&1 | head -n1 || true)"

LOG "apt update"
apt-get update -y

LOG "Creating deploy user"
if ! id -u deploy >/dev/null 2>&1; then
  useradd -m -s /bin/bash -U deploy
  passwd -l deploy
  LOG "deploy user created"
else
  LOG "deploy user already exists"
fi
# deploy may run docker without sudo via group; no password sudo needed for CI/CD runtime
if [ ! -f /etc/sudoers.d/deploy ]; then
  printf 'deploy ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker compose, /usr/bin/systemctl\n' > /etc/sudoers.d/deploy
  chmod 0440 /etc/sudoers.d/deploy
fi

LOG "Installing base packages"
apt-get install -y ca-certificates curl git jq ufw fail2ban unattended-upgrades apt-transport-https gnupg lsb-release

LOG "Installing Docker Engine from official repository"
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.asc ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
fi
if [ ! -f /etc/apt/sources.list.d/docker.list ]; then
  printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
    "$(dpkg --print-architecture)" "$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
fi
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker deploy || true

LOG "Configuring 2 GB swap"
if ! swapon --show=NAME --noheadings | grep -q '^/swapfile$'; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  if ! grep -q '^/swapfile ' /etc/fstab; then
    printf '/swapfile none swap sw 0 0\n' >> /etc/fstab
  fi
  LOG "swap enabled"
else
  LOG "swap already enabled"
fi

printf 'vm.swappiness=10\nvm.vfs_cache_pressure=50\n' > /etc/sysctl.d/99-terrabits.conf
sysctl --system >/dev/null || true

LOG "Configuring UFW"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable || true

LOG "Configuring unattended-upgrades"
printf 'APT::Periodic::Update-Package-Lists "1";\nAPT::Periodic::Unattended-Upgrade "1";\n' > /etc/apt/apt.conf.d/20auto-upgrades
systemctl enable --now unattended-upgrades || true

LOG "Configuring Docker log rotation"
install -d /etc/docker
printf '{"log-driver":"json-file","log-opts":{"max-size":"10m","max-file":"5"},"live-restore":true}\n' > /etc/docker/daemon.json
systemctl restart docker || true

LOG "Configuring Fail2ban sshd jail"
printf '[sshd]\nenabled = true\nport = ssh\nmaxretry = 5\nfindtime = 10m\nbantime = 1h\n' > /etc/fail2ban/jail.d/sshd.local
systemctl enable --now fail2ban || true

LOG "Creating project directories"
mkdir -p /opt/terrabits/apps /opt/terrabits/backups /opt/terrabits/caddy
chown -R deploy:deploy /opt/terrabits

LOG "Bootstrap complete. Run scripts/verify-staging.sh to validate."
