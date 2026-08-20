# 脸幻网站

介绍站 + 后台 + USDT(TRC20) 会员 + 在线更新 API。

## 本地启动

```
web\run.bat
```

管理员默认：`admin@local.test` / `admin123`

## 会员支付（TRC20 USDT）

1. 后台填写收款地址和价格
2. 用户登录后打开 `/buy`，转账后提交交易哈希
3. 系统自动查 TronGrid；失败则订单待确认，管理员可手动开通

## 部署

见 [deploy/DEPLOY.md](../deploy/DEPLOY.md)

## 发版

见 [RELEASE.md](../RELEASE.md)
