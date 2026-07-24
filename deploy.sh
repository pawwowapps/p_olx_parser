#!/usr/bin/env bash
set -euo pipefail

SERVER="root@46.225.76.115"
APP_DIR="/opt/olx-bot"

echo "==> Деплою на $SERVER"
ssh "$SERVER" "
  set -e
  cd $APP_DIR
  git pull
  .venv/bin/pip install -q -r requirements.txt
  systemctl restart olx-bot
  sleep 2
  systemctl status olx-bot --no-pager -l | head -n 8
"
echo "==> Готово"
