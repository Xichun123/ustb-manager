import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .byyt.errors import BYYTRateLimited, BYYTUnavailable, BYYTUpstreamError
from .config import CORS_ORIGINS
from .services.session_store import store
from .api import (
    academic,
    auth,
    course_selection,
    courses,
    exams,
    grades,
    me,
    notices,
    schedule,
    wifi,
)
from .exceptions import (
    BYYTSessionExpired,
    byyt_rate_limited_handler,
    byyt_session_expired_handler,
    byyt_unavailable_handler,
    byyt_upstream_error_handler,
    generic_exception_handler,
)

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.start_cleanup()
    yield
    store.stop_cleanup()


app = FastAPI(
    title="USTB Manager API",
    description="""
## USTB Manager - 北科大教务管理系统API

这是一个用于访问北京科技大学教务系统的API服务，提供以下功能：

### 🔐 认证模块 (Authentication)
- **二维码登录**: 使用微信扫码快速登录
- **短信验证码登录**: 通过手机号接收验证码登录
- **Cookie登录**: 使用浏览器Cookie直接登录（高级用户）
- **会话管理**: 自动管理用户会话，支持后端重启后恢复

### 📊 成绩查询模块 (Grades)
- **成绩列表**: 支持分页、筛选的成绩查询
- **GPA计算**: 自动计算总GPA和加权GPA
- **学生信息**: 获取学生基本信息和完整档案
- **培养方案**: 查看专业培养方案和课程要求
- **学业进度**: 查询必修课完成情况和学分统计

### 🔒 安全特性
- HttpOnly Cookie保护
- Session自动过期和清理
- Cookie有效性验证
- 支持CORS跨域访问

### 📝 使用说明
1. 首先调用认证接口（QR/SMS/Cookie）完成登录
2. 登录成功后会自动设置session cookie
3. 后续请求会自动携带cookie进行认证
4. 可以调用 `/api/auth/status` 检查登录状态
5. 使用 `/api/auth/logout` 退出登录

### 🌐 环境信息
- 开发环境: http://localhost:8000
- API前缀: `/api`
- 文档地址: `/docs` (Swagger UI) 或 `/redoc` (ReDoc)

### 📞 技术支持
如有问题，请查看各接口的详细文档说明。
    """,
    version="1.0.0",
    contact={
        "name": "USTB Manager",
        "url": "https://github.com/yourusername/ustb-manager",
    },
    license_info={
        "name": "MIT License",
    },
    openapi_tags=[
        {
            "name": "auth",
            "description": "**认证相关接口** - 用户登录、登出、会话管理等功能。支持三种登录方式：二维码、短信验证码、Cookie。",
        },
        {
            "name": "me",
            "description": "**个人信息接口** - 查询当前学生的规范化档案与角色。",
        },
        {
            "name": "grades",
            "description": "**成绩管理接口** - 成绩查询、GPA计算、学生信息、培养方案、学业进度等功能。提供丰富的筛选和统计功能。",
        },
        {
            "name": "schedule",
            "description": "**课表查询接口** - 查询总课表和周课表，支持按学期和周次查询。",
        },
        {
            "name": "exams",
            "description": "**考试查询接口** - 分页查询学生考试安排。",
        },
        {
            "name": "wifi",
            "description": "**校园网管理接口** - 校园网登录、流量查询、月度账单、MAC地址管理等功能。",
        },
        {
            "name": "course-selection",
            "description": "**新版选课接口** - 动态上下文、可选课程、已选课程、购物车与日志。",
        },
        {
            "name": "courses",
            "description": "**选课管理接口** - 查询已选课程、开课学期、学院列表、课程类别等选课相关功能。",
        },
        {
            "name": "notices",
            "description": "**通知公告接口** - 分页查询教务系统通知公告。",
        },
    ],
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理器
app.add_exception_handler(BYYTSessionExpired, byyt_session_expired_handler)
app.add_exception_handler(BYYTRateLimited, byyt_rate_limited_handler)
app.add_exception_handler(BYYTUnavailable, byyt_unavailable_handler)
app.add_exception_handler(BYYTUpstreamError, byyt_upstream_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(auth.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(academic.router, prefix="/api")
app.include_router(grades.router, prefix="/api")
app.include_router(exams.router, prefix="/api")
app.include_router(notices.router, prefix="/api")
app.include_router(schedule.router, prefix="/api")
app.include_router(wifi.router, prefix="/api")
app.include_router(course_selection.router, prefix="/api")
app.include_router(courses.router, prefix="/api")


@app.get("/api/health", tags=["system"], summary="健康检查")
async def health():
    """
    ## 业务说明
    检查API服务是否正常运行。

    ## 使用场景
    - 服务监控
    - 负载均衡健康检查
    - 部署验证

    ## 返回数据
    返回服务状态信息。

    ## 注意事项
    - 此接口不需要认证
    - 始终返回200状态码（除非服务完全不可用）
    """
    return {"status": "ok"}
