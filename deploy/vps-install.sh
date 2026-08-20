#!/bin/bash
# 脸幻 WEB 一键安装 / 修复（Ubuntu + 宝塔/Nginx）
#
# 用法 1（已 clone 到 /opt/lianhuan/app）：
#   bash /opt/lianhuan/app/deploy/vps-install.sh
#
# 用法 2（从零开始）：
#   curl -fsSL https://raw.githubusercontent.com/e12games/facefusion/main/deploy/vps-install.sh | bash
#
set -euo pipefail

REPO="${LIANHUAN_REPO:-https://github.com/e12games/facefusion.git}"
BRANCH="${LIANHUAN_BRANCH:-main}"
ROOT="/opt/lianhuan"
APP="$ROOT/app"
WEB="$APP/web"
VENV="$ROOT/venv"
ENV_FILE="/etc/lianhuan.env"
PORT="${LIANHUAN_PORT:-8092}"
SERVICE="lianhuan-web"

log() { echo "==> $*"; }
die() { echo "错误: $*" >&2; exit 1; }

if [[ "$(id -u)" -ne 0 ]]; then
	die "请用 root 运行： sudo bash $0"
fi

git config --global --add safe.directory "$APP" 2>/dev/null || true
git -C "$APP" checkout -- deploy/start.sh 2>/dev/null || true
git -C "$APP" reset --hard HEAD 2>/dev/null || true

log "安装系统依赖"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl ca-certificates python3 python3-venv python3-pip

command -v python3 >/dev/null || die "未找到 python3"
python3 --version

log "配置 Git（避免 dubious ownership）"
git config --global --add safe.directory "$APP" 2>/dev/null || true

log "拉取 / 更新源码"
mkdir -p "$ROOT"
if [[ -d "$APP/.git" ]]; then
	git -C "$APP" fetch origin "$BRANCH"
	git -C "$APP" reset --hard "origin/$BRANCH"
else
	git clone --depth 1 -b "$BRANCH" "$REPO" "$APP"
fi

[[ -f "$WEB/app.py" ]] || die "缺少 $WEB/app.py"

log "写入启动脚本"
mkdir -p "$APP/deploy"
cat > "$APP/deploy/start.sh" << 'EOF'
#!/bin/bash
set -euo pipefail
PORT="${LIANHUAN_PORT:-8092}"
exec /opt/lianhuan/venv/bin/uvicorn app:app --host 127.0.0.1 --port "$PORT" --proxy-headers --forwarded-allow-ips='*'
EOF
chmod +x "$APP/deploy/start.sh"

log "写入 systemd：$SERVICE"
cat > "/etc/systemd/system/${SERVICE}.service" << EOF
[Unit]
Description=LianHuan Web
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$WEB
EnvironmentFile=$ENV_FILE
ExecStart=/bin/bash /opt/lianhuan/app/deploy/start.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

if [[ ! -f "$ENV_FILE" ]]; then
	SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
	cat > "$ENV_FILE" << EOF
LIANHUAN_SECRET=$SECRET
LIANHUAN_ADMIN_EMAIL=admin@lianhuan.local
LIANHUAN_ADMIN_PASSWORD=admin123
LIANHUAN_PORT=$PORT
EOF
	chmod 600 "$ENV_FILE"
	log "已创建 $ENV_FILE（默认管理员 admin@lianhuan.local / admin123，进后台会提示改密）"
else
	if ! grep -q '^LIANHUAN_PORT=' "$ENV_FILE"; then
		echo "LIANHUAN_PORT=$PORT" >> "$ENV_FILE"
	fi
	log "使用已有 $ENV_FILE"
fi

# shellcheck disable=SC1090
source "$ENV_FILE" 2>/dev/null || true
PORT="${LIANHUAN_PORT:-8092}"

log "创建 Python 虚拟环境"
if [[ ! -x "$VENV/bin/pip" ]]; then
	rm -rf "$VENV"
	python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -U pip -q
"$VENV/bin/pip" install -r "$WEB/requirements.txt" -q

log "目录权限"
mkdir -p "$WEB/data" "$WEB/releases/files"
chown -R www-data:www-data "$WEB/data" "$WEB/releases"
chmod 755 "$ROOT" "$APP" "$WEB"
chmod 644 "$ENV_FILE"
chmod 600 "$ENV_FILE"
# systemd 以 root 读 EnvironmentFile，www-data 写数据库
chown root:root "$ENV_FILE"

log "启动服务"
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"
sleep 2

if curl -fsS "http://127.0.0.1:${PORT}/api/version"; then
	echo ""
else
	echo ""
	log "启动失败，最近日志："
	journalctl -u "$SERVICE" -n 40 --no-pager || true
	die "请根据上方日志排查"
fi

cat << EOF

========================================
脸幻 WEB 安装完成
本机：http://127.0.0.1:${PORT}
API： http://127.0.0.1:${PORT}/api/version
配置：$ENV_FILE
域名：facefusion.iqiyia.cyou
默认管理员：admin@lianhuan.local / admin123
（进后台会提示改密，不强制）
宝塔：站点 → SSL → 反向代理 http://127.0.0.1:${PORT}
========================================
EOF
