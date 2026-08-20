# 脸幻（FaceFusion 中文发行）

本地换脸 · 中文界面。运算在本机，结果保存在本机。

官网：https://facefusion.iqiyia.cyou/  
源码：https://github.com/e12games/facefusion  
客户端热更新包（公开仓）：https://github.com/e12games/facefusion-releases

---

## 一、Windows 客户端怎么用

1. 解压绿色包（或安装）后，双击 **启动换脸.bat**
2. 黑窗提示下载/解压模型时，请勿关闭
3. 登录窗可选：
   - **免费试用**（需联网，后台可关）
   - **账号登录**（网站注册邮箱；有免费启动次数，用完需买会员）
4. 浏览器打开后：「脸」放人脸照 →「原图/视频」放素材 →「开始」→「结果」查看

可选：登录窗点 **检查更新**（从公开仓拉取热更新文件）。

开发机：安装 Miniconda → `python install.py directml` → 再运行 `启动换脸.bat`。

---

## 二、网站：注册 / 会员 / 后台

| 功能 | 说明 |
|------|------|
| 注册 | 邮箱注册；后台可开「必须填注册码」 |
| 试用 | 客户端「免费试用」，不限天，后台开关 |
| 会员 | TRC20 USDT，价格后台可改（默认 20 USDT/月） |
| 默认管理员 | `admin@lianhuan.local` / `admin123`（进后台请改密） |

购买：登录官网 → **购买会员** → 转账后提交交易哈希。

---

## 三、VPS 一键部署网站

```bash
curl -fsSL https://raw.githubusercontent.com/e12games/facefusion/main/deploy/vps-install.sh | bash
```

- 本机端口默认 **8092**
- 宝塔 / Nginx 反代到 `http://127.0.0.1:8092`
- 配置文件：`/etc/lianhuan.env`
- 详细说明：`deploy/DEPLOY.md`、`deploy/BAOTA.md`

后台可：**WEB 一键更新**、**客户端发版号**、拉取公开仓发布包。

主仓若为私有，需在 `/etc/lianhuan.env` 设置 `GITHUB_TOKEN`。

---

## 四、客户端热更新怎么发

1. 改文件放入 `releases/files/`（路径对应绿色包 `internal/app/`）
2. `python scripts/build_release_manifest.py 20260820.3 "说明"`
3. `bash scripts/publish_releases_repo.sh` → 推到 **facefusion-releases**
4. 客户端从 GitHub Raw 下载，不依赖本站 `/releases/`

详见 [RELEASE.md](RELEASE.md)。

---

## 五、常用目录

| 路径 | 用途 |
|------|------|
| `启动换脸.bat` | 开发启动 |
| `portable/` / 绿色包 | 用户端 |
| `web/` | 官网 + 后台 + API |
| `deploy/` | VPS 安装与更新脚本 |
| `releases/` | 热更新内容（同步到公开仓） |
| `installer/` | Inno 安装包脚本 |
