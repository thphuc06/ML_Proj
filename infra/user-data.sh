#!/bin/bash
# EC2 first boot: Docker + compose, 4 GB swap, data dirs, nightly Postgres backup (kept 14 days).
set -eux
apt-get update
apt-get install -y ca-certificates curl python3-venv python3-pip
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker ubuntu

fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

mkdir -p /srv/sidewalk/{infra,data/crops,backups}
mkdir -p /srv/sidewalk/infra/ls-data && chown -R 1001:0 /srv/sidewalk/infra/ls-data
chown -R ubuntu:ubuntu /srv/sidewalk/data /srv/sidewalk/backups

cat > /etc/cron.d/sidewalk-backup <<'EOF'
30 2 * * * root cd /srv/sidewalk/infra && docker compose exec -T db pg_dump -U ls labelstudio | gzip > /srv/sidewalk/backups/ls_$(date +\%F).sql.gz && find /srv/sidewalk/backups -name 'ls_*.sql.gz' -mtime +14 -delete
EOF
touch /var/lib/cloud/instance/sidewalk-ready
