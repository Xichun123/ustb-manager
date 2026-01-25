# USTB Manager 部署指南

## 部署场景选择

根据服务器位置的不同，需要选择不同的部署方案：

### 场景对比表

| 场景 | 服务器位置 | 访问方式 | 推荐方案 | 难度 | 性能 |
|------|-----------|---------|---------|------|------|
| **场景 1** | 校园网内 | 直连 | ✅ 推荐 | ⭐ 简单 | ⭐⭐⭐ 快 |
| **场景 2** | 校外 VPS | WebVPN | ❌ 不推荐 | ⭐⭐⭐ 复杂 | ⭐ 慢 |
| **场景 3** | 校外 VPS + 校内代理 | 代理转发 | ⚠️ 可选 | ⭐⭐ 中等 | ⭐⭐ 中等 |

---

## 场景 1: 校园网内部署 ✅ **强烈推荐**

### 适用情况
- 服务器在校园网内（实验室服务器、宿舍服务器、校内云平台等）
- 可以直接访问 `http://202.204.60.7`

### 优势
- ✅ **无需 WebVPN**：直接访问校园网系统
- ✅ **代码简单**：不需要处理 WebVPN JavaScript 注入
- ✅ **速度快**：低延迟，高可靠性
- ✅ **稳定性高**：不依赖 WebVPN 服务
- ✅ **资源占用少**：不需要浏览器自动化

### 部署步骤

#### 1. 修改配置文件

编辑 `backend/app/api/wifi.py`，切换到直连模式：

```python
# 将这行
from app.services.wifi_service import login_vpn_only, get_user_flow, wifi_store

# 改为
from app.services.wifi_service_direct import login_backend_system, get_user_flow, wifi_store
```

#### 2. 修改登录逻辑

在 `backend/app/api/wifi.py` 中修改 `wifi_login` 函数：

```python
@router.post("/login")
async def wifi_login(body: WifiLoginRequest, current_user: dict = Depends(get_current_user)):
    """校园网登录（校内直连模式）"""
    student_id = current_user["student_id"]

    try:
        # 使用直连模式登录
        session_id, client = await login_backend_system(student_id, body.password)

        if not session_id:
            raise HTTPException(status_code=401, detail="校园网账号或密码错误")

        # 保存会话
        session = WifiSession(
            client=client,
            student_id=student_id,
            session_id=session_id
        )
        wifi_store.set(student_id, session)

        return {"message": "登录成功"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")
```

#### 3. 启动服务

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. 用户访问方式

**校内用户**：
- 直接访问服务器 IP 或域名
- 例如：`http://192.168.1.100:5173`

**校外用户**：
- 先连接学校 VPN（不是 WebVPN，是学校提供的 VPN 客户端）
- 然后访问服务器 IP

### 测试验证

```bash
# 测试是否能访问校园网系统
curl http://202.204.60.7/Self/login/

# 应该返回登录页面的 HTML
```

---

## 场景 2: 校外 VPS 部署 ❌ **不推荐**

### 适用情况
- 服务器在校外（阿里云、腾讯云等）
- 必须通过 WebVPN 访问校园网系统

### 问题
- ❌ WebVPN JavaScript 注入问题
- ❌ httpx 客户端无法正常登录
- ❌ 需要浏览器自动化（资源消耗大）
- ❌ 稳定性差

### 解决方案（如果必须使用）

#### 方案 A: 使用浏览器自动化

安装 Playwright：
```bash
pip install playwright
playwright install chromium
```

修改代码使用 Playwright 登录：
```python
from playwright.async_api import async_playwright

async def login_via_browser(account: str, password: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 访问 WebVPN 登录页
        await page.goto("https://elib.ustb.edu.cn/login")

        # 填写表单并登录
        # ... (详细代码见 self_system_api.md)

        await browser.close()
```

**缺点**：
- 资源消耗大（每次登录需要启动浏览器）
- 速度慢（需要等待页面加载）
- 维护成本高

#### 方案 B: 使用校内代理（见场景 3）

---

## 场景 3: 校外 VPS + 校内代理 ⚠️ **可选方案**

### 架构

```
用户 → 校外 VPS → 校内代理服务器 → 校园网系统
```

### 部署步骤

#### 1. 在校内部署代理服务器

在校内服务器上运行一个简单的 HTTP 代理：

```python
# proxy_server.py
from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/<path:path>', methods=['GET', 'POST'])
def proxy(path):
    url = f"http://202.204.60.7/{path}"

    if request.method == 'GET':
        resp = requests.get(url, params=request.args, headers=request.headers)
    else:
        resp = requests.post(url, data=request.form, headers=request.headers)

    return Response(resp.content, status=resp.status_code, headers=dict(resp.headers))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)
```

#### 2. 配置校外 VPS

修改 `wifi_service_direct.py` 中的 URL：

```python
# 使用代理服务器地址
PROXY_HOST = "校内代理服务器IP:8888"
AUTH_BACKEND_LOGIN_URL = f"http://{PROXY_HOST}/8080/nav_login"
AUTH_SELF_LOGIN_URL = f"http://{PROXY_HOST}/Self/login/"
```

### 优缺点

**优点**：
- ✅ 可以在校外 VPS 部署
- ✅ 不需要浏览器自动化
- ✅ 代码相对简单

**缺点**：
- ❌ 需要维护两台服务器
- ❌ 校内代理服务器需要稳定运行
- ❌ 增加了一层网络延迟

---

## 推荐配置

### 最佳实践：校内部署

如果可能，**强烈建议在校园网内部署**：

1. **实验室服务器**：
   - 联系实验室老师申请服务器
   - 配置固定 IP
   - 设置开机自启动

2. **宿舍服务器**：
   - 使用树莓派或旧电脑
   - 配置内网穿透（frp、ngrok）供校外访问
   - 注意：需要保持 24 小时运行

3. **校内云平台**：
   - 如果学校提供云平台服务
   - 申请虚拟机或容器

### 网络配置

#### 校内访问
```
用户设备 → 校园网 → 服务器
```

#### 校外访问
```
用户设备 → 学校VPN → 校园网 → 服务器
```

或使用内网穿透：
```
用户设备 → 公网 → frp服务器 → 校园网 → 服务器
```

---

## 环境变量配置

创建 `.env` 文件：

```bash
# 部署模式
DEPLOYMENT_MODE=direct  # direct: 校内直连, webvpn: 通过WebVPN

# 校园网系统选择
WIFI_SYSTEM=backend  # backend: 8080系统, self: Self系统

# 数据库配置
DATABASE_URL=sqlite:///./ustb_manager.db

# JWT 密钥
SECRET_KEY=your-secret-key-here
```

---

## 常见问题

### Q1: 如何判断服务器是否在校园网内？

**测试方法**：
```bash
# 在服务器上执行
curl http://202.204.60.7/Self/login/

# 如果返回登录页面 HTML，说明在校园网内
# 如果超时或无法访问，说明在校外
```

### Q2: 校内部署后，校外用户如何访问？

**方案 1**: 使用学校 VPN
- 用户先连接学校提供的 VPN 客户端
- 然后访问服务器 IP

**方案 2**: 使用内网穿透
- 在服务器上配置 frp 客户端
- 通过公网域名访问

### Q3: 8080 系统和 Self 系统选哪个？

**推荐使用 8080 系统**：
- ✅ 接口更简单
- ✅ 数据更完整
- ✅ 更稳定

**Self 系统**：
- ⚠️ 需要解析 HTML
- ⚠️ 数据在页面中渲染
- ✅ 界面更友好（如果需要展示）

### Q4: 如何提高稳定性？

1. **使用 systemd 管理服务**：
```bash
# /etc/systemd/system/ustb-manager.service
[Unit]
Description=USTB Manager Backend
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/backend
ExecStart=/path/to/uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

2. **配置日志轮转**
3. **设置健康检查**
4. **使用 Nginx 反向代理**

---

## 性能对比

| 指标 | 校内直连 | 校外 WebVPN | 校外 + 代理 |
|------|---------|------------|------------|
| 响应时间 | ~50ms | ~2000ms | ~200ms |
| 成功率 | 99%+ | 60-80% | 90%+ |
| 资源占用 | 低 | 高（浏览器） | 中 |
| 维护成本 | 低 | 高 | 中 |

---

## 总结

**如果你的服务器在校园网内**：
- ✅ 使用 `wifi_service_direct.py`
- ✅ 直接访问 `http://202.204.60.7`
- ✅ 简单、快速、稳定

**如果你的服务器在校外**：
- ⚠️ 考虑在校内部署代理
- ⚠️ 或使用浏览器自动化（不推荐）
- ⚠️ 或重新考虑部署位置

**最佳建议**：在校园网内部署！
