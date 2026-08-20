# 宝塔反向代理（facefusion.iqiyia.cyou）

本地服务：`http://127.0.0.1:8092`（curl 已通即可）

## 必改项

在 **反向代理** 弹窗里：

| 项 | 错误示例 | 正确填法 |
|----|----------|----------|
| 目标 URL | http://127.0.0.1:8092 | 同上 ✓ |
| **发送域名** | **127.0.0.1** ❌ | **facefusion.iqiyia.cyou** ✓ |

「发送域名」填 `127.0.0.1` 会导致 **Internal Server Error** 或静态资源异常。

代理目录：`/`

## 自定义 Nginx 配置（可选）

站点 → 配置文件，在 `location /` 的 proxy 段确保有：

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

保存后重载 Nginx。

## 验证

```bash
curl -sS http://127.0.0.1:8092/
curl -sSI -H "Host: facefusion.iqiyia.cyou" http://127.0.0.1:8092/
```

浏览器访问：https://facefusion.iqiyia.cyou/

仍 500 时：

```bash
journalctl -u lianhuan-web -n 30 --no-pager
tail -n 30 /www/wwwlogs/facefusion.iqiyia.cyou.error.log
```
