# BYYT 教务系统 API 文档

> 基础 URL: `https://byyt.ustb.edu.cn`
> 认证方式: Cookie-based Session (JSESSIONID)
> 请求方式: 默认 POST, Content-Type: `application/x-www-form-urlencoded`
> 数据加密: 部分接口参数需使用 `inco_encrypt()` 加密

## 公共参数

以下参数在多个接口中反复出现:

| 参数 | 类型 | 说明 |
|------|------|------|
| p_pylx | string | 培养类型, 默认 `"1"` (本科) |
| p_xn | string | 学年, 如 `"2025-2026"` |
| p_xq | string | 学期, 如 `"1"` (第一学期) / `"2"` (第二学期) |
| p_xnxq | string | 学年学期组合, 如 `"2025-20261"` |
| p_dqxn | string | 当前学年 |
| p_dqxq | string | 当前学期 |
| p_dqxnxq | string | 当前学年学期组合 |
| xn | string | 学年 (非 queryform 场景) |
| xq | string | 学期 (非 queryform 场景) |
| pylx | string | 培养类型 |
| xjid | string | 学籍ID (通常等于学号) |
| xh | string | 学号 |
| fah | string | 培养方案号 |
| pageNum | int | 分页页码, 从 1 开始 |
| pageSize | int | 每页数量 |

## 公共响应结构

大部分接口返回以下结构之一:

```json
// 结构1: 带 code 的标准响应
{"code": 200, "content": ...}

// 结构2: 直接返回数据 (数组或对象)
[...] 或 {...}

// 结构3: 操作结果
{"jg": "1", "message": "操作成功"}
```

---

## 1. 选课模块 (Xsxk)

### 1.1 查询当前选课学年学期
- **URL**: `Xsxk/queryXkdqXnxq`
- **方法**: POST
- **已实现**: ✅ `course_service.get_course_term_info()`
- **说明**: 选课模块入口, 页面初始化时调用, 获取选课系统当前学年学期信息(含选课开放时间等)
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| cxsfmt | string | 是 | 查询是否满退, 固定 `"0"` |
| p_pylx | string | 是 | 培养类型, 默认 `"1"` |
| mxpylx | string | 是 | 明细培养类型, 默认 `"1"` |
| p_sfgldjr | string | 是 | 是否关联登记人, 固定 `"0"` |
| p_sfredis | string | 是 | 是否使用 Redis, 固定 `"0"` |
| p_sfsyxkgwc | string | 是 | 是否使用选课购物车, 固定 `"0"` |
| p_xktjz | string | 否 | 选课途径值 |
| p_xn | string | 否 | 学年 |
| p_xq | string | 否 | 学期 |
| p_xnxq | string | 否 | 学年学期 |
| p_dqxn | string | 否 | 当前学年 |
| p_dqxq | string | 否 | 当前学期 |
| p_dqxnxq | string | 否 | 当前学年学期 |

- **响应**: 返回选课系统当前学年学期信息, 含选课开放时间段等配置

### 1.2 查询可选课程任务列表
- **URL**: `Xsxk/queryKxrw`
- **方法**: POST
- **已实现**: ✅ `course_service.get_available_courses()`
- **说明**: 获取可选课程任务列表, 支持分页和多种筛选条件
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 包含查询条件的表单 |
| p_xkfsdm | string | 是 | 选课方式代码, 如 `"bx-b-b"` |
| p_gjz | string | 否 | 搜索关键字 |
| p_xiaoqu | string | 否 | 校区筛选 |
| p_kkyx | string | 否 | 开课学院筛选 |
| p_kclb | string | 否 | 课程类别筛选 |
| p_kc_gjz | string | 否 | 课程关键字 |
| pageNum | int | 否 | 页码 |
| pageSize | int | 否 | 每页数量 |

- **响应**:
```json
{
  "kxrwList": {
    "list": [
      {
        "rwh": "任务号",
        "id": "ID",
        "kcdm": "课程代码",
        "kcmc": "课程名称",
        "xf": "学分",
        "zxs": "总学时",
        "rwlxmc": "选课方式",
        "kkyxmc": "开课学院",
        "zrl": "容量",
        "yxzrs": "已选人数",
        "dgjsmc": "教师",
        "sksj": "上课时间",
        "skdd": "上课地点",
        "xkzt": "未选/已选",
        "kxh": "课序号"
      }
    ],
    "total": "总数"
  }
}
```

### 1.3 按课程代码查询可选课程任务
- **URL**: `Xsxk/queryKxrwByKcdm_js`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 按课程代码精确查询可选课程任务
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 包含课程代码 (kcdm) 的查询表单 |

- **响应**: 返回匹配课程代码的课程任务列表

### 1.4 查询已选课程列表
- **URL**: `Xsxk/queryYxkc`
- **方法**: POST
- **已实现**: ✅ `course_service.get_selected_courses()`
- **说明**: 获取当前已选课程列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 包含查询条件的表单 |
| cxsfmt | string | 是 | 固定 `"1"` |
| p_xkfsdm | string | 是 | 选课方式代码, 如 `"yixuan"` |

- **响应**:
```json
{
  "yxkcList": [
    {
      "rwh": "任务号",
      "kcdm": "课程代码",
      "kcmc": "课程名称",
      "kcmc_en": "英文名",
      "kcxzmc": "课程性质",
      "kclbmc": "课程类别",
      "xf": "学分",
      "xs": "学时",
      "xkfsmc": "选课方式",
      "kkyxmc": "学院",
      "xiaoqumc": "校区",
      "zrl": "容量",
      "yxzrs": "已选人数",
      "dgjsmc": "教师",
      "sksj": "上课时间",
      "skdd": "上课地点",
      "pkjgmx": "排课结果HTML",
      "xksj": "选课时间",
      "xkbj": "选课标记",
      "cqzt": "抽签状态"
    }
  ]
}
```

### 1.5 查询选课购物车
- **URL**: `Xsxk/queryXkgwc`
- **方法**: POST
- **已实现**: ✅ `course_service.get_cart()`
- **说明**: 查询选课购物车内的课程
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 包含查询条件的表单 |
| p_xkfsdm | string | 是 | 选课方式代码 |

- **响应**:
```json
{
  "gwcList": ["... 课程对象, 结构同 yxkcList"]
}
```

### 1.6 添加到购物车 / 直接选课
- **URL**: `Xsxk/addGouwuche`
- **方法**: POST
- **已实现**: ✅ `course_service.select_course()` / `course_service.add_to_cart()`
- **说明**: 通过 `p_xktjz` 参数区分操作类型: `rwtjzyx` = 直接选课, `rwtjzgwc` = 加入购物车
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 包含课程信息的表单 |
| p_id | string | 是 | 课程任务 ID |
| p_xktjz | string | 是 | `"rwtjzyx"` (直接选课) 或 `"rwtjzgwc"` (加入购物车) |

- **响应**:
```json
{"jg": "1", "message": "操作成功"}
```
> `jg` 为 `"1"` 表示成功, `"0"` 表示失败

### 1.7 提交购物车选课
- **URL**: `Xsxk/addXuanke`
- **方法**: POST
- **已实现**: ✅ `course_service.submit_cart()`
- **说明**: 将购物车中的课程确认选课
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 包含购物车课程信息的表单 |
| p_xktjz | string | 是 | 固定 `"gwctjzyx"` (购物车提交至已选) |

- **响应**:
```json
{"jg": "1", "message": "操作成功"}
```

### 1.8 退课
- **URL**: `Xsxk/tuike`
- **方法**: POST
- **已实现**: ✅ `course_service.drop_course()`
- **说明**: 从已选课程中退选
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 包含课程信息的表单 |
| p_id | string | 是 | 已选课程记录 ID |

- **响应**:
```json
{"jg": "1", "message": "操作成功"}
```

### 1.9 删除购物车课程
- **URL**: `Xsxk/delGouwuche`
- **方法**: POST
- **已实现**: ✅ `course_service.remove_from_cart()`
- **说明**: 从购物车移除课程, 支持批量
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 包含课程信息的表单 |
| p_ids[] | string[] | 是 | 购物车项目 ID 数组 |

- **响应**:
```json
{"jg": "1", "message": "操作成功"}
```

### 1.10 检测选课时间冲突
- **URL**: `Xsxk/cxmtctPd`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 在加入购物车前调用, 检测是否存在时间冲突
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 包含课程时间信息的表单 |

- **响应**: 返回是否存在时间冲突的判断结果

### 1.11 修改已选课程选课系数
- **URL**: `Xsxk/updXkxsByyx`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 修改已选课程的选课系数/学分值
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| p_id | string | 是 | 已选课程记录 ID |
| p_xkxs | string | 是 | 选课系数/学分值 |

- **响应**: 修改成功后刷新已选课程列表

### 1.12 修改购物车课程选课系数
- **URL**: `Xsxk/updXkxsBygwc`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 修改购物车中课程的选课系数
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| p_id | string | 是 | 购物车课程记录 ID |
| p_xkxs | string | 是 | 选课系数/学分值 |

- **响应**: 确认后修改系数并刷新列表

### 1.13 查询选课操作日志
- **URL**: `Xsxk/queryXsxkrzList`
- **方法**: POST
- **已实现**: ✅ `course_service.get_selection_log()`
- **说明**: 查询选课/退课操作记录
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform / rzform | object | 是 | 日志查询表单, 包含查询时间范围等 |

- **响应**: 返回选课操作日志列表

### 1.14 查询学生选课详情
- **URL**: `Xsxk/queryXkxsDet`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询学生年级等选课详细信息
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 包含学生信息的查询表单 |

- **响应**: 返回学生年级等详细信息

### 1.15 查询选课公告
- **URL**: `Xsxk/queryXkggZx`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询选课公告信息, 页面初始化时调用
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xn | string | 是 | 学年 |
| xq | string | 是 | 学期 |

- **响应**: 返回选课公告内容

### 1.16 查询课程缴费信息
- **URL**: `Xsxk/queryJiaofei`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询课程缴费信息
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 课程任务 ID, 多个用逗号分隔 |

- **响应**: 返回缴费任务列表和总金额信息

### 1.17 学费缴费处理
- **URL**: `Xsxk/updXuefeijiaofei`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 学费缴费处理
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 包含缴费信息的表单 |

- **响应**: 缴费成功后刷新列表

---

## 2. 选课辅助模块 (Xsxktz / xkgzsz)

### 2.1 查询节次列表
- **URL**: `Xsxktz/queryXlcxList`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询上课时间段(节次)列表, 学年学期变更时触发
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 包含学年学期的查询表单 |

- **响应**: 返回节次列表数据

### 2.2 下载选课公告附件
- **URL**: `xkgzsz/downggfj`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 下载选课公告附件文件
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| savename | string | 是 | 服务器端保存的文件名 |
| filename | string | 是 | 下载后显示的文件名 |

- **响应**: 触发文件下载

---

## 3. 课表模块 (xszykb / Xskbcx)

### 3.1 查询学生总课表
- **URL**: `xszykb/queryxszykbzong`
- **方法**: POST
- **已实现**: ✅ `schedule_service.get_full_schedule()`
- **说明**: 获取整学期全部课程的课表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xn | string | 是 | 学年, 如 `"2025-2026"` |
| xq | string | 是 | 学期, 如 `"1"` |

- **响应**:
```json
[
  {
    "KEY": "xq1_jc1",
    "SKSJ": "课程名\n教师\n周次\n地点\n节次",
    "SKSJ_EN": "...",
    "KSJC": 1,
    "JSJC": 2,
    "RWH": "任务号",
    "ZC": "周次位图",
    "PYLX": "培养类型"
  }
]
```

### 3.2 查询学生周课表
- **URL**: `xszykb/queryxszykbzhou`
- **方法**: POST
- **已实现**: ✅ `schedule_service.get_week_schedule()`
- **说明**: 获取指定周的课程安排
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xn | string | 是 | 学年 |
| xq | string | 是 | 学期 |
| zc | string | 是 | 周次 (数字字符串) |

- **响应**: 结构同 `queryxszykbzong`

### 3.3 查询学生个人课表 (课表查询模块)
- **URL**: `Xskbcx/queryXskbcxList`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 课表查询模块的学生个人课表查询
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bs | string | 是 | 标识类型, 固定 `"2"` |
| xn | string | 是 | 学年 |
| xq | string | 是 | 学期 |

- **响应**: 返回个人课表数据, 包含每周每节的课程安排

### 3.4 查询班级课表
- **URL**: `Xskbcx/queryBjkbcxList`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询班级课表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bs | string | 是 | 标识类型, 固定 `"2"` |
| xn | string | 是 | 学年 |
| xq | string | 是 | 学期 |

- **响应**: 返回班级课表数据

### 3.5 查询购物车课表
- **URL**: `Xskbcx/queryGwckbcxList`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询购物车中课程的课表视图
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bs | string | 是 | 标识类型, 固定 `"2"` |
| xn | string | 是 | 学年 |
| xq | string | 是 | 学期 |

- **响应**: 返回购物车课表数据

### 3.6 查询开课学期列表
- **URL**: `Xskbcx/queryKkxqList`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 获取可选的开课学期列表, 用于构建学年学期选择器
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| queryform | object | 是 | 基础查询表单 |

- **响应**: 返回开课学期列表

---

## 4. 成绩查询模块 (cjgl)

### 4.1 个人成绩列表
- **URL**: `cjgl/grcjcx/dyxwList`
- **方法**: POST
- **已实现**: ✅ `grades_service.get_grades()`
- **说明**: 获取个人成绩列表, 支持分页和多种筛选条件
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pageNum | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| total | int | 是 | 固定 `0` |
| xjid | string | 是 | 学号 |
| sfgld | string | 是 | 是否过滤, 固定 `"1"` |
| pxzd | string | 否 | 排序字段 |
| pxfx | string | 否 | 排序方向 |
| xn | string | 否 | 学年筛选 |
| xq | string | 否 | 学期筛选 |
| kcxz | string | 否 | 课程性质筛选 |
| kclb | string | 否 | 课程类别筛选 |
| key | string | 否 | 搜索关键字 |
| pylx | string | 是 | 培养类型, 默认 `"1"` |
| sffx | string | 否 | 是否辅修 |
| sfcxfxcj | string | 是 | 是否查询辅修成绩, 固定 `"0"` |
| sfsjqx | string | 是 | 是否使用数据权限, 固定 `"1"` |

- **响应**:
```json
{
  "code": 200,
  "content": {
    "list": ["...成绩记录数组"],
    "total": "总数"
  }
}
```

### 4.2 跳转成绩详情页面
- **URL**: `cjgl/grcjcx/cjxqList`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 页面导航, 跳转到学习进度/成绩详情页面
- **参数**: 无
- **响应**: 页面跳转

### 4.3 获取学生方案信息 (含 fah)
- **URL**: `cjgl/cjzhtjcx/cjcx/getXss`
- **方法**: POST
- **已实现**: ✅ `grades_service.get_student_plan()`
- **说明**: 获取学生信息, 包含培养方案号 `fah`, 用于查询培养方案课程; 也用于学习进度初始化
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xjidorxh | string | 是 | 学号 (JSON 格式提交) |

- **响应**:
```json
{
  "code": 200,
  "content": [{"fah": "方案号", "...": "..."}]
}
```

### 4.4 获取学生信息 (含课程类别列表)
- **URL**: `cjgl/cjzhtjcx/cjcx/getXs`
- **方法**: POST
- **已实现**: ✅ `grades_service.get_student_xs_info()`
- **说明**: 获取学生信息, 包含培养方案号 `fah` 和课程类别列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xjidorxh | string | 是 | 学号 (JSON 格式提交) |

- **响应**:
```json
{
  "code": 200,
  "content": [
    {
      "fah": "方案号",
      "xh": "学号",
      "nj": "年级",
      "pylx": "培养类型",
      "xjid": "学籍ID",
      "kclb_list": [{"dm": "代码", "mc": "名称"}]
    }
  ]
}
```

### 4.5 查询可选学年学期
- **URL**: `cjgl/cjzhtjcx/cjcx/queryqxnxq`
- **方法**: POST
- **已实现**: ✅ `grades_service.get_available_terms()`
- **说明**: 查询成绩查询可选学年学期, 用于学习进度初始化
- **参数**: 空字符串 `data=""`
- **响应**: 返回可选学年学期数据

### 4.6 查询必修课完成情况
- **URL**: `cjgl/cjzhtjcx/cjcx/queryBxkqk`
- **方法**: POST
- **已实现**: ✅ `grades_service.get_required_course_status()`
- **说明**: 查询必修课已修/未修统计
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xh | string | 是 | 学号 |
| pylx | string | 是 | 培养类型, 默认 `"1"` |
| nj | string | 是 | 年级 (学号前4位) |
| jzxnxq | string | 是 | 截止学年学期 |
| xjid | string | 是 | 学号 |
| fah | string | 否 | 方案号 |
| sfcxxfj | string | 是 | 固定 `"0"` |

- **响应**:
```json
{"code": 200, "content": {"...": "必修课完成情况数据"}}
```

### 4.7 查询学分类别要求课程列表
- **URL**: `cjgl/cjzhtjcx/cjcx/queryXflbyq1`
- **方法**: POST
- **已实现**: ✅ `grades_service.query_xflbyq()`
- **说明**: 查询学分类别要求课程列表, 含已修课程成绩, 用于学分完成度统计

> **注意**: 后端调用的是 `queryXflbyq1` (带数字1), 前端 JS 中调用的是 `queryXflbyq` (不带数字1), 可能是不同版本

- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| current | int | 是 | 当前页, 默认 `1` |
| pageSize | int | 是 | 每页数量, 默认 `500` |
| xjid | string | 是 | 学号 |
| zyfxdm | string | 否 | 专业方向代码, 可为 `null` |
| pylx | string | 是 | 培养类型, 默认 `"1"` |
| fah | string | 是 | 方案号 |

- **响应**:
```json
{
  "xflbyqkc": [
    {
      "kcdm": "课程代码",
      "kcmc": "课程名称",
      "xf": "学分",
      "xs": "学时",
      "xscj": "学生成绩",
      "zzcj": "最终成绩",
      "kclbdm": "课程类别代码",
      "kclbmc": "课程类别名称",
      "xnxqmc": "学期名称"
    }
  ]
}
```

### 4.8 查询学分类别要求 (前端版)
- **URL**: `cjgl/cjzhtjcx/cjcx/queryXflbyq`
- **方法**: POST
- **已实现**: ⬜ (后端使用 `queryXflbyq1` 变体)
- **说明**: 查询学分类别要求 (前端组件调用版本)
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| current / pageNum | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| xjid | string | 是 | 学号 |
| pylx | string | 是 | 培养类型 |
| fah | string | 是 | 方案号 |

- **响应**: `sfxsXflbyq` 标识和 `xflbyqData` 数据

### 4.9 查询模块要求
- **URL**: `cjgl/cjzhtjcx/cjcx/queryMkyq`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询模块要求 (成绩综合统计树结构)
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xjid | string | 是 | 学号 |
| pylx | string | 是 | 培养类型 |
| fah | string | 是 | 方案号 |

- **响应**: 模块要求树结构数据, `sfxsMkyq` 标识

### 4.10 查询专业方向统计信息
- **URL**: `cjgl/cjzhtjcx/cjcx/queryZyfxTjinfo`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询专业方向统计信息
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| fah | string | 是 | 方案号 |
| zyfxdm | string | 是 | 专业方向代码 |
| xjid | string | 是 | 学号 |
| pylx | string | 是 | 培养类型 |

- **响应**: 专业方向统计数据

### 4.11 查询课程组详细信息
- **URL**: `cjgl/cjzhtjcx/cjcx/queryInfo`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询课程组详细信息
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 课程组 ID |
| xjid | string | 是 | 学号 |
| kzlx | string | 是 | 课组类型 |
| kcxzdm | string | 否 | 课程性质代码 |
| kclbdm | string | 否 | 课程类别代码 |
| pylx | string | 是 | 培养类型 |

- **响应**: 课程组数据

### 4.12 查询方案课组课程列表
- **URL**: `cjgl/cjzhtjcx/cjcx/queryFaKzkc`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询方案课组中的课程列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pageNum / current | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| xjid | string | 是 | 学号 |
| nj | string | 是 | 年级 |
| pylx | string | 是 | 培养类型 |
| fah | string | 是 | 方案号 |

- **响应**: 课程列表及总数

### 4.13 查询成绩类别课程类别
- **URL**: `cjgl/cjzhtjcx/cjcx/queryCjlbkclb`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询成绩类别课程类别
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| current / pageNum | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| xjid | string | 是 | 学号 |
| pylx | string | 是 | 培养类型 |
| kclbdms | string | 否 | 课程类别代码 (多个) |

- **响应**: 成绩类别课程列表

### 4.14 查询截止学年学期
- **URL**: `cjgl/cjzhtjcx/cjcx/queryJzxnxq`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询截止学年学期 (用于学习进度计算)
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xsquery | object | 是 | 学生查询对象 |

- **响应**: 截止学年学期数组

### 4.15 查询学习进度必修课 (未完成)
- **URL**: `cjgl/cjzhtjcx/cjcx/queryXxjdbxk`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询未完成的必修课列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| current / pageNum | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| xh | string | 是 | 学号 |
| pylx | string | 是 | 培养类型 |
| nj | string | 是 | 年级 |
| jzxnxq | string | 是 | 截止学年学期 |
| xjid | string | 是 | 学号 |

- **响应**: 未完成必修课列表

### 4.16 查询主修成绩分页列表
- **URL**: `cjgl/cjzhtjcx/cjcx/queryZxcjPage`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询主修成绩分页列表, 含绩点统计
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| current / pageNum | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| xh | string | 是 | 学号 |
| xjid | string | 是 | 学号 |
| pylx | string | 是 | 培养类型 |

- **响应**: 成绩数据, 含 `kskxfj` (课时考核学分绩), `pjxfj` (平均学分绩), `zxf` (总学分)

### 4.17 查询主修不合格成绩
- **URL**: `cjgl/cjzhtjcx/cjcx/queryZxcjBhgPage`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询主修不合格成绩 (补考/重修)
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| current / pageNum | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| xh | string | 是 | 学号 |
| xjid | string | 是 | 学号 |
| pylx | string | 是 | 培养类型 |

- **响应**: 不合格成绩数据

### 4.18 查询必修课合格成绩分页
- **URL**: `cjgl/cjzhtjcx/cjcx/queryBxkhgcjPage`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询必修课合格成绩分页
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| current / pageNum | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| xh | string | 是 | 学号 |
| pylx | string | 是 | 培养类型 |
| xjid | string | 是 | 学号 |

- **响应**: 必修课合格成绩记录

### 4.19 查询辅修成绩分页列表
- **URL**: `cjgl/cjzhtjcx/cjcx/queryFxcjPage`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询辅修成绩, 含未完成学分统计
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| current / pageNum | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| xh | string | 是 | 学号 |
| xjid | string | 是 | 学号 |
| pylx | string | 是 | 培养类型 |

- **响应**: 辅修成绩数据和 `wczxf` (未完成学分)

### 4.20 查询奖学金/获奖信息
- **URL**: `cjgl/cjzhtjcx/cjcx/querySlj`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询奖学金/获奖信息
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xsquery | object | 是 | 学生查询对象 |

- **响应**: 奖学金/获奖数据

### 4.21 查询学籍异动信息
- **URL**: `cjgl/cjzhtjcx/cjcx/queryYd`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询学籍异动记录
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xsquery | object | 是 | 学生查询对象 |

- **响应**: 学籍异动数据

### 4.22 查询未通过必修课 (学习进度模块)
- **URL**: `cjgl/cjzhtjcx/cjcx/wtgbxkcx`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 学习进度模块中查询未通过的必修课
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xjid | string | 是 | 学号 |
| falb | string | 是 | 方案类别 |
| jzxn | string | 是 | 截止学年 |
| jzxq | string | 是 | 截止学期 |
| fah | string | 是 | 方案号 |

- **响应**: 未通过必修课数据

### 4.23 查询毕业要求
- **URL**: `cjgl/cjzhtjcx/cjcx/querybyyq`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询毕业要求
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xh | string | 是 | 学号 |
| zyfx | string | 否 | 专业方向 |
| pylx | string | 是 | 培养类型 |
| fah | string | 是 | 方案号 |

- **响应**: 毕业要求数据

### 4.24 查询是否显示毕业要求
- **URL**: `cjgl/cjzhtjcx/cjcx/querysfxsbyyq`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询是否需要显示毕业要求模块 (条件判断)
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xh | string | 是 | 学号 |
| zyfx | string | 否 | 专业方向 |
| pylx | string | 是 | 培养类型 |
| fah | string | 是 | 方案号 |

- **响应**: 条件标志, 决定是否调用 `querybyyq`

### 4.25 研究生学习进度成绩查询
- **URL**: `cjgl/yjsxxjd/cjcx`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 研究生学习进度成绩查询
- **参数**: 基于 Session (无显式参数)
- **响应**: `data.content` 数组, 含 `sfkcx` 属性

### 4.26 查看更多成绩 (页面导航)
- **URL**: `cjgl/grcjcx/go/{pylx}`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 查看更多成绩的页面导航
- **参数**: URL 路径中的 `pylx` (培养类型)
- **响应**: 页面导航

---

## 5. 考试模块

### 5.1 查询学生考试安排
- **URL**: `component/queryKsxxByXs`
- **方法**: POST
- **已实现**: ✅ `schedule_service.get_exam_schedule()`
- **说明**: 获取学生考试安排信息
- **参数**: 空字符串 `data=""`  或 `{}`
- **响应**:
```json
[
  {
    "KCDM": "课程代码",
    "KCMC": "课程名称",
    "KCMC_EN": "英文名",
    "KSSJDMC": "考试时段 (期末/期中)",
    "KSRQ": "考试日期",
    "KSRQ2": "日期显示",
    "KSJTSJ": "具体时间",
    "XQJMC": "星期几",
    "DJZ": "周次",
    "KSJC": "开始节次",
    "JSJC": "结束节次",
    "JXLMC": "教学楼",
    "JXCDMC": "教室",
    "XIAOQUBMC": "校区",
    "XNXQMC": "学期",
    "JKJSBZ": "备注"
  }
]
```

### 5.2 查询监考考试信息
- **URL**: `component/queryKsxxByJk`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询监考人员的考试安排
- **参数**: `{}`
- **响应**: 考试信息数组

### 5.3 查询授课教师考试信息
- **URL**: `component/queryKsxxBySk`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询授课教师的考试安排
- **参数**: `{}`
- **响应**: 考试信息数组

### 5.4 查询教师考试信息列表
- **URL**: `component/queryJsKsxxcxList`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询教师考试信息列表
- **参数**: `{}`
- **响应**: 教师考试列表

### 5.5 查询监考信息查询模式
- **URL**: `component/queryJkxxcxMs`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询监考信息的显示模式
- **参数**: `{}`
- **响应**: `ms` 模式值

### 5.6 查询考试信息标题
- **URL**: `component/queryKsxxTitle`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询考试信息展示标题
- **参数**: `{}`
- **响应**: `ksxx_title` 标题文本

### 5.7 按学号查询监考信息 (页面导航)
- **URL**: `kscxtj/queryJkcxByXh`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 页面导航, 按学号查询监考信息
- **参数**: 无 (页面 URL)
- **响应**: 打开新窗口

### 5.8 按学号查询教师课程考试 (页面导航)
- **URL**: `kscxtj/queryJskccxByXh`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 页面导航, 按学号查询教师课程考试
- **参数**: 无 (页面 URL)
- **响应**: 打开新窗口

### 5.9 按学号查询学生考试 (页面导航)
- **URL**: `kscxtj/queryXskscxByXh`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 页面导航, 按学号查询学生考试
- **参数**: 无 (页面 URL)
- **响应**: 打开新窗口

### 5.10 按学号查询监考信息 (活动版)
- **URL**: `kscxtj/queryJkcxByXh_hd`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 按学号查询监考信息 (活动版)
- **参数**: 无 (页面 URL)
- **响应**: 打开新窗口

### 5.11 按学号查询教师课程考试 (活动版)
- **URL**: `kscxtj/queryJskccxByXh_hd`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 按学号查询教师课程考试 (活动版)
- **参数**: 无 (页面 URL)
- **响应**: 打开新窗口

### 5.12 查询教师考试信息查询页面 (导航)
- **URL**: `kscxtj/queryJsKsxxcx`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 教师考试信息查询页面导航
- **参数**: 无 (页面 URL)
- **响应**: 打开新窗口

---

## 6. 学籍信息模块 (student_info)

### 6.1 查询系统参数配置
- **URL**: `component/sys_param`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询系统参数配置
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mkdm | string | 是 | 模块代码, 如 `"RWMK"` |

- **响应**: 系统参数, 如 `RWAP_SFKWHDWRL`, `QJCS_QFBY` 等

### 6.2 查询学籍状态列表
- **URL**: `component/queryXjzt`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询可用的学籍状态列表
- **参数**: 无
- **响应**: 学籍状态数组

### 6.3 查询学籍信息列表
- **URL**: `component/queryXueji`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询学籍信息列表, 支持多种筛选条件
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| key | string | 否 | 搜索关键字 |
| glyx | string | 否 | 关联学院 |
| zydm | string | 否 | 专业代码 |
| sfsysjqx | string | 否 | 是否使用数据权限 |
| pylx | string | 否 | 培养类型 |
| bjdm | string | 否 | 班级代码 |
| nj | string | 否 | 年级 |
| pcxs | string | 否 | 排序方式 |
| sfzx | string | 否 | 是否在校 |
| xjzt | string | 否 | 学籍状态 |
| pageNum | int | 否 | 页码 |
| pageSize | int | 否 | 每页数量 |

- **响应**: 学生记录列表

### 6.4 查询学籍信息 (不分页)
- **URL**: `component/queryXuejiBfy`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询学籍信息 (不分页, 用于全选操作)
- **参数**: 同 `queryXueji`
- **响应**: 全部学生记录列表

### 6.5 查询学生默认值
- **URL**: `component/queryStudentDefValue`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询学生默认值标签列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xhs | string[] | 是 | 学生 ID 数组 |

- **响应**: 学生默认值标签列表

### 6.6 查询学位信息
- **URL**: `component/queryXwxx`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询学位相关信息
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xh | string | 是 | 学号 |
| xjid | string | 是 | 学籍 ID |

- **响应**: 学位信息, 含答辩成绩、综合考评、开题报告、中期检查、论文、学位审议等字段

---

## 7. 培养方案模块 (plan)

### 7.1 查询培养方案课程列表
- **URL**: `xspyyjsfasq/queryGrjhKcList1`
- **方法**: POST
- **已实现**: ✅ `grades_service.get_plan_course_list()`
- **说明**: 获取培养计划中的全部课程要求
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| multiple | string | 是 | 固定 `"false"` |
| pylx | string | 是 | 培养类型, 默认 `"1"` |
| pylb | string | 是 | 培养类别, 默认 `"1"` |
| bgid | string | 否 | 报告 ID |
| xsid | string | 否 | 学生 ID |
| xh | string | 否 | 学号 |
| fah | string | 是 | 方案号 |
| kcmcdm | string | 否 | 课程名称/代码筛选 |
| yxdm | string | 否 | 学院代码 |
| xqdm | string | 否 | 校区代码 |
| kclbdm | string | 否 | 课程类别代码 |
| kcxzdm | string | 否 | 课程性质代码 |

- **响应**:
```json
{
  "code": 200,
  "content": [
    {
      "kclbmc": "课程类别名称",
      "kcxzmc": "课程性质名称",
      "xf": "学分",
      "kcdm": "课程代码"
    }
  ]
}
```

### 7.2 查询个人计划报告列表
- **URL**: `xspyjhwcqk/queryGrjhBglist`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询个人培养计划完成情况报告列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| fah | string | 是 | 方案号 |
| xh | string | 是 | 学号 |
| pylx | string | 是 | 培养类型 |
| order1 | string | 否 | 排序字段1 |
| order2 | string | 否 | 排序字段2 |

- **响应**: 个人计划报告列表

### 7.3 验证学生方案 (方案满足情况)
- **URL**: `xspyyjsfasq/validationXsFa`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询方案满足情况, 包含课组树、毕业要求、课程要求、实验要求
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pylx | string | 是 | 培养类型 |
| fah | string | 是 | 方案号 |
| xh | string | 是 | 学号 |
| czlx | string | 是 | 操作类型, 固定 `"bg"` |

- **响应**: 含 `kztree` (课组树), `byyq` (毕业要求), `kcyq` (课程要求), `skyyyq` (实验要求)

---

## 8. 通知公告模块 (notification)

### 8.1 查询通知公告列表
- **URL**: `component/queryTongZhiGongGao`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询通知公告列表
- **参数**: `{}`
- **响应**: 通知公告数组

### 8.2 通知公告置顶
- **URL**: `tzgg/zdl`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 将通知公告置顶
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| tzggid | string | 是 | 通知公告 ID |

- **响应**: 操作成功

### 8.3 通知公告标记已读
- **URL**: `tzgg/addyd`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 将通知公告标记为已读
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| tzggid | string | 是 | 通知公告 ID |

- **响应**: 标记已读回调

### 8.4 保存通知公告反馈
- **URL**: `tzgg/savefk`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 保存用户对通知公告的反馈
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| tzggfkform | object | 是 | 反馈表单数据 |

- **响应**: 成功/失败消息

### 8.5 下载通知公告附件
- **URL**: `bysj/sygc/downloadWj`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 下载或预览通知公告附件
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| savename | string | 是 | 服务器保存文件名 |
| filename | string | 是 | 下载显示文件名 |

- **响应**: 文件下载或预览

### 8.6 查询关联制度
- **URL**: `component/queryglzd`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询与通知公告关联的制度
- **参数**: `{}`
- **响应**: 关联制度数组

### 8.7 通知公告实时推送 (WebSocket)
- **URL**: `user/{yhdm}/tzgg`
- **方法**: WebSocket
- **已实现**: ⬜
- **说明**: 通知公告实时推送通道
- **参数**: URL 路径中的 `yhdm` (用户代码)
- **响应**: 实时推送通知

---

## 9. 通用组件接口 (component)

### 9.1 获取当前学年学期
- **URL**: `component/querydangqianxnxq`
- **方法**: POST
- **已实现**: ✅ `schedule_service.get_current_term()`
- **说明**: 获取当前学年学期
- **参数**: 空字符串 `data=""`
- **响应**:
```json
{"XN": "2025-2026", "XQ": "1", "...": "..."}
```

### 9.2 查询学年学期列表
- **URL**: `component/queryXnxq`
- **方法**: POST
- **已实现**: ✅ `schedule_service.get_term_list()` / `grades_service.get_term_list()`
- **说明**: 获取学年学期列表; schedule 模块使用加密参数, grades 模块使用空字符串
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| data | string | 是 | 加密数据 `inco_encrypt(JSON.stringify({pylx, rwlx, cxtj}))` 或空字符串 `""` |

- **响应**:
```json
{"code": 200, "content": [{"xn": "2025-2026", "xq": "1"}]}
```
或直接返回数组

### 9.3 查询周次列表
- **URL**: `component/queryzclist`
- **方法**: POST
- **已实现**: ✅ `schedule_service.get_week_list()`
- **说明**: 获取指定学年学期的周次列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xn | string | 是 | 学年 |
| xq | string | 是 | 学期 |

- **响应**: 周次信息数组

### 9.4 查询日历周次时间
- **URL**: `component/queryRlZcSj`
- **方法**: POST
- **已实现**: ✅ `schedule_service.get_week_dates()`
- **说明**: 获取指定周的日期列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xn | string | 是 | 学年 |
| xq | string | 是 | 学期 |
| djz | string | 是 | 周次 (数字字符串) |

- **响应**:
```json
{"code": 200, "content": [{"xqj": "星期几", "rq": "日期"}]}
```

### 9.5 查询课表结构
- **URL**: `component/queryKbjg`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询课表结构 (节次列表)
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| xn | string | 是 | 学年 |
| xq | string | 是 | 学期 |
| pylx | string | 是 | 培养类型 |

- **响应**: 节次结构数据

### 9.6 获取开课学院列表
- **URL**: `component/queryKkyx`
- **方法**: POST
- **已实现**: ✅ `course_service.get_colleges()`
- **说明**: 获取开课学院列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| data | string | 是 | `"nodataqx=1"` |

- **响应**:
```json
[{"YXDM": "学院代码", "YXMC": "学院名称"}]
```
或 `[{"DM": "代码", "MC": "名称"}]`

### 9.7 获取课程类别列表
- **URL**: `component/queryDmb`
- **方法**: POST
- **已实现**: ✅ `course_service.get_course_categories()`
- **说明**: 通过代码表查询课程类别列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| dmbdm | string | 是 | 代码表代码, 如 `"byyt_kclb"` |
| mbmc | string | 否 | 模板名称 |

- **响应**:
```json
[{"DM": "代码", "MC": "名称"}]
```

### 9.8 获取校区列表
- **URL**: `component/queryXiaoqu`
- **方法**: POST
- **已实现**: ✅ `course_service.get_campuses()`
- **说明**: 获取校区列表, URL 中带 `pylx=3` 查询参数
- **参数**: 空字符串 `data=""`
- **响应**:
```json
{"code": 200, "content": [{"dm": "代码", "mc": "名称"}]}
```

### 9.9 查询当前学年学期 (简版)
- **URL**: `component/dq_xnxq`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询当前学年学期 (另一个接口)
- **参数**: 无
- **响应**:
```json
{"content": {"XN": "学年", "XQ": "学期", "XNMC": "学年名", "XQMC": "学期名", "XNMC_EN": "...", "XQMC_EN": "..."}}
```

### 9.10 查询学年学期 (场地借用)
- **URL**: `component/queryXnxqCdjy`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询学年学期 (场地借用场景)
- **参数**: 继承父组件参数
- **响应**: 学期列表

### 9.11 查询学年学期 (排课管理)
- **URL**: `component/queryXnxqpkgl`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询学年学期 (排课管理场景)
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pylx | string | 否 | 培养类型 |
| rwlx | string | 否 | 任务类型 |

- **响应**: 学期列表

### 9.12 查询学年学期 (考试管理)
- **URL**: `component/queryXnxqksgl`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询学年学期 (考试管理场景)
- **参数**: 继承父组件参数
- **响应**: 学期列表

---

## 10. 课程库模块 (kck)

### 10.1 查询课程列表 (新版)
- **URL**: `component/queryKeChengNew`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 新版课程列表查询, 支持丰富的筛选条件
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| key | string | 否 | 搜索关键字 |
| kcxz | string | 否 | 课程性质 |
| kclb | string | 否 | 课程类别 |
| kkyx | string | 否 | 开课学院 |
| sffankc | string | 否 | 是否翻课 |
| xh | string | 否 | 学号 |
| sfqb | string | 否 | 是否全部 |
| pylx | string | 否 | 培养类型 |
| pageNum | int | 否 | 页码 |
| pageSize | int | 否 | 每页数量 |

- **响应**: 课程列表及分页信息

### 10.2 查询课程默认值
- **URL**: `component/queryKeChengDefValue`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询课程默认值标签列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kcdms | string[] | 是 | 课程代码数组 |

- **响应**: 课程默认值标签列表

### 10.3 查询公共课组
- **URL**: `kck/xxxxkzkc/queryGgkz`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询公共课组列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pylb | string | 是 | 培养类别 |
| lx | string | 是 | 类型 |
| key | string | 否 | 搜索关键字 |

- **响应**: 课组列表及分页

### 10.4 查询选修课程详情
- **URL**: `kck/xxxxkzkc/queryXxkc`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询选修课程详细信息
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kcid | string | 是 | 课程 ID |

- **响应**: 课程详情信息

### 10.5 查询选修课程描述 (按申请)
- **URL**: `kck/xxxxkzkc/queryXxkcBySq`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询选修课程描述
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kcdm | string | 是 | 课程代码 |

- **响应**: 课程描述信息

### 10.6 查询课组信息树
- **URL**: `kck/xxxxkzkc/queryKzxx`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询课组信息树结构
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kzdm | string | 是 | 课组代码 |
| kzlx | string | 是 | 课组类型 |
| kcid | string | 否 | 课程 ID |

- **响应**: 树结构数据

### 10.7 学生查看课程详情 (按选课)
- **URL**: `kck/kcxxwh/xsckViewByxk`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 学生查看课程详情, 含课程大纲等
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kcid | string | 是 | 课程 ID |
| rwh | string | 否 | 任务号 |

- **响应**: 课程详情, 含 `saveform`, `kcdgEntity`, `kcxsbEntity`

### 10.8 下载课程附件
- **URL**: `kck/kcxxwh/downFj`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 下载课程附件
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kcid | string | 是 | 课程 ID |
| fjflag | string | 是 | 附件标识 |
| downFlag | string | 是 | 下载标识 |

- **响应**: 文件下载

### 10.9 下载课程简介附件
- **URL**: `kck/kcxxwh/downkcjjFj`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 下载课程简介附件
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sname | string | 是 | 服务器文件名 |
| fname | string | 是 | 显示文件名 |

- **响应**: 文件下载

### 10.10 下载课程团队附件
- **URL**: `kck/kctdwh/downKctdFj`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 下载课程团队教学资料附件
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 附件 ID |
| downFlag | string | 是 | 下载标识 |

- **响应**: 文件下载

---

## 11. 用户与认证模块

### 11.1 查询学生基本信息
- **URL**: `UserManager/queryxsxx`
- **方法**: POST
- **已实现**: ✅ `grades_service.get_student_info()`
- **说明**: 查询学生基本信息 (学号、姓名等), 也用于认证后验证会话有效性
- **参数**: 空字符串 `data=""` 或无 body
- **响应**:
```json
{"XH": "学号", "XM": "姓名", "content": {"XH": "..."}}
```
> 可能有两种结构: 顶层含 XH 或 content.XH

### 11.2 获取当前用户信息
- **URL**: `user/me`
- **方法**: POST
- **已实现**: ✅ `grades_service.get_user_info()`
- **说明**: 获取当前登录用户完整信息 (含角色权限)
- **参数**: 空字符串 `data=""`
- **响应**: 用户完整信息

### 11.3 查询用户菜单权限
- **URL**: `user/mk`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询用户菜单权限
- **参数**: `{}`
- **响应**: 用户菜单数据, 含 `qxdm` 权限代码

### 11.4 查询菜单子节点详情
- **URL**: `user/getMknodeMore`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询菜单子节点详细信息
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mkdm | string[] | 是 | 模块代码数组 (qxdms) |

- **响应**: 子菜单项, 按 `qxdm` 映射

### 11.5 用户登出
- **URL**: `login/logout.jsp`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 用户登出, 重定向到登录页
- **参数**: 无 (页面重定向)
- **响应**: 重定向到登录页面

---

## 12. 日程管理模块

### 12.1 添加日程信息
- **URL**: `component/rcxxAdd`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 添加个人日程
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bt | string | 是 | 标题 |
| rcrq | string | 是 | 日程日期 |
| sj | string | 否 | 时间 |
| nr | string | 否 | 内容 |
| lb | string | 否 | 类别 |
| sfxs | string | 否 | 是否显示 |
| sj1 | string | 否 | 时间1 |
| xzrq | string | 否 | 选择日期 |

- **响应**: `{"jg": "1"}` 表示成功

### 12.2 删除日程信息
- **URL**: `component/rcxxdel`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 删除个人日程
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 日程 ID |

- **响应**: `{"jg": "1"}` 表示成功

### 12.3 查询日程类别数据
- **URL**: `component/queryrclbdata`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询可用的日程类别
- **参数**: 无
- **响应**: 日程类别数组

### 12.4 查询个人日程列表
- **URL**: `component/querygrrclist`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询个人日程列表
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| rcrq | string | 否 | 日程日期, 如 `"2026-03-01"` |

- **响应**: 个人日程列表

### 12.5 查询日程详情列表
- **URL**: `component/queryrcxxlist`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询指定日期的日程详情
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| rcrq | string | 是 | 日期 |

- **响应**: 日程详情列表

---

## 13. 收藏功能

### 13.1 查询收藏列表
- **URL**: `component/queryShouCang`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询用户收藏的功能列表
- **参数**: `{}`
- **响应**: 收藏列表

### 13.2 添加功能收藏
- **URL**: `component/shouCang`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 将功能添加到收藏
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| qxdm | string | 是 | 权限代码 |
| jsdm | string | 是 | 角色代码 |

- **响应**: 操作成功消息

### 13.3 取消功能收藏
- **URL**: `component/qxshouCang`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 取消功能收藏
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| qxdm | string | 是 | 权限代码 |
| jsdm | string | 是 | 角色代码 |

- **响应**: 操作成功消息

---

## 14. 系统与报表接口

### 14.1 查询系统属性配置
- **URL**: `system/property`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询系统属性配置, 存储到 localStorage
- **参数**: 无
- **响应**: 系统属性对象

### 14.2 通用混入数据加载
- **URL**: `mixins/load`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 通用数据加载接口
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 数据 ID |

- **响应**: JSON 数据

### 14.3 查询自定义列信息
- **URL**: `core/zdylxx/api/{id}`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 查询自定义列配置
- **参数**: `{}`, URL 路径中的 `id`
- **响应**: `{"content": {"nr": "..."}}`

### 14.4 获取报表系统 SSO Token
- **URL**: `browserRedirect/getToken`
- **方法**: GET
- **已实现**: ⬜
- **说明**: 获取 FineReport 报表系统 SSO Token
- **参数**: 无
- **响应**: Token 字符串

### 14.5 报表电子签章
- **URL**: `fineReport/dian_zi_qian_zhang`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 报表电子签章功能
- **参数**: 报表参数表单
- **响应**: WebSocket 状态更新

### 14.6 报表批量下载
- **URL**: `fineReport/batch_download`
- **方法**: POST
- **已实现**: ⬜
- **说明**: 批量下载报表
- **参数**: 模板/格式/报表数据
- **响应**: WebSocket 进度更新

---

## 15. BYYT 代理接口 (jwapp)

### 15.1 获取成绩 (jwapp)
- **URL**: `/jwapp/sys/wdcj/modules/wdcj/xscjcx.do`
- **方法**: GET
- **已实现**: ✅ `byyt_proxy.get_grades()`
- **说明**: 通过 jwapp 路径获取成绩, 不同于 cjgl 路径的成绩接口
- **参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| XNXQDM | string | 否 | 学期代码 (URL 查询参数) |

- **响应**: BYYT 原始成绩数据 (jwapp 系统格式)

### 15.2 获取用户档案信息
- **URL**: `/jwapp/sys/emappagelog/config/index.do`
- **方法**: GET
- **已实现**: ✅ `byyt_proxy.get_profile()`
- **说明**: 获取用户档案信息
- **参数**: 无
- **响应**: BYYT 原始用户档案数据

---

## 附录: 已实现与未实现端点统计

### 统计概览

| 类别 | 已实现 | 未实现 | 合计 |
|------|--------|--------|------|
| 选课模块 (Xsxk) | 9 | 8 | 17 |
| 选课辅助模块 (Xsxktz/xkgzsz) | 0 | 2 | 2 |
| 课表模块 (xszykb/Xskbcx) | 2 | 4 | 6 |
| 成绩查询模块 (cjgl) | 7 | 19 | 26 |
| 考试模块 | 1 | 11 | 12 |
| 学籍信息模块 | 0 | 6 | 6 |
| 培养方案模块 | 1 | 2 | 3 |
| 通知公告模块 | 0 | 7 | 7 |
| 通用组件接口 | 7 | 5 | 12 |
| 课程库模块 (kck) | 0 | 10 | 10 |
| 用户与认证模块 | 2 | 3 | 5 |
| 日程管理模块 | 0 | 5 | 5 |
| 收藏功能 | 0 | 3 | 3 |
| 系统与报表接口 | 0 | 6 | 6 |
| BYYT 代理接口 | 2 | 0 | 2 |
| **合计** | **31** | **91** | **122** |

### 已实现端点列表 (31 个)

| # | URL | Python 函数 | 所在文件 |
|---|-----|-------------|----------|
| 1 | `UserManager/queryxsxx` | `get_student_info()` | grades_service.py |
| 2 | `user/me` | `get_user_info()` | grades_service.py |
| 3 | `component/querydangqianxnxq` | `get_current_term()` | schedule_service.py |
| 4 | `component/queryXnxq` | `get_term_list()` | schedule_service.py / grades_service.py |
| 5 | `component/queryzclist` | `get_week_list()` | schedule_service.py |
| 6 | `component/queryRlZcSj` | `get_week_dates()` | schedule_service.py |
| 7 | `xszykb/queryxszykbzong` | `get_full_schedule()` | schedule_service.py |
| 8 | `xszykb/queryxszykbzhou` | `get_week_schedule()` | schedule_service.py |
| 9 | `component/queryKsxxByXs` | `get_exam_schedule()` | schedule_service.py |
| 10 | `cjgl/grcjcx/dyxwList` | `get_grades()` | grades_service.py |
| 11 | `xspyyjsfasq/queryGrjhKcList1` | `get_plan_course_list()` | grades_service.py |
| 12 | `cjgl/cjzhtjcx/cjcx/getXss` | `get_student_plan()` | grades_service.py |
| 13 | `cjgl/cjzhtjcx/cjcx/queryqxnxq` | `get_available_terms()` | grades_service.py |
| 14 | `cjgl/cjzhtjcx/cjcx/queryBxkqk` | `get_required_course_status()` | grades_service.py |
| 15 | `cjgl/cjzhtjcx/cjcx/getXs` | `get_student_xs_info()` | grades_service.py |
| 16 | `cjgl/cjzhtjcx/cjcx/queryXflbyq1` | `query_xflbyq()` | grades_service.py |
| 17 | `Xsxk/queryXkdqXnxq` | `get_course_term_info()` | course_service.py |
| 18 | `Xsxk/queryYxkc` | `get_selected_courses()` | course_service.py |
| 19 | `Xsxk/queryKxrw` | `get_available_courses()` | course_service.py |
| 20 | `Xsxk/addGouwuche` | `select_course()` / `add_to_cart()` | course_service.py |
| 21 | `Xsxk/tuike` | `drop_course()` | course_service.py |
| 22 | `Xsxk/delGouwuche` | `remove_from_cart()` | course_service.py |
| 23 | `Xsxk/addXuanke` | `submit_cart()` | course_service.py |
| 24 | `Xsxk/queryXkgwc` | `get_cart()` | course_service.py |
| 25 | `Xsxk/queryXsxkrzList` | `get_selection_log()` | course_service.py |
| 26 | `component/queryKkyx` | `get_colleges()` | course_service.py |
| 27 | `component/queryDmb` | `get_course_categories()` | course_service.py |
| 28 | `component/queryXiaoqu` | `get_campuses()` | course_service.py |
| 29 | `/jwapp/sys/wdcj/modules/wdcj/xscjcx.do` | `get_grades()` | byyt_proxy.py |
| 30 | `/jwapp/sys/emappagelog/config/index.do` | `get_profile()` | byyt_proxy.py |
| 31 | (component/queryXnxq 重复调用) | `get_term_list()` | grades_service.py |
