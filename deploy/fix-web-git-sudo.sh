#!/bin/bash
# 一次性修复：WEB 在线更新 + 客户端发布包目录
set -euo pipefail

APP="${LIANHUAN_APP_ROOT:-/opt/lianhuan/app}"
RELEASES="${LIANHUAN_RELEASES_DIR:-/opt/lianhuan/releases}"
RELEASES_REPO="${LIANHUAN_RELEASES_REPO:-https://github.com/e12games/facefusion-releases.git}"
ENV_FILE="/etc/lianhuan.env"

if [[ "$(id -u)" -ne 0 ]]; then
	echo "请用 root 运行: sudo bash $0"
	exit 1
fi

cd "$APP"
git checkout -- deploy/web-self-update.sh deploy/web-git.sh 2>/dev/null || true
git pull --ff-only origin main || git pull --ff-only

chmod +x "$APP/deploy/web-git.sh" "$APP/deploy/web-self-update.sh" 2>/dev/null || true

cat >/etc/sudoers.d/lianhuan-web-update <<EOF
www-data ALL=(root) NOPASSWD: /bin/bash ${APP}/deploy/web-git.sh
www-data ALL=(root) NOPASSWD: /bin/bash ${APP}/deploy/web-self-update.sh
EOF
chmod 440 /etc/sudoers.d/lianhuan-web-update

git config --global --add safe.directory "$RELEASES" 2>/dev/null || true
if [[ -d "$RELEASES/.git" ]]; then
	git -C "$RELEASES" pull --ff-only origin main || git -C "$RELEASES" pull --ff-only
else
	git clone "$RELEASES_REPO" "$RELEASES"
fi
chown -R www-data:www-data "$RELEASES"

grep -q '^LIANHUAN_RELEASES_DIR=' "$ENV_FILE" 2>/dev/null || echo "LIANHUAN_RELEASES_DIR=$RELEASES" >>"$ENV_FILE"
grep -q '^LIANHUAN_RELEASES_REPO=' "$ENV_FILE" 2>/dev/null || echo "LIANHUAN_RELEASES_REPO=$RELEASES_REPO" >>"$ENV_FILE"

systemctl restart lianhuan-web
echo "OK: WEB 更新 sudo + 发布包 $RELEASES 已就绪"
