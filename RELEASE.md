# 脸幻发布 Checklist

版本号：**YYYYMMDD**（同日再发用 `20260820.2`）。不强制客户端升级。

**客户端热更新文件** 放在公开仓 [facefusion-releases](https://github.com/e12games/facefusion-releases.git)，VPS 从 `/opt/lianhuan/releases` 读取。

---

## A. 改代码后（WEB）

- [ ] 本地测：注册 / 登录 / 试用 / 购买 USDT
- [ ] push 到 facefusion 主仓 → 后台 **拉取并重启 WEB**

## B. 客户端热更发版

- [ ] 把更新文件放进 **`releases/files/`**（路径对应 `internal/app/`）
- [ ] 生成 manifest：
  ```bash
  python scripts/build_release_manifest.py 20260820.3 "更新说明"
  ```
- [ ] 推送到公开仓：
  ```bash
  bash scripts/publish_releases_repo.sh
  ```
- [ ] VPS 后台 **拉取发布包**，或 SSH：`git -C /opt/lianhuan/releases pull`
- [ ] 后台保存客户端版本号（可勾选同步 manifest）
- [ ] 验证：`https://facefusion.iqiyia.cyou/releases/files/...` 可下载

## C. 绿色包 / 安装包

- [ ] 更新 `lianhuan_version.txt`（大版本时）
- [ ] `scripts\sync_portable.bat` → 测 `启动换脸.bat`

## D. VPS 一次性修复

```bash
cd /opt/lianhuan/app
sudo bash deploy/fix-web-git-sudo.sh
```

---

## 目录速查

| 用途 | 路径 |
|------|------|
| 主程序 WEB | `facefusion` 主仓 → `/opt/lianhuan/app` |
| **客户端热更新** | **`facefusion-releases` 公开仓 → `/opt/lianhuan/releases`** |
| manifest | `releases/manifest.json` |
| 更新文件 | `releases/files/` |
