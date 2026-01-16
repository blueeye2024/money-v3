#!/bin/bash
set -e

# Project root
PROJECT_ROOT="/home/blue/blue/my_project/money"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# 1. Build frontend
cd "$FRONTEND_DIR"
npm install
npm run build

# 2. Copy built files to remote server
REMOTE_USER="blue"
REMOTE_HOST="money.mysmartgate.kr"
REMOTE_PATH="/var/www/html"
sshpass -p "blueeye0037!" rsync -avz "$FRONTEND_DIR/dist/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/"

# 3. Restart backend service on remote server
sshpass -p "blueeye0037!" ssh -o StrictHostKeyChecking=no "${REMOTE_USER}@${REMOTE_HOST}" "echo 'blueeye0037!' | sudo -S systemctl restart cheongan-backend"

echo "✅ Deployment to $REMOTE_HOST completed."
