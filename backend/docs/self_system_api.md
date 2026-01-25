# Self 系统 API 接口文档

## 概述

Self 系统是北京科技大学校园网用户自助服务系统，提供账户管理、流量查询、在线记录等功能。

**基础信息**
- 系统地址: `http://202.204.60.7/Self/`
- WebVPN 地址: `https://elib.ustb.edu.cn/https/77726476706e69737468656265737421a2a713d275603c1e2858c7fb/Self/`
- 开发商: 广州热点软件科技股份有限公司

## 重要发现

### 浏览器登录成功的关键

通过浏览器测试发现，Self 系统的登录**在浏览器中是可以成功的**！关键在于：

1. **动态路由参数**: 浏览器的 JavaScript 会自动在 URL 后添加 `?vpn-12-o2-202.204.60.7` 这样的动态参数
2. **WebVPN JavaScript 注入**: WebVPN 会注入 JavaScript 代码来处理表单提交和 cookie 同步
3. **自动 cookie 管理**: 浏览器会自动管理 WebVPN 的 cookie

### 为什么 httpx 客户端失败

使用 Python httpx 客户端直接模拟登录会失败，因为：
- 缺少 WebVPN JavaScript 注入的动态参数
- 无法复制浏览器的 cookie 同步机制
- WebVPN 会检测并阻止非浏览器的请求

## 登录流程

### 1. 登录页面
**URL**: `/Self/login/`

**页面元素**:
```html
<form action="/Self/login/verify" method="post">
    <input name="foo" type="hidden" value="">
    <input name="bar" type="hidden" value="">
    <input name="checkcode" type="hidden" value="[动态生成]">
    <input name="account" type="text">
    <input name="password" type="password">
    <input name="code" type="text">
</form>
```

**关键字段**:
- `checkcode`: 动态生成的验证码，从页面 HTML 中提取
- `account`: 学号
- `password`: MD5 加密后的密码
- `code`: 图形验证码（通常为空）

### 2. 登录验证
**URL**: `/Self/login/verify`
**方法**: POST
**Content-Type**: `application/x-www-form-urlencoded`

**请求参数**:
```
foo=&bar=&checkcode=[从页面提取]&account=[学号]&password=[MD5密码]&code=
```

**成功响应**: 302 重定向到 `/Self/dashboard`
**失败响应**: 302 重定向回 `/Self/login/`

## Dashboard API

### 1. 刷新账户信息
**URL**: `/Self/dashboard/refreshaccount`
**方法**: GET
**参数**:
- `csrftoken`: CSRF 令牌
- `t`: 时间戳（随机数）

**响应**: 空响应（数据已在页面 HTML 中）

### 2. 获取登录历史
**URL**: `/Self/dashboard/getLoginHistory`
**方法**: GET
**参数**:
- `t`: 时间戳
- `order`: 排序方式（asc/desc）
- `_`: 时间戳

**响应示例**:
```json
[[1769012268000,1769014078000,"115.25.60.54","000000000000",31,0,2,0,null,"#PC","PC",1]]
```

**字段说明**:
- [0]: 上线时间（毫秒时间戳）
- [1]: 注销时间（毫秒时间戳）
- [2]: IP 地址
- [3]: MAC 地址
- [4]: 使用时长（分钟）
- [5]: 使用流量（MB）
- [6]: 计费方式（2=流量）
- [7]: 计费金额
- [8]: null
- [9]: 主机名标识
- [10]: 终端类型
- [11]: 记录 ID

### 3. 获取在线列表
**URL**: `/Self/dashboard/getOnlineList`
**方法**: GET
**参数**:
- `t`: 时间戳
- `order`: 排序方式
- `_`: 时间戳

**响应**: 在线设备列表（当前无在线设备时返回 `[]`）

### 4. 刷新无感知认证类型
**URL**: `/Self/dashboard/refreshMauthType`
**方法**: GET
**参数**:
- `t`: 时间戳

**响应**: 无感知认证状态

## 数据结构

### 用户信息（从 Dashboard HTML 提取）

```json
{
  "account": "U202440984",
  "status": "正常",
  "package": "学生用户",
  "balance": "0.00",
  "used_flow": "0",
  "available_flow": "122880",
  "billing_method": "按使用流量计费",
  "billing_cycle": "2026-01-01 至 2026-02-01",
  "expire_date": "2028-09-15"
}
```

### 套餐信息
```
学生用户
赠122880MB，超出0.0006元/MB，4点登录，单向计费
```

**说明**:
- 每月赠送 120GB 流量
- 超出部分按 0.0006 元/MB 计费（约 0.6 元/GB）
- 4点登录（可能指凌晨4点自动登录）
- 单向计费（只计下载流量）

## 实现建议

### 方案 1: 使用浏览器自动化（推荐）

由于 Self 系统在浏览器中可以正常登录，建议使用浏览器自动化方案：

1. 使用 Playwright 或 Selenium
2. 通过 WebVPN 访问 Self 系统
3. 自动填写表单并登录
4. 从 Dashboard 页面提取数据

**优点**:
- 可以完全模拟浏览器行为
- 不需要处理复杂的 WebVPN JavaScript 注入
- 稳定性高

**缺点**:
- 需要运行浏览器，资源消耗较大
- 速度相对较慢

### 方案 2: 直接解析 Dashboard HTML

如果能够成功登录（通过浏览器自动化），可以直接解析 Dashboard 页面的 HTML 来获取数据：

```python
from bs4 import BeautifulSoup

def parse_dashboard(html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')

    # 提取流量信息
    dls = soup.select('.user-info1 dl')
    data = {}

    for dl in dls:
        dt = dl.select_one('dt')
        dd = dl.select_one('dd')
        if dt and dd:
            value = dt.get_text().strip()
            label = dd.get_text().strip()

            if label == '已用流量':
                data['used_flow'] = float(value.replace('M', ''))
            elif label == '可用流量':
                data['available_flow'] = float(value.replace('M', ''))
            elif label == '账户余额':
                data['balance'] = float(value.replace('元', ''))

    return data
```

### 方案 3: 寻找替代 API

继续探索是否有其他可以通过 WebVPN 访问的校园网管理接口，例如：
- 移动端 API
- 其他端口的管理系统
- 直接的流量查询接口

## 注意事项

1. **WebVPN 限制**: 8080 端口的后台管理系统目前被 WebVPN 阻止访问
2. **动态参数**: Self 系统的 API 请求需要动态的 `vpn-12-o2-202.204.60.7` 参数
3. **Cookie 管理**: 需要正确管理 WebVPN 的 cookie
4. **CSRF 保护**: 部分接口需要 CSRF token

## 测试结果

- ✅ 浏览器登录: 成功
- ❌ httpx 直接登录: 失败（302 重定向回登录页）
- ✅ Dashboard 数据提取: 成功
- ✅ 登录历史 API: 成功
- ✅ 在线列表 API: 成功

## 下一步计划

1. 实现基于浏览器自动化的登录方案
2. 或者寻找其他可用的 API 接口
3. 考虑使用移动端 API（如果存在）
