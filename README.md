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
mkdir -p ~/ustb-manager && cd ~/ustb-manager

# 创建 docker-compose.yml
cat > docker-compose.yml << 'EOF'
services:
  backend:
    image: xichun/ustb-manager-backend:latest
    container_name: ustb-backend
    restart: unless-stopped
    environment:
      - COOKIE_SECURE=true
      - SESSION_TTL=31536000
    networks:
      - ustb-network

  frontend:
    image: xichun/ustb-manager-frontend:latest
    container_name: ustb-frontend
    restart: unless-stopped
    ports:
      - "127.0.0.1:8032:80"
    depends_on:
      - backend
    networks:
      - ustb-network

networks:
  ustb-network:
    driver: bridge
EOF

# 启动
docker compose up -d
```

### Caddy 反代（可选）

```
ustb.example.com {
    reverse_proxy 127.0.0.1:8032
}
```

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
| COOKIE_SECURE | Cookie 仅 HTTPS 传输 | false |
| SESSION_TTL | 会话有效期（秒） | 31536000 |

## License

MIT
