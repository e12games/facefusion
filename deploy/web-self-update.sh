#!/bin/bash
# WEB 在线更新：git pull + pip + 延迟重启（由后台管理员触发）
set -euo pipefail

APP="${LIANHUAN_APP_ROOT:-/opt/lianhuan/app}"
WEB="${APP}/web"
VENV="${LIANHUAN_VENV:-/opt/lianhuan/venv}"
SERVICE="${LIANHUAN_SERVICE:-lianhuan-web}"
BRANCH="${LIANHUAN_BRANCH:-main}"
LOG="${WEB}/data/web_update.log"
LOCK="${WEB}/data/web_update.lock"
GIT="$APP/deploy/web-git.sh"

mkdir -p "${WEB}/data"
exec >>"$LOG" 2>&1

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) web-self-update start ==="
trap 'rm -f "$LOCK"' EXIT

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
	if command -v sudo >/dev/null 2>&1; then
		exec sudo -n -E /bin/bash "$0" "$@"
	fi
	echo "web-self-update: need root" >&2
	exit 1
fi

export GIT_TERMINAL_PROMPT=0
cd "$APP"
"$GIT" _fetch "$BRANCH"
"$GIT" pull --ff-only origin "$BRANCH"
"$VENV/bin/pip" install -r "$WEB/requirements.txt" -q
chown -R www-data:www-data "$WEB/data" "$WEB/releases" 2>/dev/null || true
echo "pull ok, scheduling service restart"
nohup bash -c "sleep 2; systemctl restart ${SERVICE}" >/dev/null 2>&1 &
echo "=== web-self-update done ==="
