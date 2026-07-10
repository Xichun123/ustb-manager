# USTB Manager 全面升级蓝图

> 版本：Draft 1
>
> 日期：2026-07-10
>
> 范围：FastAPI 后端、React Web、微信小程序
>
> 暂不包含：校园网模块的功能重构（仅要求升级期间不被破坏）

## 1. 已确认的项目决策

- 三端分阶段升级：后端基础与新版接口适配 → React Web → 微信小程序。
- 允许重新设计现有 API 和数据模型，不要求长期保持旧契约。
- 第一批覆盖全部核心教务模块：
  - 成绩与学业
  - 课表与考试
  - 选课与课程
  - 通知与个人信息
- 新功能由“用户核心需求 + 新版教务系统能力盘点”共同确定。
- 校园网模块后续独立升级，本轮只做必要的回归保护。
- 首个交付物为本升级蓝图，确认后再进入代码实施。

## 2. 执行摘要

当前项目具备可用的三端产品雏形，但后端直接依赖上游 BYYT 的 URL、参数名和原始字段，且缺少自动化测试与稳定的接口适配层。上游发生变化时，问题会直接扩散到 FastAPI、Web 和小程序。

本次只读线上审计已确认：

1. 两个旧 `/jwapp/...` 底层接口已经返回 404。
2. 课程类别接口已由 `component/queryDmb` 迁移到 `component/queryKclb`。
3. 当前项目对“当前学期”的定义在夏季学期会选错：行政学期接口返回第二学期，按日期接口返回夏季学期及当前周次。
4. 旧课表接口虽然仍可访问，但返回字段已不足以满足项目现有解析器；新版课表查询接口提供了完整字段。
5. 选课冲突返回码的解释与项目代码相反，属于高风险写操作缺陷。
6. 选课公告在无公告时可能返回 HTTP 200 空响应体，现有 `.json()` 会直接异常。
7. 通知公告已有分页接口；当前非分页接口一次返回近四千条记录，不适合产品直接使用。
8. 校历接口要求 `RoleCode` 请求头，通用客户端目前不支持按端点注入角色上下文。
9. 项目没有正式测试套件、CI、锁定的 Python 依赖，也存在明文持久化上游 Cookie 等安全问题。

因此不建议继续在三个现有 `*_service.py` 中逐个打补丁。推荐建立一个集中式 BYYT 客户端和稳定领域模型，再迁移各业务模块。

## 3. 审计方法与数据边界

本次审计使用用户明确授权的登录态，只执行：

- 页面与菜单读取
- 静态 JavaScript 资源分析
- 查询类 GET/POST 请求
- 响应状态、顶层结构、字段集合和数组长度探测

明确未执行：

- 选课
- 退课
- 添加或删除购物车课程
- 提交购物车
- 确认学业警示
- 修改志愿或积分
- 上传、保存、撤回、提交等业务写操作

登录态、Cookie、个人信息、成绩值和课程内容均未写入仓库；临时审计数据只保存在系统临时目录。

## 4. 当前项目基线

### 4.1 技术栈

- 后端：FastAPI + Pydantic + httpx，同步上游客户端通过 `asyncio.to_thread` 调用。
- Web：React 18 + React Router 6 + Ant Design 5 + Vite 5。
- 小程序：原生微信小程序 TypeScript。
- 部署：Docker Compose，Nginx 前端反代 FastAPI。
- 会话：内存 Session + 本地 JSON Cookie/Session 映射。

### 4.2 规模与耦合

- FastAPI 对外路由约 49 个。
- 后端直接调用约 31 个 BYYT 上游接口。
- 上游 URL、请求参数、响应字段散落于：
  - `backend/app/services/grades_service.py`
  - `backend/app/services/schedule_service.py`
  - `backend/app/services/course_service.py`
- 大文件与多职责文件明显：
  - `backend/app/services/course_service.py`：约 729 行
  - `backend/app/services/grades_service.py`：约 516 行
  - `frontend/src/pages/Courses.tsx`：约 708 行
  - `miniapp/miniprogram/pages/courses/courses.ts`：约 656 行
- Web API 数据存在大量 `any`；小程序业务代码中 `any` 使用更多，接口变更无法在编译期暴露。

### 4.3 质量基线

- 无正式 `pytest` 测试套件。
- 无 Web 单元测试或端到端测试。
- 无小程序自动化测试。
- 无 GitHub Actions 等 CI 工作流。
- Python 依赖无锁文件，且 `requirements.txt` 与 `pyproject.toml` 不完全一致。
- README 引用了不存在的 `.env.example`。
- 前端当前锁文件审计结果：10 个已知问题，其中 4 个 high、5 个 moderate、1 个 low。

## 5. 已确认的上游接口差异

### 5.1 接口差异矩阵

| 模块 | 当前项目行为 | 2026-07-10 线上结果 | 影响 | 升级动作 |
|---|---|---|---|---|
| BYYT 原始成绩 | `GET /jwapp/sys/wdcj/modules/wdcj/xscjcx.do` | 404 | `/api/byyt/grades` 已失效 | 删除旧实现，改为新版成绩适配器；不再直接暴露不稳定原始接口 |
| BYYT 原始档案 | `GET /jwapp/sys/emappagelog/config/index.do` | 404 | `/api/byyt/profile` 已失效 | 改用 `UserManager/queryxsxx` 与 `user/me` 的规范化模型 |
| 当前学期 | `component/querydangqianxnxq` | 返回 2025-2026-2 | 暑期默认学期错误 | 区分行政学期与按日期教学学期 |
| 日期所在学期 | 当前未使用 | `component/getXnxqByRq?rq=2026-07-10` 返回夏季学期 3、第 1 周 | 首页与课表应使用该语义 | 新增 `AcademicContext` 接口 |
| 成绩列表 | 主要使用 `cjgl/grcjcx/dyxwList` | 旧接口仍可用；当前个人成绩主页使用 JSON 接口 `cjgl/grcjcx/grcjcx` | 旧接口可作兼容来源，但缺少当前页面能力 | 新版优先使用 `grcjcx`，保留旧接口作为受控回退 |
| GPA | 后端自行按固定规则计算 | 官方接口 `cjgl/grcjcx/getgpa` 可用 | 项目结果可能与教务口径不同 | 同时提供“官方统计”和“本地估算”，明确口径 |
| 成绩学期列表 | 代码只接受数组 | `component/queryXnxq` 返回 `{code, content}` | `grades_service.get_term_list()` 实际返回空数组 | 统一响应解包 |
| 学业进度 | 用学号前四位推导年级 | U 前缀学号会得到 `U202`，正确年级应来自 `getXs.nj` | 排名、绩点、专业人数等字段不完整 | 所有内部 ID、年级、方案号均从 `getXs` 获取 |
| 总课表 | `xszykb/queryxszykbzong` + 旧解析器 | 接口仍可用，但结果不含 `KEY` | 所有课程可能被解析成 weekday/period=0 | 迁移到 `Xskbcx/queryXskbcxList` |
| 周课表 | `xszykb/queryxszykbzhou` + 旧解析器 | 结果缺少现有模型声明的多个字段 | 起止节次、任务号、周位图不可靠 | 使用新版详细课表模型，旧接口仅用于首页快速周视图回退 |
| 详细课表 | 当前未使用 | `Xskbcx/queryXskbcxList` 返回完整小写字段和 `key` | 可解决旧解析缺失 | 建立新版 Schedule Adapter |
| 考试 | `component/queryKsxxByXs` | 仍可用，返回考试摘要 | 基本功能可继续 | 增加 `kscxtj/queryXsksByxhList` 作为分页详细查询 |
| 课程类别 | `component/queryDmb` | HTTP 200 空响应体 | `/courses/categories` 会返回空或异常 | 改为 `component/queryKclb?pylb=1`，解包 `content` |
| 选课方式 | Web/小程序硬编码 | 当前由 `queryYxkc.xkgzszList` 动态返回 | 上游增删选课方式时客户端失效 | 后端暴露动态 methods/capabilities |
| 可选课程 | 直接重复请求 `queryKxrw` | 上游会返回“查询请求频率过高” | 快速切换筛选会失败 | 单飞请求、客户端防抖、按会话短缓存、明确限流错误 |
| 冲突检查 | `jg == "1"` 解释为冲突 | 当前脚本：`-9`=有冲突，`-1`=禁止，`1`=无冲突 | 现有结果反转，可能误导选课写操作 | 重做状态枚举与测试，写操作前强制 preflight |
| 选课公告 | 总是假定 JSON | 无公告时可能 HTTP 200 空响应体 | `.json()` 抛错，页面加载失败 | 空响应归一化为 `null` 或 `[]` |
| 通知公告 | 当前未实现 | 非分页接口返回约 3977 条；分页接口可用 | 直接全量拉取性能差 | 使用 `component/queryTongZhiGongGaoPage` |
| 校历 | 当前未实现 | `Xiaoli/queryMonthList` 可用，但要求 `RoleCode` | 通用请求器无法调用 | BYYT Client 支持端点级角色请求头 |
| 学业警示 | 当前未实现 | 查询接口可用 | 可新增只读提醒 | 第一批新功能候选 |
| 个人执行计划 | 菜单存在 | 菜单 URL 当前返回 404 | 菜单数据可能滞后 | 暂缓实现，等待上游恢复或确认新 URL |

### 5.2 当前可动态发现的选课方式

当前账号线上返回：

- `bx-b-b`：必修
- `sztzk-b-b`：素质拓展选课
- `zytzk-b-b`：专业拓展选课

该列表属于动态配置，不应继续在 Web 和小程序中写死。不同年级、培养类型和选课阶段可能返回不同集合。

## 6. 当前代码中的高优先级问题

### 6.1 P0：正确性与写操作安全

1. **冲突状态解释反转**

   `backend/app/services/course_service.py:599` 将 `jg == "1"` 当作有冲突，而当前上游脚本定义 `1` 为无冲突、`-9` 为冲突提示。

2. **旧 BYYT 原始接口已 404**

   `backend/app/services/byyt_proxy.py:28`、`:32` 已不可用。

3. **总课表解析器与当前响应字段不匹配**

   `backend/app/services/schedule_service.py:182` 依赖 `KEY/KSJC/JSJC/RWH`，旧总课表响应不再提供完整字段。

4. **夏季学期默认上下文错误**

   `backend/app/services/schedule_service.py:19` 只使用行政当前学期，未使用按日期教学学期。

### 6.2 P1：接口兼容与数据完整性

1. `backend/app/services/course_service.py:677` 使用已空响应的 `component/queryDmb`。
2. `backend/app/services/course_service.py:624` 未处理选课公告空响应体。
3. `backend/app/services/grades_service.py:296` 未解包 `component/queryXnxq.content`。
4. `backend/app/services/grades_service.py:273` 从 U 前缀学号截取错误年级。
5. 上游会对重复 `queryKxrw` 请求限流，项目没有稳定错误映射、单飞或防抖约束。
6. 认证失效被映射为 502，而不是可识别的 401/会话错误码。

### 6.3 P1：安全与会话

1. `backend/app/services/cookie_store.py` 将上游 Cookie 明文写入 `cookies.json`。
2. Session 映射与 Cookie 文件不是原子写入，异常被静默吞掉。
3. `SESSION_TTL`/`SESSION_MAX_AGE` 与 `SessionStore()` 实际默认值没有统一接入。
4. `cleanup_loop()` 弹出会话后再次从字典读取，导致目标客户端无法被关闭。
5. 全局异常处理器将原始异常字符串直接返回给客户端，可能泄露上游细节。
6. 选课、退课、购物车提交等 Cookie 鉴权写接口缺少明确的 CSRF/Origin 防护和幂等机制。
7. 浏览器和小程序目前共用“手工 Cookie”思路，传输方式没有抽象。

### 6.4 P2：工程质量与维护性

1. 没有契约测试，无法快速判断“路径变了、参数变了、还是响应字段变了”。
2. Router、上游请求、解析、统计和业务编排混在同一文件。
3. Web 与小程序重复定义 API 路径、字段和选课方式。
4. 大量 `any` 使接口变化无法在编译阶段暴露。
5. Python 与 Node 依赖未采用可复现锁定策略。
6. 无 CI、代码格式、静态检查和依赖安全门禁。

## 7. 升级范围

### 7.1 本轮必须完成

- 新版 BYYT 适配层。
- 会话、Cookie 存储与错误模型加固。
- 成绩、GPA、学业进度。
- 行政学期、教学学期、校历和周次上下文。
- 课表与考试。
- 选课查询、已选、购物车、规则、日志与安全写操作。
- 通知公告与个人信息。
- Web 全量迁移。
- 小程序全量迁移。
- 自动化测试、CI、依赖锁定与部署文档。

### 7.2 本轮明确暂缓

- 校园网功能重构。
- 第三方外部系统深度集成：毕设、评教、北科学堂、实践教学平台等。
- 交流生报名、转专业申请等完整写流程。
- 上游当前返回 404 的个人执行计划页面。
- 未经测试账号验证的缴费和申请类写操作。

### 7.3 校园网保护边界

校园网模块本轮只要求：

- 现有路由不因公共认证重构而失效。
- Web 与小程序仍可进入校园网页面。
- 添加最小冒烟测试。
- 不主动重写 `wifi_service.py`、页面结构或业务能力。

## 8. 目标后端架构

### 8.1 原则

- 所有上游请求必须经过一个 BYYT Client。
- API Router 不直接使用 `httpx`，不解析上游原始字段。
- 上游模型与产品领域模型分离。
- 不建立过度复杂的通用框架；按模块拆分清晰函数即可。
- 默认不向客户端暴露 `raw` 上游数据。

### 8.2 推荐目录

```text
backend/app/
├── api/
│   ├── auth.py
│   ├── me.py
│   ├── academic.py
│   ├── grades.py
│   ├── schedule.py
│   ├── exams.py
│   ├── course_selection.py
│   └── notices.py
├── byyt/
│   ├── client.py
│   ├── errors.py
│   ├── profile.py
│   ├── academic.py
│   ├── grades.py
│   ├── schedule.py
│   ├── exams.py
│   ├── courses.py
│   └── notices.py
├── models/
│   ├── common.py
│   ├── academic.py
│   ├── grades.py
│   ├── schedule.py
│   ├── courses.py
│   └── notices.py
├── services/
│   ├── auth_service.py
│   ├── academic_service.py
│   └── course_selection_service.py
└── storage/
    └── session_store.py
```

### 8.3 BYYT Client 职责

`BYYTClient` 统一处理：

- form、JSON、空 body 三种请求格式。
- `RoleCode` 等端点级请求头。
- 302/登录 HTML/401 的会话失效判断。
- HTTP 200 空响应体。
- `{code, content}`、直接数组、PageInfo、`jg/message` 等响应包装。
- 上游限流与可重试错误分类。
- 单次请求超时、请求 ID、脱敏日志。
- 仅对幂等查询执行受控重试。
- 同一会话、同一查询的 single-flight 合并。

### 8.4 适配器职责

每个模块适配器只负责：

1. 构造当前上游参数。
2. 调用 `BYYTClient`。
3. 将原始字段转换为稳定的 Pydantic 模型。
4. 对上游缺失字段使用明确的 `None`，而不是伪造空字符串。

## 9. 会话与安全目标

### 9.1 存储

单机 Docker 部署阶段推荐使用 SQLite 代替多个 JSON 文件：

- Session 元数据事务化存储。
- 上游 Cookie 使用 `cryptography` 加密后保存。
- 加密密钥通过 `SESSION_ENCRYPTION_KEY` 注入，不写入镜像或仓库。
- Session Token 只保存哈希。
- 文件权限限制为服务用户可读写。
- 明确 idle TTL 与 absolute TTL。

暂不为了未来多实例引入 Redis；真正需要横向扩容时再替换存储实现。

### 9.2 Web 与小程序认证传输

- Web：继续使用 `HttpOnly + Secure + SameSite=Lax` Cookie。
- 小程序：使用 `Authorization: Bearer <opaque-token>`，不再手工拼接浏览器 Cookie。
- 两种传输映射到同一个后端 Session 模型。
- 登录成功后轮换 Session ID。
- 浏览器响应不返回可被 JavaScript 读取的 Session Token。

### 9.3 写操作保护

- 校验 Origin/Referer 或 CSRF Token。
- 所有选课写操作先调用 preflight。
- 支持 `Idempotency-Key`，避免重复点击产生重复提交。
- 写操作不自动重试。
- 记录不含个人敏感内容的审计事件：操作类型、结果、请求 ID、时间。
- 上游返回语义必须用枚举建模，不再用散落的字符串判断。

### 9.4 错误响应

统一错误格式：

```json
{
  "error": {
    "code": "UPSTREAM_RATE_LIMITED",
    "message": "教务系统请求过于频繁，请稍后重试",
    "retryable": true,
    "request_id": "..."
  }
}
```

核心错误码至少包括：

- `AUTH_REQUIRED`
- `UPSTREAM_SESSION_EXPIRED`
- `UPSTREAM_RATE_LIMITED`
- `UPSTREAM_BAD_RESPONSE`
- `UPSTREAM_UNAVAILABLE`
- `COURSE_CONFLICT`
- `COURSE_OPERATION_BLOCKED`
- `VALIDATION_ERROR`

## 10. 新 API 草案

允许破坏升级，但考虑微信小程序发布存在审核和用户升级延迟，实施期仍需短期保留旧路由适配器。旧路由只作为迁移垫片，不作为长期兼容承诺。

### 10.1 个人与学期上下文

```text
GET  /api/me
GET  /api/academic/context?date=YYYY-MM-DD
GET  /api/academic/terms
GET  /api/academic/calendar?term=2025-2026-3
```

`AcademicContext` 同时返回：

- `administrative_term`
- `teaching_term`
- `week`
- `date`
- `is_in_teaching_week`

### 10.2 成绩与学业

```text
GET /api/grades?term=&page=&page_size=
GET /api/grades/summary
GET /api/academic/progress
GET /api/academic/progress/modules
GET /api/academic/progress/courses
GET /api/academic/warnings
```

成绩摘要区分：

- `official_gpa`：教务系统官方返回。
- `estimated_gpa`：项目按公开规则计算的估算值。
- `earned_credits`
- `passed_courses`
- `failed_courses`

### 10.3 课表与考试

```text
GET /api/schedule?term=&week=
GET /api/schedule/terms
GET /api/exams?term=&page=&page_size=
```

统一课程时段模型：

```json
{
  "course_id": "...",
  "course_code": "...",
  "course_name": "...",
  "teacher": "...",
  "weekday": 1,
  "start_period": 1,
  "end_period": 2,
  "weeks": [1, 2],
  "location": "...",
  "campus": "..."
}
```

### 10.4 通知公告

```text
GET  /api/notices?page=&page_size=&unread_only=
GET  /api/notices/{id}
POST /api/notices/{id}/read
```

第一阶段可以只实现查询；已读写入应在完成接口验证后启用。

### 10.5 选课

```text
GET    /api/course-selection/context
GET    /api/course-selection/courses
GET    /api/course-selection/selected
GET    /api/course-selection/cart
GET    /api/course-selection/logs
POST   /api/course-selection/preflight
POST   /api/course-selection/selections
DELETE /api/course-selection/selections/{id}
POST   /api/course-selection/cart/items
DELETE /api/course-selection/cart/items/{id}
POST   /api/course-selection/cart/submit
```

`context` 返回动态信息：

- 当前选课学期
- 当前可用选课方式
- 选课模式（先到先得、抽签等）
- 选课/退课时间窗
- 是否允许忽略冲突或零容量
- 课程类别、学院、校区
- 上游能力标志

客户端不得再写死选课方式和规则。

## 11. 三端类型与数据契约

### 11.1 OpenAPI 为唯一契约来源

- 后端 Pydantic 模型生成 OpenAPI。
- Web 和小程序由 OpenAPI 生成 TypeScript 类型。
- 禁止三端分别手写同名响应结构。
- CI 检查生成文件是否与 OpenAPI 同步。

### 11.2 类型目标

- Web API 层不允许 `any`。
- 小程序 API、缓存和页面数据模型不允许业务响应使用 `any`。
- 微信事件对象可在确实缺少类型时局部使用窄化类型，不要求为了清零 `any` 制造复杂声明。
- 日期、学期、课程 ID、任务 ID 分别使用明确字段，不混用字符串。

## 12. 第一批产品功能矩阵

| 功能 | 当前状态 | 升级目标 | 优先级 |
|---|---|---|---|
| 登录与会话恢复 | 已有，稳定性一般 | 加密持久化、统一错误、Web/小程序双传输 | P0 |
| 个人信息 | 已有原始结构展示 | 规范化学生档案与权限信息 | P0 |
| 当前教学周 | 暑期语义错误 | 日期感知学期与周次 | P0 |
| 成绩列表 | 已有 | 新接口、官方 GPA、筛选与分页 | P0 |
| 学业进度 | 已有但参数与统计不完整 | 模块、学分类别、未完成课程与毕业要求 | P0 |
| 课表 | 已有但总课表解析不可靠 | 新详细接口、夏季学期、周/学期视图 | P0 |
| 考试 | 已有摘要 | 详细分页、筛选与倒计时 | P1 |
| 动态选课方式 | 硬编码 | 后端动态下发 | P0 |
| 选课查询 | 已有 | 限流保护、规则与容量信息 | P0 |
| 选课写操作 | 已有但冲突语义错误 | preflight、幂等、明确状态枚举 | P0 |
| 通知公告 | 无 | 分页列表、详情、附件与已读状态 | P1 |
| 校历 | 无 | 学期校历和教学周展示 | P1 |
| 学业警示 | 无 | 只读提醒和状态展示 | P1 |
| 交流成绩 | 无 | 作为第二批只读候选 | P2 |
| 转专业申请 | 无 | 仅展示入口/状态，写流程另行评审 | P2 |
| 外部教学平台 | 仅官方菜单入口 | 暂只提供安全跳转 | P2 |

## 13. Web 升级方向

### 13.1 工程升级

当前 registry 候选版本（2026-07-10）：

- React 19.2
- React Router 7.18
- Ant Design 6.5
- Vite 8.1
- TypeScript 7.0
- Axios 1.18

不建议在同一个提交中同时完成“后端契约重写 + 全部前端框架大版本升级”。推荐两步：

1. 先在现有 React 架构上完成新 API 迁移和安全修复。
2. 页面行为稳定后再升级 React/Router/AntD/Vite/TypeScript。

### 13.2 数据层

- 建立统一 API Client。
- 引入请求去重、缓存和明确的 retry 策略。
- 401 由认证状态机处理，不直接使用 `window.location.href` 作为唯一机制。
- 上游限流错误显示可恢复提示，不自动快速重试。
- 页面支持 partial error，仪表盘某一模块失败不应导致整页空白。

### 13.3 页面拆分

优先拆分：

- `Courses.tsx`
- `Schedule.tsx`
- `Dashboard.tsx`
- `Wifi.tsx` 暂不重构，仅避免继续增长

拆分单位按页面真实区块，不创建无复用价值的抽象组件。

## 14. 小程序升级方向

- 升级 `miniprogram-api-typings`（当前 2.8，registry 当前 5.2）。
- 使用 Bearer Token，不再在业务请求层手工拼接 `ustb_sid` Cookie。
- API 类型从 OpenAPI 生成。
- 将页面缓存版本与 API schema version 绑定，升级后自动清理旧缓存。
- 选课方式、学期、学院、校区等均从后端动态获取。
- 页面只保留展示状态，网络和错误处理集中到 service 层。
- 对登录轮询、页面重复加载和过期响应继续保留竞态保护，但改为可测试状态机。

## 15. 测试策略

### 15.1 后端测试工具

候选工具：

- pytest 9
- pytest-asyncio
- respx 0.23
- FastAPI TestClient/httpx ASGITransport
- Ruff 0.15

### 15.2 测试层级

1. **解析器单元测试**

   使用脱敏固定响应验证上游字段到领域模型的转换。

2. **BYYT Client 测试**

   覆盖空 body、HTML 登录页、302、401、`{code, content}`、PageInfo、`jg/message`、限流。

3. **服务测试**

   验证学期上下文、官方/估算 GPA、学业进度组合、选课 preflight。

4. **API 契约测试**

   验证 OpenAPI 响应模型和统一错误格式。

5. **Web 测试**

   页面关键状态、筛选、空数据、会话过期、限流提示。

6. **小程序测试**

   service 层、认证状态机、缓存迁移和页面数据转换。

7. **可选线上只读契约测试**

   仅在人工提供临时登录态时执行，严格白名单查询接口，CI 默认不运行。

### 15.3 必须固化的回归案例

- 2026-07-10 应识别为夏季学期第 1 周，而不是第二学期。
- `component/queryDmb` 空响应应切换到 `component/queryKclb`。
- 选课公告空 body 应返回空结果，不应 500。
- `jg=-9` 必须映射为课程冲突；`jg=1` 必须映射为无冲突。
- `queryKxrw` 限流应映射为 `UPSTREAM_RATE_LIMITED`。
- 总课表必须使用有效 `key/weekday/start_period/end_period`。
- U 前缀学号不得通过字符串截取推导年级。
- Session 失效必须返回 401 和稳定错误码。
- Cookie 文件不得以明文保存。

## 16. CI 与质量门禁

每个 Pull Request 至少执行：

```text
Backend
- ruff check
- ruff format --check
- pytest
- OpenAPI schema generation/diff

Frontend
- npm ci
- typecheck
- unit tests
- production build
- npm audit: 禁止 high/critical

Miniapp
- npm ci
- TypeScript typecheck
- service tests
- generated API type sync check

Repository
- Docker image build
- secret scan
- dependency lock consistency
```

## 17. 性能与可靠性目标

### 17.1 上游请求

- 按会话限制并发，避免同一登录态同时冲击 BYYT。
- `queryKxrw` 等敏感查询启用 single-flight 和短时缓存。
- 参考数据按培养类型/角色/学期设置缓存键，禁止全局错误串用。
- 空响应、部分字段缺失和临时限流都应可预测处理。
- 不对选课写操作自动重试。

### 17.2 客户端

- 仪表盘使用一个聚合接口或统一查询编排，减少重复请求。
- 通知使用分页接口，不再加载全部历史通知。
- Web 与小程序筛选输入防抖。
- 页面缓存必须带更新时间、用户和 schema version。

### 17.3 可观测性

- 每个请求生成 request ID。
- 日志记录端点、耗时、状态分类和重试次数。
- 不记录 Cookie、Session Token、手机号、完整学号、姓名、成绩值。
- 健康检查拆分：
  - liveness：进程存活
  - readiness：存储可用、基础配置有效
- 上游 BYYT 不作为容器存活的硬依赖，避免学校系统故障导致服务反复重启。

## 18. 依赖升级策略

### 18.1 后端

候选目标版本：

- FastAPI 0.139
- Pydantic 2.13
- httpx 0.28
- Uvicorn 0.51

策略：

- 第一阶段保留 Python 3.12，避免同时升级 Python 大版本与业务架构。
- 引入 `uv.lock` 并提交仓库。
- 删除重复的 `requirements.txt`，或由 `pyproject.toml` 自动生成，避免双源漂移。
- 审核 `USTB-SSO` 的当前版本和登录回调兼容性后再锁定。

### 18.2 Web

- 先立即升级存在 high 风险的 Axios/Vite/Router 依赖。
- 后续单独提交 React 19、Router 7、AntD 6、Vite 8、TypeScript 7 迁移。
- 每次大版本升级必须有独立构建与页面回归结果。

### 18.3 小程序

- 增加 lockfile。
- 升级 typings。
- 评估并清理项目内手工补充、已被官方 typings 覆盖的声明。

## 19. 分阶段实施计划

### Phase 0：冻结契约与建立测试基线

目标：在改代码前把当前上游行为固化为脱敏 fixture。

任务：

- 建立 pytest/respx。
- 保存核心查询接口的脱敏响应 fixture。
- 为已确认的回归案例先写失败测试。
- 生成当前 OpenAPI 快照。
- 添加 CI 最小流水线。

验收：

- 测试能够复现旧 BYYT 接口 404、类别空响应、公告空 body、冲突码反转、夏季学期错误。

### Phase 1：BYYT Client、错误模型与安全会话

目标：所有上游请求进入统一边界。

任务：

- 新建 `BYYTClient`。
- 集中处理 Session 失效、空响应、角色头、限流和响应解包。
- SQLite + 加密 Cookie 存储。
- 统一错误响应。
- 修复 Session 清理和 TTL。

验收：

- Router/Service 不再直接调用上游 URL。
- Cookie 不以明文落盘。
- Session 失效稳定返回 401。
- 上游错误不向客户端泄露内部异常。

### Phase 2：只读核心教务 API

目标：先稳定所有查询能力。

任务：

- `/api/me`
- `AcademicContext`
- 成绩列表、官方 GPA、学期列表
- 学业进度
- 新版课表
- 考试摘要与详细列表
- 通知公告
- 校历
- 学业警示

验收：

- 所有接口具有 Pydantic 模型和 fixture 测试。
- 夏季学期与普通学期均能正确选择。
- 不再暴露 `/api/byyt/*` 旧原始接口。

### Phase 3：选课只读能力与动态规则

目标：先准确展示，不执行写操作。

任务：

- 动态选课方式。
- 选课上下文与规则。
- 可选课程、已选课程、购物车、日志。
- 学院、校区、课程类别新接口。
- 限流与 single-flight。

验收：

- Web/小程序不再硬编码选课方式。
- 快速切换筛选不会产生并发重复请求。
- 上游限流得到明确可恢复提示。

### Phase 4：选课写操作

目标：在模拟测试完善后恢复安全写能力。

任务：

- preflight 状态机。
- 选课、退课、购物车增删与提交。
- CSRF/Origin 校验。
- 幂等键。
- 写操作审计事件。

验收：

- `-9/-1/1` 等返回码均有 fixture 和测试。
- 自动测试不访问真实写接口。
- 线上启用前进行一次人工受控验收。

### Phase 5：React Web 迁移

目标：Web 完全使用新契约。

任务：

- 生成 API 类型。
- 迁移认证状态机。
- 按功能矩阵改造页面。
- 拆分大型页面。
- 修复依赖安全问题。
- 完成框架大版本升级。

验收：

- production build 通过。
- API 层无 `any`。
- 关键页面具有空态、错误态和 Session 过期测试。
- npm audit 无 high/critical。

### Phase 6：微信小程序迁移

目标：小程序完全使用新契约和 Token 传输。

任务：

- 生成 API 类型。
- Bearer Token 认证。
- 缓存 schema version 迁移。
- 迁移全部教务页面。
- 升级 typings。

验收：

- 不再手工拼接 `ustb_sid` Cookie。
- API 响应不使用业务 `any`。
- 旧缓存不会污染新版页面。

### Phase 7：迁移收尾与部署

目标：删除临时兼容层并形成可回滚发布。

任务：

- Web 已切换后观察稳定性。
- 小程序新版本达到可接受覆盖率后移除旧 API。
- 更新 README、环境变量样例和部署文档。
- 镜像使用不可变版本标签。
- 保留上一个稳定镜像用于回滚。

验收：

- 旧路由无调用后删除。
- Docker Compose 可从空环境启动。
- 文档中的所有文件和命令真实存在。

## 20. 发布与兼容策略

虽然允许破坏升级，但微信小程序无法保证与后端同步即时发布，因此采用：

1. 后端先上线新契约，同时保留短期旧路由适配。
2. Web 切换新契约并观察。
3. 小程序提交、审核并发布。
4. 监控旧路由调用量。
5. 旧客户端降至可接受比例后删除兼容层。

兼容层只做字段桥接，不继续修补旧架构，也不支持新增功能。

## 21. 项目级完成标准

本轮升级完成需同时满足：

- 已确认的上游接口差异全部有测试覆盖。
- 成绩、课表、考试、学业进度、选课、通知、校历、个人信息在三端可用。
- 夏季学期默认上下文正确。
- 选课冲突状态无反转风险。
- 上游 Cookie 加密存储。
- Web 与小程序使用统一 OpenAPI 类型。
- 后端、Web、小程序均有 CI。
- 前端依赖无 high/critical 漏洞。
- 日志不含敏感身份与成绩数据。
- Docker 部署可复现、有明确版本和回滚路径。
- 校园网现有功能通过冒烟测试。

## 22. 推荐的首个编码批次

蓝图确认后，建议第一个代码批次只做以下内容：

1. 建立测试目录、脱敏 fixture 和 CI。
2. 新建 `BYYTClient`，暂不迁移全部业务。
3. 用测试先修复五个已确认问题：
   - 旧 `/jwapp` 接口 404
   - 课程类别新接口
   - 空选课公告
   - 冲突码语义
   - 夏季学期上下文
4. 提供新的只读 `AcademicContext`、成绩和课表 API。
5. 验证后再进入选课写操作。

该批次能快速建立安全边界，同时避免一次性重写三端造成不可验证的大改动。

## 23. 实施前仍需确认的产品决策

以下决策不阻塞 Phase 0/1，但应在对应模块开发前确认：

1. 成绩页是否同时显示官方 GPA 与项目估算 GPA，还是只显示官方值。
2. 成绩单导出是否首期接入 FineReport，还是先提供官方页面跳转。
3. 通知“已读”是否同步写回教务系统，还是仅在本项目本地记录。
4. 学业警示是否只展示，还是允许从本项目执行“确认核对”。
5. 交流生、转专业等流程首期只展示入口/状态，还是计划接入完整写流程。
6. Cookie 登录是否保留为高级功能，还是生产环境默认关闭。
