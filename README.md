# USTB Manager

北京科技大学教务管理系统 API 服务

## 功能

- 二维码/短信验证码登录
- 成绩查询与 GPA 计算
- 课表查询（周课表/总课表）
- 考试安排查询
- 选课查询
- 校园网管理
- 学业进度查询

## 部署

### Docker 部署（推荐）

```bash
mkdir -p /opt/ustb-manager
cd /opt/ustb-manager

# 从仓库复制这两个文件
cp /path/to/ustb-manager/docker-compose.yml .
cp /path/to/ustb-manager/.env.example .env

# 首次启动
docker compose pull
docker compose up -d

# 查看状态
docker compose ps
docker compose logs -f
```

当前 [docker-compose.yml](/Users/xichun/Downloads/code/ustb-manager/docker-compose.yml) 的行为：

- `backend` 使用镜像 `xichun/ustb-manager-backend:${IMAGE_TAG:-latest}`
- `frontend` 使用镜像 `xichun/ustb-manager-frontend:${IMAGE_TAG:-latest}`
- 前端只监听 `127.0.0.1:${APP_PORT:-8032}`，默认不会直接暴露到公网
- 后端不单独映射端口，只在 Docker 网络内提供给前端访问
- 后端数据持久化到 Docker volume `backend-data`
- `frontend` 依赖 `backend` 的健康检查结果再启动

### 反代（推荐）

```
ustb.example.com {
    reverse_proxy 127.0.0.1:8032
}
```

如果你还没配 HTTPS，请先把 `.env` 里的 `COOKIE_SECURE=false`，否则浏览器不会在纯 HTTP 下发送登录 Cookie。

## 本地开发

**后端：**
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端：**
```bash
cd frontend
npm install
npm run dev
```

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| IMAGE_TAG | Docker 镜像标签 | latest |
| APP_PORT | 前端绑定到本机的端口 | 8032 |
| COOKIE_SECURE | Cookie 仅 HTTPS 传输 | true |
| SESSION_TTL | 会话有效期（秒） | 31536000 |

## License

MIT
