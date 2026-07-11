# USTB Manager

北京科技大学教务管理系统 API 服务

## 功能

- 二维码/短信验证码登录
- 成绩查询与 GPA 计算
- 课表查询（周课表/总课表）
- 考试安排查询
- 选课查询与安全写操作
- 通知公告与校历
- 校园网管理
- 学业进度与学业警示

## 部署

### Docker 部署（推荐）

```bash
mkdir -p /opt/ustb-manager
cd /opt/ustb-manager

# 从仓库复制这两个文件
cp /path/to/ustb-manager/docker-compose.yml .
cp /path/to/ustb-manager/.env.example .env

# 生成 Fernet 密钥，并将输出填入 .env 的 SESSION_ENCRYPTION_KEY
python3 -c 'import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'

# 首次启动
docker compose pull
docker compose up -d

# 查看状态
docker compose ps
docker compose logs -f
```

当前 `docker-compose.yml` 的行为：

- `backend` 使用镜像 `xichun/ustb-manager-backend:${IMAGE_TAG}`
- `frontend` 使用镜像 `xichun/ustb-manager-frontend:${IMAGE_TAG}`
- `IMAGE_TAG` 必须是不可变发布标签，不允许依赖 `latest`
- 前端只监听 `127.0.0.1:${APP_PORT:-8032}`，默认不会直接暴露到公网
- 后端不单独映射端口，只在 Docker 网络内提供给前端访问
- 后端会话保存到 Docker volume `backend-data` 中的 SQLite 数据库
- 上游 Cookie 使用 Fernet 加密，Session Token 仅保存 SHA-256 哈希
- 缺少 `SESSION_ENCRYPTION_KEY` 时后端拒绝启动；更换密钥会使已有登录失效
- 升级到 SQLite 存储时会直接删除旧 `cookies.json` / `session_map.json`，用户需重新登录
- `frontend` 依赖 `backend` 的 readiness 检查结果再启动

完整发布、升级和回滚步骤见 [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)。

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
export SESSION_ENCRYPTION_KEY="$(python3 -c 'import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')"
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

本地重启后若要恢复已有会话，请复用同一个 `SESSION_ENCRYPTION_KEY`，不要每次重新生成。

**前端：**
```bash
cd frontend
npm ci
npm run generate:api
npm run dev
```

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

**小程序类型检查：**
```bash
cd miniapp
npm ci
npx tsc --noEmit
```

**后端门禁：**
```bash
cd backend
uv sync --frozen --group dev
uv run ruff check app tests scripts
uv run pytest -q
uv run python scripts/export_openapi.py --check
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| IMAGE_TAG | 后端与前端共用的不可变镜像标签 | 必填 |
| APP_PORT | 前端绑定到本机的端口 | 8032 |
| COOKIE_SECURE | Cookie 仅 HTTPS 传输 | true |
| SESSION_TTL | 会话空闲有效期（秒） | 31536000 |
| SESSION_MAX_AGE | 会话绝对有效期（秒） | 31536000 |
| SESSION_ENCRYPTION_KEY | Fernet 密钥；缺失时后端拒绝启动 | 必填 |

## License

MIT
