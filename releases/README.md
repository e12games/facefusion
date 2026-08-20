# 脸幻 · 客户端热更新发布包

公开仓库，供 VPS 拉取；客户端通过 `https://facefusion.iqiyia.cyou/releases/` 下载。

## 目录

| 路径 | 说明 |
|------|------|
| `manifest.json` | 版本号与文件清单 |
| `files/` | 热更新文件（路径对应绿色包 `internal/app/`） |

## 发版（本地）

```bash
# 1. 把要更新的文件放进 files/
# 2. 生成 manifest
python scripts/build_release_manifest.py 20260820.3 "更新说明"

# 3. 推送到本仓库
bash scripts/publish_releases_repo.sh
```

## VPS

后台 `/admin` → **客户端发布包** → **拉取发布包**，或安装脚本自动 clone 到 `/opt/lianhuan/releases`。
