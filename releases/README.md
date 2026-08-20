# 脸幻 · 客户端热更新发布包

公开仓库：[e12games/facefusion-releases](https://github.com/e12games/facefusion-releases)

- **客户端下载**：`https://raw.githubusercontent.com/e12games/facefusion-releases/main/files/…`
- **manifest**：`https://raw.githubusercontent.com/e12games/facefusion-releases/main/manifest.json`
- VPS 可 clone 到 `/opt/lianhuan/releases` 作缓存（可选，客户端不依赖本站 `/releases/`）

## 目录

| 路径 | 说明 |
|------|------|
| `manifest.json` | 版本号与文件清单 |
| `files/` | 热更新文件（路径对应绿色包 `internal/app/`） |

## 发版

```bash
# 1. 把要更新的文件放进 files/
# 2. 生成 manifest
python scripts/build_release_manifest.py 20260820.3 "更新说明"

# 3. 推送到本仓库
bash scripts/publish_releases_repo.sh
```

推送后客户端即可通过 GitHub Raw 下载，无需改域名。
