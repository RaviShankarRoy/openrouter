#!/usr/bin/env bash
# deploy/aws/setup-server.sh — one-time setup for a fresh Ubuntu EC2 instance.
#
# Run this once, over SSH, as the default `ubuntu` user:
#   curl -fsSL https://raw.githubusercontent.com/<you>/<repo>/main/deploy/aws/setup-server.sh | bash
# or copy the repo up first and run:  bash deploy/aws/setup-server.sh
#
# What it does: installs Docker + Compose, adds you to the docker group,
# and adds a 4GB swap file (image builds need more RAM than small instances have).

set -euo pipefail

echo "==> Updating packages"
sudo apt-get update -y
sudo apt-get install -y git curl ca-certificates

echo "==> Installing Docker (official convenience script)"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
else
  echo "    docker already installed: $(docker --version)"
fi

echo "==> Allowing user '$USER' to run docker without sudo"
sudo usermod -aG docker "$USER"

echo "==> Adding 4GB swap (protects builds on small instances)"
if [ ! -f /swapfile ]; then
  sudo fallocate -l 4G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
else
  echo "    swap already configured"
fi

echo "==> Enabling Docker on boot"
sudo systemctl enable docker

echo
echo "================================================================"
echo " Setup complete. NOW LOG OUT AND SSH BACK IN (the docker group"
echo " membership only takes effect on a new login), then:"
echo
echo "   git clone <your-repo-url> openrouter && cd openrouter"
echo "   cp deploy/aws/.env.aws.example .env.aws"
echo "   nano .env.aws          # fill in domain + secrets"
echo "   ./deploy/aws/deploy.sh"
echo "================================================================"
