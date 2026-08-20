#!/bin/bash
# 在 VPS 上运行（root）：bash vps-bootstrap.sh
# 前提：/opt/lianhuan/app/web/app.py 已存在（git clone 或上传 web 目录）
set -euo pipefail

APP_ROOT="/opt/lianhuan/app"
WEB_DIR="$APP_ROOT/web"
VENV="/opt/lianhuan/venv"
DEPLOY="$APP_ROOT/deploy"
ENV_FILE="/etc/lianhuan.env"
PORT="${LIANHUAN_PORT:-8092}"

if [[ ! -f "$WEB_DIR/app.py" ]]; then
	echo "缺少 $WEB_DIR/app.py"
	echo "请先执行："
	echo "  mkdir -p /opt/lianhuan && cd /opt/lianhuan"
	echo "  git clone https://github.com/e12games/facefusion.git app"
	echo "或把本机 web 文件夹上传到 $WEB_DIR"
	exit 1
fi

mkdir -p "$DEPLOY"

cat > "$DEPLOY/start.sh" << 'EOF'
#!/bin/bash
set -euo pipefail
PORT="${LIANHUAN_PORT:-8092}"
exec /opt/lianhuan/venv/bin/uvicorn app:app --host 127.0.0.1 --port "$PORT"
EOF
chmod +x "$DEPLOY/start.sh"

cat > /etc/systemd/system/lianhuan-web.service << EOF
[Unit]
Description=LianHuan Web
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$WEB_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$DEPLOY/start.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

if [[ ! -f "$ENV_FILE" ]]; then
	SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))' 2>/dev/null || openssl rand -hex 32)
	cat > "$ENV_FILE" << EOF
LIANHUAN_SECRET=$SECRET
LIANHUAN_ADMIN_EMAIL=admin@local.test
LIANHUAN_ADMIN_PASSWORD=请改成强密码
LIANHUAN_PORT=$PORT
EOF
	chmod 600 "$ENV_FILE"
	echo "已创建 $ENV_FILE ，请 nano 修改管理员密码"
fi

if [[ ! -x "$VENV/bin/python" ]]; then
	apt-get install -y -qq python3-venv python3-pip 2>/dev/null || true
	python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -U pip
"$VENV/bin/pip" install -r "$WEB_DIR/requirements.txt"

mkdir -p "$WEB_DIR/data"
chown -R www-data:www-data "$WEB_DIR/data" "$WEB_DIR/releases" 2>/dev/null || true
chown -R www-data:www-data "$APP_ROOT" || true

systemctl daemon-reload
systemctl enable lianhuan-web
systemctl restart lianhuan-web
sleep 1
systemctl status lianhuan-web --no-pager || true
curl -sS "http://127.0.0.1:$PORT/api/version" || echo "curl 失败，请看 journalctl -u lianhuan-web -n 50"

echo ""
echo "完成。宝塔反向代理 -> http://127.0.0.1:$PORT"
echo "请编辑 $ENV_FILE 后 systemctl restart lianhuan-web"
