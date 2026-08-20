# 脸幻发布 Checklist

版本号：**YYYYMMDD**（同日再发用 `20260820.2`）。不强制客户端升级。

---

## A. 改代码后（WEB）

- [ ] 本地测：注册 / 登录 / 试用 API / 购买 USDT 提交流程
- [ ] 若改了客户端脚本：放入 `web/releases/files/`（路径对应 `internal/app/`）
- [ ] 生成 manifest：
  ```bash
  python scripts/build_release_manifest.py 20260821 "更新说明"
  ```
- [ ] 后台 `/admin` 保存版本号（可勾选同步 manifest）
- [ ] VPS：`git pull` + `systemctl restart lianhuan-web`
- [ ] 浏览器访问 `/api/version` 确认版本

## B. 改代码后（客户端 / 绿色包）

- [ ] 更新 `lianhuan_version.txt`
- [ ] 运行同步脚本：
  ```powershell
  scripts\sync_portable.bat
  ```
- [ ] 确认 `internal/app/lianhuan_api.txt` 为 **正式 HTTPS 域名**
- [ ] 本机双击 `启动换脸.bat` 走通：更新检查 → 登录 → 换脸

## C. 打安装包（Inno）

- [ ] 取消绿色包 `internal` 隐藏属性：
  ```bat
  attrib -h "脸幻中文便携版\internal"
  ```
- [ ] 编译：
  ```powershell
  powershell -File scripts/build_installer.ps1
  ```
- [ ] 输出：`installer-output\LianHuanZH-Setup.exe`

## D. 上线卖会员

- [ ] 后台填 **TRC20 USDT 收款地址** 和价格
- [ ] 首页 /buy 能打开，测试一笔小额 USDT
- [ ] 自动确认或后台「确认开通」后，客户端付费登录成功

## E. 热更新演练（建议每次发版做一次）

### E1. 探针发版（绿色包保持 20260820）

1. 确认探针文件已在仓库：`web/releases/files/lianhuan_probe.txt`
2. 本地生成 manifest（或 git pull 后 VPS 上已有）：
   ```bash
   python scripts/build_release_manifest.py 20260820.2 "探针测试"
   ```
3. 推送到 GitHub，VPS 执行：
   ```bash
   cd /opt/lianhuan/app && git pull && systemctl restart lianhuan-web
   ```
4. 后台 `/admin` → **版本与更新**：
   - 当前版本填 **`20260820.2`**
   - 勾选「允许客户端在线更新」
   - 勾选「同时写 manifest.json 版本号」→ 保存
5. 浏览器验证：
   - `https://facefusion.iqiyia.cyou/api/version` → `version` 为 `20260820.2`
   - `https://facefusion.iqiyia.cyou/releases/files/lianhuan_probe.txt` → 能下载
6. **绿色包不要改** `internal/app/lianhuan_version.txt`（保持 `20260820`）
7. 双击 `启动换脸.bat` → 应弹出「发现新版本 20260820.2」→ 点「是」
8. 更新成功后检查：
   - `internal/app/lianhuan_probe.txt` 存在
   - `internal/app/lianhuan_version.txt` 变为 `20260820.2`
   - `internal/update/state.json` 中 `version` 为 `20260820.2`

### E2. 错误哈希回滚

1. 在 VPS 上临时改 `web/releases/manifest.json` 里探针文件的 `sha256` 为错误值
2. 把绿色包版本改回 `20260820`（或删 `state.json` 后改版本文件），再启动
3. 点「是」更新 → 应提示失败并已恢复，原文件未被破坏
4. 改回正确 manifest 后再测一次成功路径

### E3. 真文件热更（探针通过后）

1. 把新版 `lianhuan_login.py` 等复制到 `web/releases/files/`（路径即 `internal/app/` 相对路径）
2. 发版号如 `20260820.3`，重新 `build_release_manifest.py` → git pull → 后台保存版本
3. 客户端（版本落后）启动应提示并更新

**白名单规则**：仅允许写入 `internal/app/` 下相对路径；禁止 `..`、绝对路径、`.assets/models/`、`runtime/`。

---

## 文件速查

| 用途 | 路径 |
|------|------|
| WEB | `web/app.py` |
| 更新 manifest | `web/releases/manifest.json` |
| 更新文件 | `web/releases/files/` |
| 客户端 API | `internal/app/lianhuan_api.txt` |
| 绿色包 | `脸幻中文便携版/` |
| 安装脚本 | `installer/lianhuan.iss` |
