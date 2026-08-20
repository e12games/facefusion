# VPS 部署（Ubuntu 22.04+ 示例）

## 1. 准备

- 域名 A 记录指向 VPS
- 开放 80 / 443

## 2. 检测已有 WEB 占用的端口（SSH 登录 VPS 后执行）

外网一般仍是 **80 / 443**（Caddy/Nginx 共用）；脸幻程序本身只监听 **本机 127.0.0.1 的某一端口**，不要和现有站点冲突。

**推荐：先看所有监听端口**
```bash
sudo ss -tlnp
```

**只看常见 WEB / 应用端口**
```bash
sudo ss -tlnp | grep -E ':(80|443|3000|5000|8000|8080|8081|8082|8090|8091|8092|8093|8888)\s'
```

**看是哪个程序占用（需 root）**
```bash
sudo lsof -iTCP -sTCP:LISTEN -P -n
```

**若用 Caddy 管多站点，看已有站点配置**
```bash
sudo cat /etc/caddy/Caddyfile
# 或
ls /etc/caddy/sites/ 2>/dev/null
```

**若用 Nginx**
```bash
ls /etc/nginx/sites-enabled/
grep -R "proxy_pass\|listen" /etc/nginx/sites-enabled/
```

在输出里找已被占用的端口（例如已有 `127.0.0.1:8080`），脸幻另选一个 **未被 LISTEN 的端口**，例如 `8092`、`8093`。

选定端口后，写入两处（必须一致）：
- `/etc/lianhuan.env` → `LIANHUAN_PORT=8092`
- Caddy 站点块 → `reverse_proxy 127.0.0.1:8092`  
  （若 Caddy 用 `import` 多文件，可为脸幻单独加 `facefusion.iqiyia.cyou { ... }` 块，不要覆盖别的域名）

**自检端口是否空闲（把 8092 换成你选的）**
```bash
sudo ss -tlnp | grep ':8092' || echo "8092 空闲"
```

## 3. 安装依赖

```bash
sudo apt update
sudo apt install -y git python3.12 python3.12-venv caddy
sudo mkdir -p /opt/lianhuan
sudo chown $USER:$USER /opt/lianhuan
```

## 4. 拉代码

```bash
cd /opt/lianhuan
git clone https://github.com/e12games/facefusion.git app
cd app/web
python3.12 -m venv /opt/lianhuan/venv
/opt/lianhuan/venv/bin/pip install -r requirements.txt
```

## 5. 环境变量

```bash
sudo cp /opt/lianhuan/app/deploy/env.example /etc/lianhuan.env
sudo nano /etc/lianhuan.env
```

务必修改：`LIANHUAN_SECRET`、管理员邮箱和密码。`LIANHUAN_PORT=8092`（本 VPS 扫描后 8092 空闲，勿改除非冲突）。

## 6. systemd

```bash
sudo cp /opt/lianhuan/app/deploy/lianhuan-web.service /etc/systemd/system/
sudo chmod +x /opt/lianhuan/app/deploy/start.sh
sudo systemctl daemon-reload
sudo systemctl enable --now lianhuan-web
sudo systemctl status lianhuan-web
curl -sS "http://127.0.0.1:${LIANHUAN_PORT:-8092}/api/version"
```

## 7. HTTPS 反向代理（本 VPS：Nginx + 宝塔）

你的机器 **80/443 已是 Nginx**，不要另装 Caddy。脸幻只在本机 **8092** 起 uvicorn，由 Nginx 反代。

**宝塔面板（推荐）**

1. 网站 → 添加站点 → 域名填 `facefusion.iqiyia.cyou`
2. 站点 → SSL → Let's Encrypt 申请证书
3. 站点 → 反向代理 → 目标 URL：`http://127.0.0.1:8092`
4. 保存后测试：`curl -sS https://facefusion.iqiyia.cyou/api/version`

**或手动 Nginx**：参考仓库 `deploy/nginx-facefusion.conf`

```bash
sudo nginx -t && sudo nginx -s reload
```

## 7b. 若不用宝塔、单独用 Caddy 时

见 `deploy/Caddyfile`（`reverse_proxy 127.0.0.1:8092`）。**当前 VPS 请用上一节 Nginx 方式。**

## 8. 后台初次设置

1. 打开 https://facefusion.iqiyia.cyou/login
2. 用 env 里的管理员登录
3. **USDT 收款**：填 TRC20 地址和价格
4. **发版号**：填 `YYYYMMDD`

## 9. 客户端 API 地址

绿色包 / 安装包内 `internal/app/lianhuan_api.txt` 写一行：

```
https://facefusion.iqiyia.cyou
```

## 10. 备份

```bash
# 每日备份 SQLite
cp /opt/lianhuan/app/web/data/lianhuan.db ~/backup/lianhuan-$(date +%F).db
```

## 11. 更新 WEB

```bash
cd /opt/lianhuan/app && git pull
sudo systemctl restart lianhuan-web
```
