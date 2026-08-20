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

- [ ] 服务端 manifest 有至少 1 个文件
- [ ] 客户端版本故意落后，启动时应提示更新
- [ ] 更新后 `internal/update/state.json` 版本变新

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
