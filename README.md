# 脸幻

本地换脸 · 中文界面。软件在你电脑上运行，不是云端。

## Windows 客户端

1. 解压绿色包或安装后，双击 **启动换脸.bat**
2. 黑窗提示「正在启动 / 可能下载模型」时请勿关闭
3. 登录窗：**免费试用** 或 **邮箱付费登录**（须联网）
4. 浏览器打开后：「脸」放人脸照 →「原图/视频」放素材 → 点「开始」

开发环境：安装 Miniconda 后执行 `python install.py directml`，再双击 `启动换脸.bat`。

## 网站与会员

- 官网注册邮箱，**TRC20 USDT** 购买会员后，客户端用同一邮箱登录
- 试用不限天数，是否开放由后台控制

## VPS 部署网站（一键）

```bash
curl -fsSL https://raw.githubusercontent.com/e12games/facefusion/main/deploy/vps-install.sh | bash
```

默认端口 **8092**（仅本机）。宝塔 / Nginx 将域名反代到 `http://127.0.0.1:8092`。

部署后编辑 `/etc/lianhuan.env` 修改管理员密码，详见 `deploy/DEPLOY.md`。

## 发版

见 [RELEASE.md](RELEASE.md)
