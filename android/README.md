# USTB Manager Android

独立的 Kotlin / Jetpack Compose 安卓客户端。客户端直接访问北京科技大学统一认证与本研一体教务系统，不依赖本仓库 FastAPI 后端。

## 当前功能

- APP 内学校统一身份认证（短信验证码、微信 / 企微扫码）
- 首页摘要
- 周课表
- 成绩与官方 GPA
- 考试安排
- 个人信息与退出登录

## 构建

要求：JDK 17、Android SDK 35。

```bash
cd android
./gradlew assembleDebug
```

调试 APK：`app/build/outputs/apk/debug/app-debug.apk`

## 安全说明

- 仅允许 HTTPS，不启用明文网络访问。
- 登录 Cookie 保存在 Android WebView 的应用私有 Cookie 存储中，并只发送给学校域名。
- APP 不收集或转发账号、短信验证码、Cookie 与教务数据。
- 上游接口发生变化时，客户端可能需要同步升级。
