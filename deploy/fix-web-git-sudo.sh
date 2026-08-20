#!/bin/bash
# 一次性修复：WEB 在线更新的 git / sudo 权限（已有 VPS 执行一次）
set -euo pipefail

APP="${LIANHUAN_APP_ROOT:-/opt/lianhuan/app}"

if [[ "$(id -u)" -ne 0 ]]; then
	echo "请用 root 运行: sudo bash $0"
	exit 1
fi

chmod +x "$APP/deploy/web-git.sh" "$APP/deploy/web-self-update.sh" 2>/dev/null || true

cat >/etc/sudoers.d/lianhuan-web-update <<EOF
www-data ALL=(root) NOPASSWD: /bin/bash ${APP}/deploy/web-git.sh
www-data ALL=(root) NOPASSWD: /bin/bash ${APP}/deploy/web-self-update.sh
EOF
chmod 440 /etc/sudoers.d/lianhuan-web-update

echo "OK: sudoers 已配置。可在后台「检查 WEB 更新」测试。"
echo "若仓库为私有，请在 /etc/lianhuan.env 添加 GITHUB_TOKEN=你的PAT 后 systemctl restart lianhuan-web"
