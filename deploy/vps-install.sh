#!/bin/bash
# 脸幻 WEB 一键安装（Ubuntu + 宝塔/Nginx）
# 用法：curl -fsSL https://raw.githubusercontent.com/e12games/facefusion/main/deploy/vps-install.sh | bash
set -euo pipefail

REPO="${LIANHUAN_REPO:-https://github.com/e12games/facefusion.git}"
BRANCH="${LIANHUAN_BRANCH:-main}"
ROOT="/opt/lianhuan"
APP="$ROOT/app"
WEB="$APP/web"
VENV="$ROOT/venv"
ENV_FILE="/etc/lianhuan.env"
PORT="${LIANHUAN_PORT:-8092}"

echo "==> 安装系统依赖"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl ca-certificates python3 python3-venv python3-pip

if ! command -v python3 >/dev/null; then
	echo "未找到 python3"
	exit 1
fi

echo "==> 拉取源码"
mkdir -p "$ROOT"
if [[ -d "$APP/.git" ]]; then
	git -C "$APP" fetch origin "$BRANCH"
	git -C "$APP" reset --hard "origin/$BRANCH"
else
	git clone --depth 1 -b "$BRANCH" "$REPO" "$APP"
fi

if [[ ! -f "$WEB/app.py" ]]; then
	echo "缺少 $WEB/app.py，请检查仓库是否完整"
	exit 1
fi

echo "==> 写入启动脚本与 systemd"
mkdir -p "$APP/deploy"
cat > "$APP/deploy/start.sh" << 'EOF'
#!/bin/bash
set -euo pipefail
PORT="${LIANHUAN_PORT:-8092}"
exec /opt/lianhuan/venv/bin/uvicorn app:app --host 127.0.0.1 --port "$PORT"
EOF
chmod +x "$APP/deploy/start.sh"

cat > /etc/systemd/system/lianhuan-web.service << EOF
[Unit]
Description=LianHuan Web
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$WEB
EnvironmentFile=$ENV_FILE
ExecStart=$APP/deploy/start.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

if [[ ! -f "$ENV_FILE" ]]; then
	SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
	cat > "$ENV_FILE" << EOF
LIANHUAN_SECRET=$SECRET
LIANHUAN_ADMIN_EMAIL=admin@local.test
LIANHUAN_ADMIN_PASSWORD=admin123
LIANHUAN_PORT=$PORT
EOF
	chmod 600 "$ENV_FILE"
	echo "==> 已创建 $ENV_FILE（默认密码 admin123，请尽快修改）"
fi

echo "==> Python 虚拟环境"
if [[ ! -x "$VENV/bin/python" ]]; then
	python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -U pip -q
"$VENV/bin/pip" install -r "$WEB/requirements.txt" -q

mkdir -p "$WEB/data" "$WEB/releases/files"
chown -R www-data:www-data "$ROOT"

echo "==> 启动服务"
systemctl daemon-reload
systemctl enable lianhuan-web
systemctl restart lianhuan-web
sleep 2

if curl -fsS "http://127.0.0.1:$PORT/api/version" >/dev/null; then
	echo "==> 成功：http://127.0.0.1:$PORT/api/version"
else
	echo "==> 启动可能失败，请执行： journalctl -u lianhuan-web -n 50 --no-pager"
	exit 1
fi

cat << EOF

========================================
脸幻 WEB 已安装
本机端口：127.0.0.1:$PORT
环境配置：$ENV_FILE
宝塔：添加站点 facefusion.iqiyia.cyou → SSL → 反向代理 http://127.0.0.1:$PORT
改密码后：systemctl restart lianhuan-web
========================================
EOF
