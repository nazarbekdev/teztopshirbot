#!/usr/bin/env bash
# Serverga joylash: kod → rsync, bog'liqliklar → venv, qayta ishga tushirish.
#   ./deploy/deploy.sh            oddiy yangilash
#   ./deploy/deploy.sh --first    birinchi marta: foydalanuvchi, papkalar, systemd, zaxira cron
# `.env` va baza serverga YUBORILMAYDI: sirlar serverda /etc/teztopshir/env da, baza /var/lib/teztopshir da.
set -euo pipefail

HOST="${DEPLOY_HOST:-root@95.111.234.221}"
KEY="${DEPLOY_KEY:-$HOME/.ssh/osontopshir_ci}"
SSH="ssh -i $KEY -o BatchMode=yes"
APP=/var/www/teztopshir-bot
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--first" ]]; then
  $SSH "$HOST" "id teztopshir >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin teztopshir
    mkdir -p $APP /etc/teztopshir /var/lib/teztopshir/backups
    chown -R teztopshir:teztopshir /var/lib/teztopshir
    chmod 750 /etc/teztopshir && chgrp teztopshir /etc/teztopshir
    [ -f /etc/teztopshir/env ] && chgrp teztopshir /etc/teztopshir/env && chmod 640 /etc/teztopshir/env
    python3 -m venv $APP/venv"
  scp -i "$KEY" deploy/teztopshir-bot.service "$HOST:/etc/systemd/system/teztopshir-bot.service"
  $SSH "$HOST" "echo '30 3 * * * teztopshir /var/www/teztopshir-bot/venv/bin/python /var/www/teztopshir-bot/deploy/backup.py >> /var/lib/teztopshir/backup.log 2>&1' > /etc/cron.d/teztopshir-backup
    systemctl daemon-reload && systemctl enable teztopshir-bot"
fi

rsync -az --delete -e "$SSH" \
  --exclude '.git' --exclude '.venv' --exclude 'venv' --exclude '.idea' --exclude '__pycache__' --exclude '.pytest_cache' \
  --exclude '.env*' --exclude '*.db*' --exclude 'tests' --exclude 'brand' \
  ./ "$HOST:$APP/"
$SSH "$HOST" "chown -R root:teztopshir $APP && chmod -R g+rX,o-rwx $APP
  $APP/venv/bin/pip install -q -r $APP/requirements.txt 2>&1 | grep -v 'notice' || true
  systemctl restart teztopshir-bot && sleep 4 && systemctl is-active teztopshir-bot"
