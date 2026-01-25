# BYYT API 响应示例和字段说明

本文档包含从BYYT系统捕获的真实API响应示例（已脱敏处理）和详细的字段说明。

## 1. 成绩查询接口

### 接口信息
- **URL**: `POST /cjgl/grcjcx/dyxwList`
- **用途**: 获取学生个人成绩列表，支持分页和筛选

### 请求参数
```
pageNum=1              # 页码
pageSize=20            # 每页记录数
total=0                # 总记录数（首次查询传0）
xjid=U202412345        # 学籍ID（学号）
sfgld=1                # 是否过滤掉（1=否）
pxzd=                  # 排序字段
pxfx=                  # 排序方向
xn=                    # 学年（如：2024-2025）
xq=                    # 学期（1/2/3）
kcxz=                  # 课程性质（必修/选修等）
kclb=                  # 课程类别
key=                   # 关键字搜索
pylx=1                 # 培养类型（1=本科）
sffx=                  # 是否辅修
sfcxfxcj=0             # 是否查询辅修成绩
sfsjqx=1               # 是否实践权限
```

### 响应示例（脱敏）
```json
{
  "code": 200,
  "msg": null,
  "msg_en": null,
  "content": {
    "total": 43,
    "list": [
      {
        "xnxq": "2025-2026-1",
        "xnxq_en": "2025Autumn",
        "kcdm": "1060110",
        "kcmc": "线性代数A",
        "kcmc_en": "Linear Algebra A",
        "kcxzmc": "必修",
        "kclbmc": "通识课程",
        "kkdw": "数理学院",
        "kkdw_en": "the School of Mathematics and Physics",
        "jsxm": "张三",
        "xf": "3",
        "xs": "48",
        "xscj": "85",
        "xszscj": "85",
        "zpcj": "85",
        "zzzscj": "85",
        "zzcj": "85",
        "bkcxbj": "正考",
        "bkcxbj_en": "Formal examination",
        "rwh": "2025-2026-1-1060110-019",
        "rwlx": "必修课任务",
        "rwlx_en": "必修课任务_en",
        "xszxs": "48",
        "xnxqx": "2025-20261",
        "sfpjcxcj": "0"
      }
    ]
  }
}
```

### 字段说明

#### 响应结构
| 字段 | 类型 | 说明 |
|------|------|------|
| code | number | 响应状态码，200表示成功 |
| msg | string | 错误消息（成功时为null） |
| msg_en | string | 英文错误消息 |
| content | object | 响应内容 |
| content.total | number | 总记录数 |
| content.list | array | 成绩列表 |

#### 成绩记录字段
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| xnxq | string | 学年学期 | "2025-2026-1" |
| xnxq_en | string | 学年学期英文 | "2025Autumn" |
| xnxqx | string | 学年学期代码 | "2025-20261" |
| kcdm | string | 课程代码 | "1060110" |
| kcmc | string | 课程名称 | "线性代数A" |
| kcmc_en | string | 课程名称英文 | "Linear Algebra A" |
| kcxzmc | string | 课程性质名称 | "必修"/"选修"/"任选" |
| kclbmc | string | 课程类别名称 | "通识课程"/"学科平台"/"专业课程" |
| kkdw | string | 开课单位 | "数理学院" |
| kkdw_en | string | 开课单位英文 | "the School of Mathematics and Physics" |
| jsxm | string | 教师姓名 | "张三" |
| xf | string | 学分 | "3" |
| xs | string | 学时 | "48" |
| xszxs | string | 学生总学时 | "48" |
| xscj | string | 学生成绩 | "85" |
| xszscj | string | 学生折算成绩 | "85" |
| zpcj | string | 总评成绩 | "85" |
| zzzscj | string | 总折算成绩 | "85" |
| zzcj | string | 最终成绩 | "85" |
| bkcxbj | string | 补考重修标记 | "正考"/"补考"/"重修" |
| bkcxbj_en | string | 补考重修标记英文 | "Formal examination" |
| rwh | string | 任务号 | "2025-2026-1-1060110-019" |
| rwlx | string | 任务类型 | "必修课任务"/"选修课任务" |
| rwlx_en | string | 任务类型英文 | "必修课任务_en" |
| sfpjcxcj | string | 是否平均重修成绩 | "0"/"1" |
| cjbz | string | 成绩备注 | 可能为null |
| cjbzmc | string | 成绩备注名称 | 可能为null |

## 2. 学生信息查询接口

### 接口信息
- **URL**: `POST /UserManager/queryxsxx`
- **用途**: 获取学生基本信息

### 请求参数
```
无请求体（空字符串）
```

### 响应示例（脱敏）
```json
{
  "XH": "U202412345",
  "XM": "张三",
  "XBMC": "男",
  "CSRQ": "2005-01-15",
  "SFZH": "110101200501150000",
  "MZ": "汉族",
  "ZZMMMC": "共青团员",
  "YXMC": "经济管理学院",
  "ZYMC": "信息管理与信息系统",
  "BJMC": "信管2024-1班",
  "NJ": "2024",
  "RXNY": "2024",
  "XJZTMC": "在校",
  "PYCCMC": "四年",
  "PYCCDM": "4",
  "XSLBMC": "普通本科生",
  "XZMC": "本科",
  "SJHM": "13800138000",
  "DZYX": "zhangsan@example.com"
}
```

### 字段说明
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| XH | string | 学号 | "U202412345" |
| XM | string | 姓名 | "张三" |
| XBMC | string | 性别名称 | "男"/"女" |
| CSRQ | string | 出生日期 | "2005-01-15" |
| SFZH | string | 身份证号 | "110101200501150000" |
| MZ | string | 民族 | "汉族" |
| ZZMMMC | string | 政治面貌名称 | "共青团员"/"中共党员" |
| YXMC | string | 院系名称 | "经济管理学院" |
| ZYMC | string | 专业名称 | "信息管理与信息系统" |
| BJMC | string | 班级名称 | "信管2024-1班" |
| NJ | string | 年级 | "2024" |
| RXNY | string | 入学年月 | "2024" |
| XJZTMC | string | 学籍状态名称 | "在校"/"休学"/"毕业" |
| PYCCMC | string | 培养层次名称 | "四年"/"五年" |
| PYCCDM | string | 培养层次代码 | "4"/"5" |
| XSLBMC | string | 学生类别名称 | "普通本科生" |
| XZMC | string | 学制名称 | "本科"/"硕士"/"博士" |
| SJHM | string | 手机号码 | "13800138000" |
| DZYX | string | 电子邮箱 | "zhangsan@example.com" |

## 3. 可选学年学期查询接口

### 接口信息
- **URL**: `POST /cjgl/cjzhtjcx/cjcx/queryqxnxq`
- **用途**: 查询可用于成绩查询的学年学期列表

### 请求参数
```
无请求体（空字符串）
```

### 响应示例（脱敏）
```json
{
  "code": 200,
  "msg": null,
  "content": [
    {
      "xnxqdm": "2025-2026-1",
      "xnxqmc": "2025-2026学年第一学期"
    },
    {
      "xnxqdm": "2024-2025-3",
      "xnxqmc": "2024-2025学年夏季学期"
    },
    {
      "xnxqdm": "2024-2025-2",
      "xnxqmc": "2024-2025学年第二学期"
    }
  ]
}
```

### 字段说明
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| xnxqdm | string | 学年学期代码 | "2025-2026-1" |
| xnxqmc | string | 学年学期名称 | "2025-2026学年第一学期" |

## 4. 必修课完成情况查询接口

### 接口信息
- **URL**: `POST /cjgl/cjzhtjcx/cjcx/queryBxkqk`
- **用途**: 查询必修课程的完成情况

### 请求参数
```json
{
  "xh": "U202412345",
  "pylx": "1",
  "nj": "2024",
  "jzxnxq": "2024-2025-3",
  "xjid": "U202412345",
  "fah": "",
  "sfcxxfj": "0"
}
```

### 响应示例（脱敏）
```json
{
  "code": 200,
  "msg": null,
  "content": {
    "yqms": 45,
    "ywcms": 14,
    "yqxf": 120.5,
    "ywcxf": 35.0,
    "wcbl": "29.05%",
    "list": [
      {
        "kcdm": "1060110",
        "kcmc": "线性代数A",
        "xf": "3",
        "xs": "48",
        "kcxzmc": "必修",
        "kclbmc": "通识课程",
        "sfwc": "1",
        "xscj": "85",
        "xnxqmc": "2025-2026-1"
      }
    ]
  }
}
```

### 字段说明
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| yqms | number | 要求门数 | 45 |
| ywcms | number | 已完成门数 | 14 |
| yqxf | number | 要求学分 | 120.5 |
| ywcxf | number | 已完成学分 | 35.0 |
| wcbl | string | 完成比例 | "29.05%" |
| list | array | 课程列表 | - |
| list[].kcdm | string | 课程代码 | "1060110" |
| list[].kcmc | string | 课程名称 | "线性代数A" |
| list[].xf | string | 学分 | "3" |
| list[].xs | string | 学时 | "48" |
| list[].kcxzmc | string | 课程性质名称 | "必修" |
| list[].kclbmc | string | 课程类别名称 | "通识课程" |
| list[].sfwc | string | 是否完成 | "1"=已完成, "0"=未完成 |
| list[].xscj | string | 学生成绩 | "85" |
| list[].xnxqmc | string | 学年学期名称 | "2025-2026-1" |

## 5. 学年学期列表查询接口

### 接口信息
- **URL**: `POST /component/queryXnxq`
- **用途**: 获取完整的学年学期列表

### 请求参数
```
无请求体（空字符串）
```

### 响应示例（脱敏）
```json
[
  {
    "dm": "2025-2026-1",
    "mc": "2025-2026学年第一学期",
    "kssj": "2025-09-01",
    "jssj": "2026-01-15"
  },
  {
    "dm": "2024-2025-3",
    "mc": "2024-2025学年夏季学期",
    "kssj": "2025-07-01",
    "jssj": "2025-08-31"
  }
]
```

### 字段说明
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| dm | string | 代码（学年学期代码） | "2025-2026-1" |
| mc | string | 名称（学年学期名称） | "2025-2026学年第一学期" |
| kssj | string | 开始时间 | "2025-09-01" |
| jssj | string | 结束时间 | "2026-01-15" |

## 接口依赖关系

### 成绩查询流程
1. **登录认证** → 获取session cookie
2. **查询可选学期** (`/cjgl/cjzhtjcx/cjcx/queryqxnxq`) → 获取可查询的学期列表
3. **查询成绩列表** (`/cjgl/grcjcx/dyxwList`) → 根据学期筛选成绩

### 学业进度查询流程
1. **登录认证** → 获取session cookie
2. **获取学生信息** (`/UserManager/queryxsxx`) → 获取学号、专业等基本信息
3. **获取培养方案** (`/cjgl/cjzhtjcx/cjcx/getXss`) → 获取学生的培养方案号(fah)
4. **查询必修课情况** (`/cjgl/cjzhtjcx/cjcx/queryBxkqk`) → 查看必修课完成度
5. **查询学分完成情况** (`/cjgl/cjzhtjcx/cjcx/queryXflbyq1`) → 查看各类课程学分统计

## 6. 用户完整信息查询接口

### 接口信息
- **URL**: `POST /user/me`
- **用途**: 获取当前登录用户的完整信息，包括权限、角色、选课信息等

### 请求参数
```
无请求体（空字符串）
```

### 响应示例（脱敏）
```json
{
  "yhdm": "U202412345",
  "xm": "张三",
  "xm_en": "Zhang San",
  "kyf": "1",
  "skin": "skin_b.css",
  "id": "U202412345",
  "bmdm": "07",
  "bmmc": "经济管理学院",
  "bmmc_en": "the School of Economics and Management",
  "sfxs": "1",
  "sfzx": "1",
  "pylx": "1",
  "username": "U202412345",
  "loginType": "oauth2",
  "yhsf": "03",
  "authorities": [
    {"authority": "1813"},
    {"authority": "2505"}
  ],
  "rolecode": ["01"],
  "role": [
    {
      "jsdm": "01",
      "jsmc": "本科生",
      "xtdm": "jwxt"
    }
  ],
  "xkxg_xs": {
    "xsid": "U202412345",
    "xh": "U202412345",
    "xm": "张三",
    "xjnj": "2024",
    "xjyxdm": "07",
    "xjzydm": "0074",
    "bjdm": "07742401",
    "pylx": "1",
    "xz": "4"
  }
}
```

### 字段说明
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| yhdm | string | 用户代码（学号） | "U202412345" |
| xm | string | 姓名 | "张三" |
| xm_en | string | 英文姓名 | "Zhang San" |
| bmdm | string | 部门代码 | "07" |
| bmmc | string | 部门名称（院系） | "经济管理学院" |
| bmmc_en | string | 部门英文名称 | "the School of Economics and Management" |
| sfxs | string | 是否学生 | "1"=是 |
| sfzx | string | 是否在校 | "1"=是 |
| pylx | string | 培养类型 | "1"=本科 |
| loginType | string | 登录类型 | "oauth2" |
| yhsf | string | 用户身份代码 | "03"=学生 |
| authorities | array | 权限列表 | - |
| rolecode | array | 角色代码列表 | ["01"] |
| role | array | 角色详细信息 | - |
| xkxg_xs | object | 选课相关学生信息 | - |
| xkxg_xs.xjnj | string | 学籍年级 | "2024" |
| xkxg_xs.xjyxdm | string | 学籍院系代码 | "07" |
| xkxg_xs.xjzydm | string | 学籍专业代码 | "0074" |
| xkxg_xs.bjdm | string | 班级代码 | "07742401" |
| xkxg_xs.xz | string | 学制 | "4" |

## 7. 用户基本信息查询接口

### 接口信息
- **URL**: `POST /user/basic`
- **用途**: 获取当前用户的基本信息（简化版）

### 请求参数
```
无请求体（空字符串）
```

### 响应示例（脱敏）
```json
{
  "yhdm": "U202412345",
  "xm": "张三",
  "xm_en": "Zhang San",
  "kyf": "1",
  "skin": "skin_b.css",
  "id": "U202412345",
  "bmdm": "07",
  "bmmc": "经济管理学院",
  "bmmc_en": "the School of Economics and Management",
  "sfxs": "1",
  "sfzx": "1",
  "sfzj": "1",
  "sfzc": "1",
  "pyccm": "03",
  "pylx": "1",
  "sfytxxjk": "0"
}
```

### 字段说明
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| yhdm | string | 用户代码 | "U202412345" |
| xm | string | 姓名 | "张三" |
| xm_en | string | 英文姓名 | "Zhang San" |
| bmdm | string | 部门代码 | "07" |
| bmmc | string | 部门名称 | "经济管理学院" |
| sfxs | string | 是否学生 | "1" |
| sfzx | string | 是否在校 | "1" |
| sfzj | string | 是否在籍 | "1" |
| sfzc | string | 是否正常 | "1" |
| pyccm | string | 培养层次码 | "03"=本科 |
| pylx | string | 培养类型 | "1" |

## 8. 学生培养方案信息查询接口

### 接口信息
- **URL**: `POST /cjgl/cjzhtjcx/cjcx/getXs`
- **用途**: 获取学生信息及培养方案号(fah)和课程类别列表

### 请求参数
```json
{
  "xjidorxh": "U202412345"
}
```

### 响应示例（脱敏）
```json
{
  "code": 200,
  "msg": null,
  "content": [
    {
      "xh": "U202412345",
      "xjid": "U202412345",
      "nj": "2024",
      "pylx": "1",
      "fah": "2235187B93874310A372AA8A1E6EA371",
      "falxdm": "1",
      "kclb_list": [
        {"dm": "05", "mc": "专业选修", "level": "1"},
        {"dm": "18", "mc": "国防公益", "level": "1"},
        {"dm": "19", "mc": "通识课程", "level": "1"},
        {"dm": "20", "mc": "学科平台", "level": "1"},
        {"dm": "21", "mc": "专业核心", "level": "1"},
        {"dm": "23", "mc": "素质拓展", "level": "1"},
        {"dm": "2301", "mc": "外语(素质拓展)", "level": "2"},
        {"dm": "2302", "mc": "美育(素质拓展)", "level": "2"},
        {"dm": "2303", "mc": "自主选修(素质拓展)", "level": "2"},
        {"dm": "24", "mc": "基础实习", "level": "1"},
        {"dm": "25", "mc": "专业实习", "level": "1"},
        {"dm": "27", "mc": "创新创业", "level": "1"},
        {"dm": "37", "mc": "劳育", "level": "1"},
        {"dm": "55", "mc": "专业拓展", "level": "1"}
      ],
      "rwlx_list": [
        {"lxdm": "mooc", "lxmc": "MOOC"},
        {"lxdm": "zyrw", "lxmc": "必修课任务"},
        {"lxdm": "xmjxrw", "lxmc": "项目教学任务"},
        {"lxdm": "ggkrw", "lxmc": "公共课任务"},
        {"lxdm": "zytzk", "lxmc": "专业拓展课"},
        {"lxdm": "sztzk", "lxmc": "素质拓展课"}
      ]
    }
  ]
}
```

### 字段说明
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| xh | string | 学号 | "U202412345" |
| xjid | string | 学籍ID | "U202412345" |
| nj | string | 年级 | "2024" |
| pylx | string | 培养类型 | "1"=本科 |
| fah | string | 培养方案号（重要！用于查询学分要求） | "2235187B..." |
| falxdm | string | 方案类型代码 | "1" |
| kclb_list | array | 课程类别列表 | - |
| kclb_list[].dm | string | 类别代码 | "19" |
| kclb_list[].mc | string | 类别名称 | "通识课程" |
| kclb_list[].level | string | 层级 | "1"=一级, "2"=二级 |
| rwlx_list | array | 任务类型列表 | - |
| rwlx_list[].lxdm | string | 类型代码 | "zyrw" |
| rwlx_list[].lxmc | string | 类型名称 | "必修课任务" |

## 9. 课程性质查询接口

### 接口信息
- **URL**: `POST /component/queryKcxz`
- **用途**: 查询课程性质列表（必修/限选/任选）

### 请求参数
```
pylb=1    # 培养类别（1=本科）
```

### 响应示例
```json
{
  "code": 200,
  "msg": null,
  "content": [
    {"dm": "1", "mc": "必修"},
    {"dm": "4", "mc": "任选"},
    {"dm": "2", "mc": "限选"}
  ]
}
```

### 字段说明
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| dm | string | 代码 | "1" |
| mc | string | 名称 | "必修" |

### 课程性质代码对照
| 代码 | 名称 | 说明 |
|------|------|------|
| 1 | 必修 | 培养方案中必须完成的课程 |
| 2 | 限选 | 在指定范围内选择的课程 |
| 4 | 任选 | 自由选择的课程 |

## 10. 当前学年学期查询接口

### 接口信息
- **URL**: `POST /component/dq_xnxq`
- **用途**: 获取当前的学年学期信息

### 请求参数
```
无请求体（空字符串）
```

### 响应示例
```json
{
  "code": 0,
  "msg": null,
  "content": {
    "XQMC_EN": "Autumn",
    "XNMC": "2025-2026",
    "XN": "2025-2026",
    "XQMC": "-1",
    "XNMC_EN": "2025",
    "XQ": "1"
  }
}
```

### 字段说明
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| XN | string | 学年 | "2025-2026" |
| XNMC | string | 学年名称 | "2025-2026" |
| XNMC_EN | string | 学年英文 | "2025" |
| XQ | string | 学期代码 | "1"=秋季, "2"=春季, "3"=夏季 |
| XQMC | string | 学期名称 | "-1"（需映射） |
| XQMC_EN | string | 学期英文 | "Autumn" |

## 接口依赖关系

### 成绩查询流程
1. **登录认证** → 获取session cookie
2. **查询可选学期** (`/cjgl/cjzhtjcx/cjcx/queryqxnxq`) → 获取可查询的学期列表
3. **查询成绩列表** (`/cjgl/grcjcx/dyxwList`) → 根据学期筛选成绩

### 学业进度查询流程
1. **登录认证** → 获取session cookie
2. **获取学生信息** (`/UserManager/queryxsxx`) → 获取学号、专业等基本信息
3. **获取培养方案** (`/cjgl/cjzhtjcx/cjcx/getXs`) → 获取学生的培养方案号(fah)和课程类别
4. **查询必修课情况** (`/cjgl/cjzhtjcx/cjcx/queryBxkqk`) → 查看必修课完成度
5. **查询学分完成情况** (`/cjgl/cjzhtjcx/cjcx/queryXflbyq1`) → 查看各类课程学分统计

### 用户信息查询流程
1. **登录认证** → 获取session cookie
2. **获取用户完整信息** (`/user/me`) → 包含权限、角色、选课信息
3. **或获取基本信息** (`/user/basic`) → 简化版用户信息

## 常用字段拼音缩写对照表

| 缩写 | 全称 | 英文 |
|------|------|------|
| xh | 学号 | Student ID |
| xm | 姓名 | Name |
| xb | 性别 | Gender |
| nj | 年级 | Grade |
| yx | 院系 | Department |
| zy | 专业 | Major |
| bj | 班级 | Class |
| xn | 学年 | Academic Year |
| xq | 学期 | Semester |
| xf | 学分 | Credit |
| xs | 学时 | Hours |
| kc | 课程 | Course |
| cj | 成绩 | Grade/Score |
| dm | 代码 | Code |
| mc | 名称 | Name |
| py | 培养 | Training |
| rw | 任务 | Task |
| js | 教师 | Teacher |
| kk | 开课 | Course Offering |
| bk | 补考 | Make-up Exam |
| cx | 重修 | Retake |

## 注意事项

1. **认证要求**: 所有接口都需要携带有效的session cookie (INCO和SESSION)
2. **数据格式**: 大部分数值字段以字符串形式返回，需要在客户端转换
3. **字段命名**: 字段名使用拼音缩写，如XH=学号、XM=姓名、YXMC=院系名称
4. **空值处理**: 某些字段可能为null或空字符串，需要做好空值处理
5. **分页**: 成绩查询等接口支持分页，注意total字段的使用
6. **学期格式**: 学年学期格式为"YYYY-YYYY-X"，其中X为1(秋季)/2(春季)/3(夏季)
7. **培养方案号(fah)**: 这是一个关键字段，用于查询学分要求等接口，需从getXs接口获取
8. **响应状态码**: 大部分接口返回code=200表示成功，但部分接口（如dq_xnxq）返回code=0表示成功

---

## 7. 课表查询接口

### 7.1 获取当前学年学期
- **URL**: `POST /component/querydangqianxnxq`
- **用途**: 获取当前学年学期信息

**响应示例**:
```json
{
  "XNXQ_EN": "2025Autumn",
  "XN": "2025-2026",
  "XNXQ": "2025-2026-1",
  "XQ": "1"
}
```

### 7.2 获取周次列表
- **URL**: `POST /component/queryzclist`
- **参数**: `xn=&xq=` (可选)

**响应示例**:
```json
[{"ZC":1},{"ZC":2},...,{"ZC":18},{"ZC":99}]
```
> 注：ZC=99 表示"未排周次"

### 7.3 获取总课表
- **URL**: `POST /xszykb/queryxszykbzong`
- **参数**: `xn=2025-2026&xq=1`

**响应示例**:
```json
[
  {
    "JSJC": 8,           // 结束节次
    "KSJC": 7,           // 开始节次
    "RWH": "2025-2026-1-1080108-013",  // 任务号
    "SKSJ": "马克思主义基本原理\n宁全荣\n1-16周\n【校本部】逸夫楼502\n第7-8节",  // 上课时间描述
    "ZC": "0111111111111111100000000000000000",  // 周次位图（1表示有课）
    "XB": 3,             // 序号
    "SKSJ_EN": "...",    // 英文版
    "PYLX": "1",         // 培养类型
    "KEY": "xq1_jc4"     // 位置标识（xq1=周一, jc4=第7-8节）
  }
]
```

**字段说明**:
- `KEY`: 格式为 `xq{星期}_jc{节次组}`，其中星期1-7对应周一到周日，节次组1=1-2节、2=3-4节...
- `ZC`: 34位周次位图，第N位为1表示第N周有课
- `SKSJ`: 用换行符分隔的课程信息（课程名、教师、周次、地点、节次）

### 7.4 获取周课表
- **URL**: `POST /xszykb/queryxszykbzhou`
- **参数**: `xn=2025-2026&xq=1&zc=1` (zc为周次)

**响应示例**: 与总课表格式相同，但只返回该周有课的课程

### 7.5 获取周日期
- **URL**: `POST /component/queryRlZcSj`
- **参数**: `xn=2025-2026&xq=1&djz=1` (djz为周次)

**响应示例**:
```json
{
  "code": 200,
  "content": [
    {"xqj": "1", "rq": "2025-09-01"},
    {"xqj": "2", "rq": "2025-09-02"},
    {"xqj": "3", "rq": "2025-09-03"},
    {"xqj": "4", "rq": "2025-09-04"},
    {"xqj": "5", "rq": "2025-09-05"},
    {"xqj": "6", "rq": "2025-09-06"},
    {"xqj": "7", "rq": "2025-09-07"}
  ]
}
```

**字段说明**:
- `xqj`: 星期几（1-7）
- `rq`: 对应日期

## 8. 考试安排查询接口

### 接口信息
- **URL**: `POST /component/queryKsxxByXs`
- **用途**: 获取学生的考试安排列表

### 请求参数
```
无请求体（空字符串）
```

### 响应示例（脱敏）
```json
[
  {
    "KCDM": "2071004",
    "KSJC": 8,
    "XQJMC_EN": "星期一",
    "YHID": "U202412345",
    "KSRQ": "2025-12-29",
    "KSSJDMC_EN": "期末考试_en",
    "XIAOQUBMC_EN": "校本部",
    "KCMC": "管理信息系统",
    "DJZ": 17,
    "XNXQMC": "2025-2026-1",
    "JSJC": 10,
    "KSJTSJ": "16:00-18:00",
    "KSHKID": "c0fd7638-9ded-4a9c-ac44-74ef10d7c7be",
    "JKJSBZ": "",
    "XIAOQUBMC": "校本部",
    "KSRQ2": "12月29日",
    "JXLMC": "逸夫楼",
    "PYLX": "1",
    "KSSJDMC": "期末",
    "JXCDMC_EN": null,
    "CDDM": "0238",
    "XNXQMC_EN": "2025Autumn",
    "XQJMC": "星期一",
    "JXCDMC": "逸夫楼405",
    "JXLMC_EN": null,
    "KSRQ_EN": "29 December 2025",
    "KCMC_EN": "Management Information Systems"
  }
]
```

### 字段说明
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| KCDM | string | 课程代码 | "2071004" |
| KCMC | string | 课程名称 | "管理信息系统" |
| KCMC_EN | string | 课程英文名称 | "Management Information Systems" |
| KSSJDMC | string | 考试时间点名称（考试类型） | "期末"/"期中" |
| KSRQ | string | 考试日期 | "2025-12-29" |
| KSRQ2 | string | 考试日期简短格式 | "12月29日" |
| KSRQ_EN | string | 考试日期英文 | "29 December 2025" |
| KSJTSJ | string | 考试具体时间 | "16:00-18:00" |
| XQJMC | string | 星期几名称 | "星期一" |
| DJZ | number | 第几周 | 17 |
| KSJC | number | 开始节次 | 8 |
| JSJC | number | 结束节次 | 10 |
| JXLMC | string | 教学楼名称 | "逸夫楼" |
| JXCDMC | string | 教学场地名称（教室） | "逸夫楼405" |
| XIAOQUBMC | string | 校区名称 | "校本部" |
| XNXQMC | string | 学年学期名称 | "2025-2026-1" |
| YHID | string | 用户ID（学号） | "U202412345" |
| KSHKID | string | 考试环节ID（UUID） | "c0fd7638-..." |
| JKJSBZ | string | 监考教师备注 | "" |
| PYLX | string | 培养类型 | "1"=本科 |
| CDDM | string | 场地代码 | "0238" |

### 本地API封装

**端点**: `GET /schedule/exams`

**响应格式**:
```json
[
  {
    "course_code": "2071004",
    "course_name": "管理信息系统",
    "course_name_en": "Management Information Systems",
    "exam_type": "期末",
    "exam_date": "2025-12-29",
    "exam_date_display": "12月29日",
    "exam_time": "16:00-18:00",
    "weekday": "星期一",
    "week_number": 17,
    "start_period": 8,
    "end_period": 10,
    "building": "逸夫楼",
    "room": "逸夫楼405",
    "campus": "校本部",
    "term": "2025-2026-1",
    "remark": ""
  }
]
```

---

## 10. 校园网管理接口

### 10.1 校园网登录 (VPN模式)

#### 接口信息
- **本地API**: `POST /api/wifi/login`
- **上游接口**: 
  - `https://elib.ustb.edu.cn/login` (WebVPN登录)
  - `https://elib.ustb.edu.cn/http-8080/.../LoginAction.action` (校园网后台登录)

#### 认证流程
1. 访问 elib.ustb.edu.cn/login 获取 VPN cookie
2. 提取 captcha_id，POST 到 do-login 完成 VPN 登录
3. 访问代理后的校园网登录页，获取 checkcode
4. 密码 MD5 加密后 POST 到 LoginAction.action

#### 请求参数
```json
{
  "password": "校园网密码"
}
```

#### 响应示例
```json
{
  "success": true,
  "message": "登录成功"
}
```

### 10.2 流量查询

#### 接口信息
- **本地API**: `GET /api/wifi/flow`
- **上游接口**: `http://202.204.48.66:801/eportal/portal/visitor/loadUserFlow`
  - VPN代理: `https://elib.ustb.edu.cn/http-801/.../eportal/portal/visitor/loadUserFlow`

#### 上游响应格式 (JSONP)
```javascript
jsonpReturn({
  "result": "success",
  "balance": "23.45",      // 余额（元）
  "flow": "1024.5",        // 已用流量（MB）
  "uptime": "2024-01-15 10:30:00"  // 更新时间
});
```

#### 本地API响应
```json
{
  "balance": 23.45,
  "used_flow": 1024.5,
  "update_time": "2024-01-15 10:30:00"
}
```

### 10.3 月度账单

#### 接口信息
- **本地API**: `GET /api/wifi/month-pay?year=2024`
- **上游接口**: `http://202.204.60.7:8080/MonthPayAction.action`
  - VPN代理: `https://elib.ustb.edu.cn/http-8080/.../MonthPayAction.action`

#### 本地API响应
```json
{
  "year_cost": 12.50,
  "year_used_duration": 86400,
  "year_used_flow": 51200.5,
  "monthly_data": [
    {
      "month": 1,
      "cost": 1.50,
      "used_duration": 7200,
      "used_flow": 5120.0
    }
  ]
}
```

### 10.4 MAC地址管理

#### 接口信息
- **获取列表**: `GET /api/wifi/mac`
- **解绑**: `POST /api/wifi/unbind-mac`
- **上游接口**: 
  - 获取: `http://202.204.60.7:8080/nav_unBandMacJsp`
  - 解绑: `http://202.204.60.7:8080/nav_unbindMACAction.action`

#### 获取MAC列表响应
```json
[
  {
    "device_name": "DESKTOP-ABC123",
    "mac_address": "AABBCCDDEE11"
  },
  {
    "device_name": "iPhone",
    "mac_address": "112233445566"
  }
]
```

#### 解绑请求
```json
{
  "macs_to_keep": ["AABBCCDDEE11"]  // 要保留的MAC地址
}
```

### 10.5 关键说明

| 参数 | 说明 |
|------|------|
| wengine_vpn_ticketelib_ustb_edu_cn | WebVPN会话cookie |
| JSESSIONID | 校园网后台会话cookie |
| checkcode | 登录验证码（页面提取） |
| password | 需要MD5加密后传输 |

### 10.6 VPN代理URL规则
校园网API通过WebVPN访问时的URL转换规则：
- `http://202.204.60.7:8080/xxx` → `https://elib.ustb.edu.cn/http-8080/77726476706e69737468656265737421a2a713d275603c1e2858c7fb/xxx`
- `http://202.204.48.66:801/xxx` → `https://elib.ustb.edu.cn/http-801/77726476706e69737468656265737421a2a713d275603c1e2a50c7face/xxx`

---

## 11. 校园网自助服务系统接口 (zifuwu.ustb.edu.cn)

### 11.1 Dashboard 账户信息刷新

#### 接口信息
- **URL**: `GET /Self/dashboard/refreshaccount`
- **WebVPN URL**: `https://elib.ustb.edu.cn/https/77726476706e69737468656265737421eafe4789302526456d1c8be29d51367b8ada/Self/dashboard/refreshaccount`
- **用途**: 刷新账户信息（余额、流量等）

#### 请求参数
```
csrftoken=a1aa1c8f-7bc8-4a28-9326-1dd8ced6264e  # CSRF令牌
t=0.16614107581605342                           # 时间戳（随机数）
```

#### 响应示例
```
空响应体（200 OK）
```

#### 说明
- 该接口触发服务器端刷新账户数据
- 响应为空，实际数据通过页面HTML返回
- 需要携带有效的session cookie

### 11.2 获取无感知认证类型

#### 接口信息
- **URL**: `GET /Self/dashboard/refreshMauthType`
- **WebVPN URL**: `https://elib.ustb.edu.cn/https/77726476706e69737468656265737421eafe4789302526456d1c8be29d51367b8ada/Self/dashboard/refreshMauthType`
- **用途**: 获取当前无感知认证设置

#### 请求参数
```
t=0.19038023303994478  # 时间戳（随机数）
```

#### 响应示例
```html
"<a href='dashboard/oprateMauthAction'>默认</a>"
```

#### 说明
- 返回HTML片段，显示当前无感知认证状态
- 可能的值：默认、已开启等

### 11.3 获取登录历史记录

#### 接口信息
- **URL**: `GET /Self/dashboard/getLoginHistory`
- **WebVPN URL**: `https://elib.ustb.edu.cn/https/77726476706e69737468656265737421eafe4789302526456d1c8be29d51367b8ada/Self/dashboard/getLoginHistory`
- **用途**: 获取近期上网记录

#### 请求参数
```
t=0.5942309583133506  # 时间戳
order=asc             # 排序方式
_=1769189608521       # 时间戳（毫秒）
```

#### 响应示例
```json
[
  [
    1769186736000,           // 上线时间（Unix时间戳，毫秒）
    1769188538000,           // 注销时间（Unix时间戳，毫秒）
    "115.25.60.140",         // IP地址
    "000000000000",          // MAC地址
    31,                      // 使用时长（分钟）
    0,                       // 使用流量（MB）
    2,                       // 计费方式（2=流量）
    0,                       // 计费金额
    null,                    // 主机名
    "#PC",                   // 终端类型标识
    "PC",                    // 终端类型显示名
    1                        // 记录序号
  ],
  [
    1769177006000,
    1769178809000,
    "115.25.60.144",
    "000000000000",
    31,
    0,
    2,
    0,
    null,
    "#PC",
    "PC",
    2
  ]
]
```

#### 字段说明
| 索引 | 类型 | 说明 | 示例 |
|------|------|------|------|
| 0 | number | 上线时间（Unix毫秒时间戳） | 1769186736000 |
| 1 | number | 注销时间（Unix毫秒时间戳） | 1769188538000 |
| 2 | string | IP地址 | "115.25.60.140" |
| 3 | string | MAC地址 | "000000000000" |
| 4 | number | 使用时长（分钟） | 31 |
| 5 | number | 使用流量（MB） | 0 |
| 6 | number | 计费方式（2=流量计费） | 2 |
| 7 | number | 计费金额（元） | 0 |
| 8 | string/null | 主机名 | null |
| 9 | string | 终端类型标识 | "#PC" |
| 10 | string | 终端类型显示名 | "PC" |
| 11 | number | 记录序号 | 1 |

### 11.4 获取在线设备列表

#### 接口信息
- **URL**: `GET /Self/dashboard/getOnlineList`
- **WebVPN URL**: `https://elib.ustb.edu.cn/https/77726476706e69737468656265737421eafe4789302526456d1c8be29d51367b8ada/Self/dashboard/getOnlineList`
- **用途**: 获取当前在线的设备列表

#### 请求参数
```
t=0.5942309583133506  # 时间戳
order=asc             # 排序方式
_=1769189608522       # 时间戳（毫秒）
```

#### 响应示例
```json
[]
```

#### 说明
- 返回数组格式，每个元素结构与登录历史记录相同
- 空数组表示当前无在线设备
- 如果有在线设备，格式为：
```json
[
  [
    1769189608000,      // 上线时间
    null,               // 注销时间（在线时为null）
    "115.25.60.140",    // IP地址
    "000000000000",     // MAC地址
    11,                 // 已使用时长（分钟）
    0.000,              // 已使用流量（MB）
    2,                  // 计费方式
    0,                  // 当前费用
    null,               // 主机名
    "#PC",              // 终端类型标识
    "PC",               // 终端类型
    1                   // 序号
  ]
]
```

### 11.5 关键请求头

所有接口都需要携带以下请求头：

```http
Cookie: show_vpn=0; show_faq=0; wengine_vpn_ticketelib_ustb_edu_cn={vpn_cookie}
X-Requested-With: XMLHttpRequest
Accept: application/json, text/javascript, */*; q=0.01
Referer: https://elib.ustb.edu.cn/https/77726476706e69737468656265737421eafe4789302526456d1c8be29d51367b8ada/Self/dashboard
```

### 11.6 URL编码规则

校园网自助服务系统通过WebVPN访问时的URL转换：
- 原始域名: `zifuwu.ustb.edu.cn`
- 加密后: `77726476706e69737468656265737421eafe4789302526456d1c8be29d51367b8ada`
- 完整格式: `https://elib.ustb.edu.cn/https/{加密域名}/{路径}`

### 11.7 本地API封装建议

#### 获取账户概览
```
GET /api/wifi/dashboard
```

**响应格式**:
```json
{
  "account": "U202440984",
  "balance": 0.00,
  "used_flow_v4": 0,
  "used_flow_v6": 0,
  "available_flow": 122880,
  "package": "学生用户",
  "status": "正常",
  "expire_date": "2028-09-15"
}
```

#### 获取上网记录
```
GET /api/wifi/history?limit=10
```

**响应格式**:
```json
[
  {
    "login_time": "2026-01-23 22:03:26",
    "logout_time": "2026-01-23 22:33:29",
    "ip_address": "115.25.60.144",
    "mac_address": "00-00-00-00-00-00",
    "duration_minutes": 31,
    "used_flow_mb": 0,
    "cost": 0,
    "device_type": "PC"
  }
]
```

#### 获取在线设备
```
GET /api/wifi/online-devices
```

**响应格式**:
```json
[
  {
    "login_time": "2026-01-24 00:45:36",
    "ip_address": "115.25.60.140",
    "mac_address": "00-00-00-00-00-00",
    "duration_minutes": 11,
    "used_flow_mb": 0.000,
    "device_type": "PC"
  }
]
```

### 11.8 注意事项

1. **时间戳格式**:
   - 上游接口使用Unix毫秒时间戳
   - 需要转换为可读的日期时间格式

2. **数组响应**:
   - 登录历史和在线列表返回的是数组的数组，不是对象数组
   - 需要按索引位置解析字段

3. **MAC地址格式**:
   - 上游返回12位无分隔符格式 "000000000000"
   - 建议转换为标准格式 "00-00-00-00-00-00"

4. **流量单位**:
   - 上游接口使用MB作为单位
   - 可用流量显示为整数，已用流量可能有小数

5. **CSRF保护**:
   - refreshaccount接口需要csrftoken参数
   - token可能从页面HTML中提取或从cookie中获取

### 11.9 获取绑定设备列表

#### 接口信息
- **URL**: `GET /Self/service/getMacList`
- **WebVPN URL**: `https://elib.ustb.edu.cn/https/77726476706e69737468656265737421eafe4789302526456d1c8be29d51367b8ada/Self/service/getMacList`
- **用途**: 获取当前账号绑定的所有设备

#### 请求参数
```
pageSize=100          # 每页数量
pageNumber=1          # 页码
sortName=2            # 排序字段
sortOrder=DESC        # 排序方向
_=1769280971159       # 时间戳（毫秒）
```

#### 响应示例
```json
{
  "total": 4,
  "rows": [
    ["0", "AC45CAE3E96B", "", null, null, "否", ""],
    ["0", "DA25F6BB060B", "", null, null, "否", ""],
    ["0", "76BAFB19DE9D", "", null, null, "否", ""],
    ["0", "AEB74F5FA885", "", null, null, "否", ""]
  ]
}
```

#### 字段说明（rows数组每行）
| 索引 | 类型 | 说明 | 示例 |
|------|------|------|------|
| 0 | string | 在线状态（"0"=离线, "1"=在线） | "0" |
| 1 | string | MAC地址（无分隔符） | "AC45CAE3E96B" |
| 2 | string | 终端信息 | "" |
| 3 | string/null | 最近登录时间 | null |
| 4 | string/null | 最近登录IP | null |
| 5 | string | 是否哑终端 | "否" |
| 6 | string | 终端名称 | "" |

### 11.10 解绑MAC地址

#### 接口信息
- **URL**: `GET /Self/service/unbindmac`（注意：小写）
- **WebVPN URL**: `https://elib.ustb.edu.cn/https/77726476706e69737468656265737421eafe4789302526456d1c8be29d51367b8ada/Self/service/unbindmac`
- **用途**: 解绑指定的MAC地址

#### 请求参数
```
mac=AC45CAE3E96B                              # MAC地址（无分隔符，大写）
ajaxCsrfToken=6f6df440-a263-4dc2-8a9a-xxx     # CSRF令牌（UUID格式）
```

#### 响应
- 成功：页面重定向到 `/Self/service/myMac`
- 失败：返回错误页面

#### 注意事项
- **必须使用GET请求**，不是POST
- URL路径是 `unbindmac`（全小写），不是 `unbindMac`
- ajaxCsrfToken 可以使用随机生成的UUID

### 11.11 MAC地址厂商查询（本地API）

#### 接口信息
- **本地API**: `GET /api/wifi/mac-vendor`
- **用途**: 查询MAC地址对应的设备厂商

#### 请求参数
```
mac=AC-45-CA-E3-E9-6B    # MAC地址（支持多种格式）
```

#### 响应示例
```json
{
  "vendor": "GUANGDONG OPPO MOBILE TELECOMMUNICATIONS CORP.,LTD",
  "is_random": false
}
```

#### 随机MAC地址响应
```json
{
  "vendor": "随机MAC",
  "is_random": true
}
```

#### 说明
- 使用离线IEEE OUI数据库（约38000条记录）
- 自动识别随机MAC地址（iOS/Android隐私保护功能生成）
- 随机MAC地址特征：第一字节的第二位为1（本地管理地址）

---

## 12. 选课管理接口

### 12.1 获取选课当前学年学期

#### 接口信息
- **URL**: `POST /Xsxk/queryXkdqXnxq`
- **用途**: 获取选课系统当前学年学期及相关参数

#### 请求参数
```
cxsfmt=0&p_pylx=1&mxpylx=1&p_sfgldjr=0&p_sfredis=0&p_sfsyxkgwc=0&p_xktjz=&p_chaxunxh=&p_gjz=&p_skjs=&p_xn=&p_xq=&p_xnxq=&p_dqxn=&p_dqxq=&p_dqxnxq=&p_xkfsdm=&p_xiaoqu=&p_kkyx=&p_kclb=&p_xkxs=&p_dyc=&p_kkxnxq=&p_id=&p_sfhlctkc=0&p_sfhllrlkc=0&p_kxsj_xqj=&p_kxsj_ksjc=&p_kxsj_jsjc=&p_kcdm_js=&p_kcdm_cxrw=&p_kcdm_cxrw_zckc=&p_kc_gjz=&p_xzcxtjz_nj=&p_xzcxtjz_yx=&p_xzcxtjz_zy=&p_xzcxtjz_zyfx=&p_xzcxtjz_bj=&p_sfxsgwckb=1&p_skyy=&p_sfmxzj=0
```

#### 响应示例
```json
{
  "p_xn": "2025-2026",
  "p_dqxnxq": "2025-20261",
  "p_dqxn": "2025-2026",
  "p_xq": "2",
  "p_dqxq": "1",
  "p_xnxq": "2025-20262",
  "cxsfmt": "1"
}
```

#### 字段说明
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| p_xn | string | 选课学年 | "2025-2026" |
| p_xq | string | 选课学期 | "2" |
| p_xnxq | string | 选课学年学期（拼接格式） | "2025-20262" |
| p_dqxn | string | 当前学年 | "2025-2026" |
| p_dqxq | string | 当前学期 | "1" |
| p_dqxnxq | string | 当前学年学期 | "2025-20261" |
| cxsfmt | string | 查询是否满条 | "1" |

### 12.2 获取开课学期列表

#### 接口信息
- **URL**: `POST /Xsxk/queryKkxqList`
- **用途**: 获取可供选课的学期列表

#### 响应示例
```json
[
  {"dm": "2025-20262", "mc": "2025-2026-2"},
  {"dm": "2025-20261", "mc": "2025-2026-1"},
  {"dm": "2024-20253", "mc": "2024-2025-3"}
]
```

### 12.3 获取已选课程列表 ⭐

#### 接口信息
- **URL**: `POST /Xsxk/queryYxkc`
- **用途**: 获取学生已选课程的详细列表

#### 请求参数
```
cxsfmt=1
p_pylx=1                  # 培养类型（1=本科）
mxpylx=1                  # 明细培养类型
p_sfgldjr=0               # 是否过滤掉仅任
p_sfredis=0               # 是否使用Redis
p_sfsyxkgwc=0             # 是否使用选课功能
p_xktjz=                  # 选课条件组
p_chaxunxh=               # 查询学号
p_gjz=                    # 关键字
p_skjs=                   # 上课教师
p_xn=2025-2026            # 学年
p_xq=2                    # 学期
p_xnxq=2025-20262         # 学年学期
p_dqxn=2025-2026          # 当前学年
p_dqxq=1                  # 当前学期
p_dqxnxq=2025-20261       # 当前学年学期
p_xkfsdm=yixuan           # 选课方式代码（yixuan=已选）
p_xiaoqu=                 # 校区
p_kkyx=                   # 开课学院
p_kclb=                   # 课程类别
p_xkxs=                   # 选课学时
p_dyc=                    # 大一层
p_kkxnxq=                 # 开课学年学期
p_id=                     # ID
p_sfhlctkc=0              # 是否忽略冲突课程
p_sfhllrlkc=0             # 是否忽略容量课程
p_kxsj_xqj=               # 空闲时间-星期几
p_kxsj_ksjc=              # 空闲时间-开始节次
p_kxsj_jsjc=              # 空闲时间-结束节次
p_kcdm_js=                # 课程代码_教师
p_kcdm_cxrw=              # 课程代码_查询任务
p_kcdm_cxrw_zckc=         # 课程代码_查询任务_主课程
p_kc_gjz=                 # 课程关键字
p_xzcxtjz_nj=             # 限制查询条件_年级
p_xzcxtjz_yx=             # 限制查询条件_院系
p_xzcxtjz_zy=             # 限制查询条件_专业
p_xzcxtjz_zyfx=           # 限制查询条件_专业方向
p_xzcxtjz_bj=             # 限制查询条件_班级
p_sfxsgwckb=1             # 是否学生功能查看课表
p_skyy=                   # 上课语言
p_sfmxzj=                 # 是否明细增加
p_chaxunxkfsdm=           # 查询选课方式代码
```

#### 响应示例
```json
{
  "xkgwcList": [],
  "xkgl_xscxtj_sfyxhlctkc": {...},
  "kbjclist": [...],
  "yxkcList": [
    {
      "xh": "U202412345",
      "rwh": "2025-2026-2-M360050-001",
      "kxh": "001",
      "kcdm": "M360050",
      "kcmc": "实用交际日语",
      "kcmc_en": null,
      "kcxz": "4",
      "kcxzmc": "任选",
      "kclb": "2301",
      "kclbmc": "外语(素质拓展)",
      "xf": "2.0",
      "xs": "32.0",
      "xkfsdm": "mooc-b-b",
      "xkfsmc": "MOOC",
      "kkyx": "15",
      "kkyxmc": "教务处",
      "xiaoqu": "01",
      "xiaoqumc": "校本部",
      "zrl": "200",
      "yxzrs": "1532",
      "xksj": "2026-01-08 15:07:47",
      "dgjsmc": "张丙戈",
      "rwmc": "融优学堂--实用交际日语",
      "sksj": null,
      "skdd": null,
      "pkjgmx": "<div>...</div>",
      "xkbj": "0",
      "cqzt": "0",
      "sfxyjf": "0",
      "sfxysh": "0",
      "ktxkkssj": "2026-01-08 11:00:00",
      "ktxkjssj": "2026-01-15 23:59:00",
      "kcxx": "<p>...</p>"
    },
    {
      "xh": "U202412345",
      "rwh": "2025-2026-2-4071014-001",
      "kxh": "001",
      "kcdm": "4071014",
      "kcmc": "高级语言程序设计",
      "kcmc_en": "Advanced Language programming",
      "kcxz": "1",
      "kcxzmc": "必修",
      "kclb": "21",
      "kclbmc": "专业核心",
      "xf": "3.0",
      "xs": "48.0",
      "xkfsdm": "bx-b-b",
      "xkfsmc": "必修",
      "kkyx": "07",
      "kkyxmc": "经济管理学院",
      "xiaoqu": "01",
      "xiaoqumc": "校本部",
      "zrl": "69",
      "yxzrs": "63",
      "xksj": "2026-01-08 15:07:11",
      "dgjsmc": "袁帅鹏",
      "sksj": null,
      "skdd": null,
      "pkjgmx": "<div>上课时间地点HTML...</div>",
      "xkbj": "0",
      "sxbj": "1"
    }
  ]
}
```

#### 核心字段说明（yxkcList数组）
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| xh | string | 学号 | "U202412345" |
| rwh | string | 任务号（唯一标识） | "2025-2026-2-4071014-001" |
| kxh | string | 课序号 | "001" |
| kcdm | string | 课程代码 | "4071014" |
| kcmc | string | 课程名称 | "高级语言程序设计" |
| kcmc_en | string | 课程英文名称 | "Advanced Language programming" |
| kcxz | string | 课程性质代码 | "1"=必修, "4"=任选 |
| kcxzmc | string | 课程性质名称 | "必修"/"任选" |
| kclb | string | 课程类别代码 | "21" |
| kclbmc | string | 课程类别名称 | "专业核心" |
| xf | string | 学分 | "3.0" |
| xs | string | 学时 | "48.0" |
| xkfsdm | string | 选课方式代码 | "bx-b-b"/"mooc-b-b" |
| xkfsmc | string | 选课方式名称 | "必修"/"MOOC" |
| kkyx | string | 开课学院代码 | "07" |
| kkyxmc | string | 开课学院名称 | "经济管理学院" |
| xiaoqu | string | 校区代码 | "01" |
| xiaoqumc | string | 校区名称 | "校本部" |
| zrl | string | 总容量 | "69" |
| yxzrs | string | 已选总人数 | "63" |
| xksj | string | 选课时间 | "2026-01-08 15:07:11" |
| dgjsmc | string | 主讲教师 | "袁帅鹏" |
| rwmc | string | 任务名称（展示名称） | "融优学堂--实用交际日语" |
| pkjgmx | string | 排课结果明细（上课时间地点HTML） | `<div>...</div>` |
| kcxx | string | 课程详细信息HTML | `<p>...</p>` |
| xkbj | string | 选课标记 | "0" |
| cqzt | string | 抽签状态 | "0"=未抽签, "2"=待抽签 |
| sxbj | string | 筛选标记 | "1"=已选中 |
| sfxyjf | string | 是否需要缴费 | "0"/"1" |
| sfxysh | string | 是否需要审核 | "0"/"1" |
| ktxkkssj | string | 可退选课开始时间 | "2026-01-08 11:00:00" |
| ktxkjssj | string | 可退选课结束时间 | "2026-01-15 23:59:00" |

### 12.4 获取周次节次列表

#### 接口信息
- **URL**: `POST /Xsxktz/queryXlcxList`
- **用途**: 获取选课系统的周次和节次信息

#### 响应示例
```json
{
  "jclist": [
    {"XJMS": "第一小节", "XJ": "1", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"},
    {"XJMS": "第二小节", "XJ": "2", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"},
    {"XJMS": "第三小节", "XJ": "3", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"},
    {"XJMS": "第四小节", "XJ": "4", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"},
    {"XJMS": "第五小节", "XJ": "5", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"},
    {"XJMS": "第六小节", "XJ": "6", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"},
    {"XJMS": "第七小节", "XJ": "7", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"},
    {"XJMS": "第八小节", "XJ": "8", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"},
    {"XJMS": "第九小节", "XJ": "9", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"},
    {"XJMS": "第十小节", "XJ": "10", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"},
    {"XJMS": "第十一小节", "XJ": "11", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"},
    {"XJMS": "第十二小节", "XJ": "12", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"},
    {"XJMS": "第十三小节", "XJ": "13", "KSKSSJ": null, "KSJSSJ": null, "JSKZ": "1"}
  ],
  "zclist": [
    {"ZC": "1"}, {"ZC": "2"}, {"ZC": "3"}, {"ZC": "4"},
    {"ZC": "5"}, {"ZC": "6"}, {"ZC": "7"}, {"ZC": "8"},
    {"ZC": "9"}, {"ZC": "10"}, {"ZC": "11"}, {"ZC": "12"},
    {"ZC": "13"}, {"ZC": "14"}, {"ZC": "15"}, {"ZC": "16"},
    {"ZC": "17"}, {"ZC": "18"}
  ]
}
```

#### 字段说明
| 字段 | 类型 | 说明 |
|------|------|------|
| jclist | array | 节次列表 |
| jclist[].XJMS | string | 小节名称 |
| jclist[].XJ | string | 小节序号 |
| jclist[].JSKZ | string | 节数控制 |
| zclist | array | 周次列表 |
| zclist[].ZC | string | 周次 |

### 12.5 获取开课学院列表

#### 接口信息
- **URL**: `POST /component/queryKkyx`
- **用途**: 获取所有开课学院

#### 响应示例
```json
{
  "code": 200,
  "content": [
    {"dm": "01", "mc": "土木与资源工程学院"},
    {"dm": "02", "mc": "冶金与生态工程学院"},
    {"dm": "03", "mc": "材料科学与工程学院"},
    {"dm": "07", "mc": "经济管理学院"},
    {"dm": "09", "mc": "外国语学院"},
    {"dm": "15", "mc": "教务处"}
  ]
}
```

### 12.6 获取课程类别列表

#### 接口信息
- **URL**: `POST /component/queryDmb`
- **用途**: 获取课程类别代码表

#### 请求参数
```
dmbmc=kclb    # 代码表名称（kclb=课程类别）
```

#### 响应示例
```json
{
  "code": 200,
  "content": [
    {"dm": "18", "mc": "国防公益"},
    {"dm": "19", "mc": "通识课程"},
    {"dm": "20", "mc": "学科平台"},
    {"dm": "21", "mc": "专业核心"},
    {"dm": "23", "mc": "素质拓展"},
    {"dm": "2301", "mc": "外语(素质拓展)"},
    {"dm": "2302", "mc": "美育(素质拓展)"},
    {"dm": "2303", "mc": "自主选修(素质拓展)"},
    {"dm": "55", "mc": "专业拓展"}
  ]
}
```

### 12.7 获取校区列表

#### 接口信息
- **URL**: `POST /component/queryXiaoqu`
- **参数**: `pylx=3` (培养类型)

#### 响应示例
```json
{
  "code": 200,
  "content": [
    {"dm": "01", "mc": "校本部"},
    {"dm": "02", "mc": "管庄校区"},
    {"dm": "03", "mc": "顺德研究生院"}
  ]
}
```

### 12.8 获取课表节次结构

#### 接口信息
- **URL**: `POST /component/queryKbjg`
- **用途**: 获取课表的节次结构（大节和小节映射）

#### 响应示例
```json
{
  "code": 200,
  "content": [
    {"XJMS": "第一小节", "XJ": 1, "DJ": 1, "DJMS": "第一大节"},
    {"XJMS": "第二小节", "XJ": 2, "DJ": 1, "DJMS": "第一大节"},
    {"XJMS": "第三小节", "XJ": 3, "DJ": 2, "DJMS": "第二大节"},
    {"XJMS": "第四小节", "XJ": 4, "DJ": 2, "DJMS": "第二大节"},
    {"XJMS": "第五小节", "XJ": 5, "DJ": 3, "DJMS": "第三大节"},
    {"XJMS": "第六小节", "XJ": 6, "DJ": 3, "DJMS": "第三大节"},
    {"XJMS": "第七小节", "XJ": 7, "DJ": 4, "DJMS": "第四大节"},
    {"XJMS": "第八小节", "XJ": 8, "DJ": 4, "DJMS": "第四大节"},
    {"XJMS": "第九小节", "XJ": 9, "DJ": 5, "DJMS": "第五大节"},
    {"XJMS": "第十小节", "XJ": 10, "DJ": 5, "DJMS": "第五大节"},
    {"XJMS": "第十一小节", "XJ": 11, "DJ": 6, "DJMS": "第六大节"},
    {"XJMS": "第十二小节", "XJ": 12, "DJ": 6, "DJMS": "第六大节"},
    {"XJMS": "第十三小节", "XJ": 13, "DJ": 7, "DJMS": "第七大节"}
  ]
}
```

#### 字段说明
| 字段 | 类型 | 说明 |
|------|------|------|
| XJ | number | 小节序号 |
| XJMS | string | 小节名称 |
| DJ | number | 大节序号 |
| DJMS | string | 大节名称 |

### 12.9 选课方式代码对照表

| 代码 | 名称 | 说明 |
|------|------|------|
| bx-b-b | 必修 | 培养方案中的必修课程，直接选中 |
| mooc-b-b | MOOC | 在线课程（慕课） |
| sztzk | 素质拓展课 | 素质拓展选修课 |
| zytzk | 专业拓展课 | 专业拓展选修课 |
| ggkrw | 公共课任务 | 公共选修课 |
| yixuan | 已选 | 查询已选课程时使用 |

### 12.10 选课状态说明

| 字段 | 值 | 说明 |
|------|------|------|
| xkbj | "0" | 正常选课状态 |
| xkbj | "1" | 预选状态 |
| cqzt | "0" | 不需要抽签 |
| cqzt | "2" | 待抽签（选课人数超过容量） |
| sxbj | "1" | 已选中 |
| sfxyjf | "0" | 不需要缴费 |
| sfxyjf | "1" | 需要缴费 |
| sfxysh | "0" | 不需要审核 |
| sfxysh | "1" | 需要审核 |

### 12.11 接口依赖关系

#### 选课查询流程
1. **登录认证** → 获取session cookie
2. **获取当前学期** (`/Xsxk/queryXkdqXnxq`) → 确定选课学年学期
3. **获取筛选条件**（可选）
   - `/component/queryKkyx` → 开课学院列表
   - `/component/queryDmb?dmbmc=kclb` → 课程类别列表
   - `/component/queryXiaoqu?pylx=3` → 校区列表
4. **查询已选课程** (`/Xsxk/queryYxkc`) → 获取学生已选课程

#### 本地API封装建议

```
GET /api/course-selection/current-term
GET /api/course-selection/selected-courses?xnxq=2025-20262
GET /api/course-selection/colleges
GET /api/course-selection/categories
GET /api/course-selection/campuses
```

**已选课程响应格式建议**:
```json
{
  "term": "2025-2026-2",
  "total_credits": 28.5,
  "courses": [
    {
      "task_id": "2025-2026-2-4071014-001",
      "course_code": "4071014",
      "course_name": "高级语言程序设计",
      "course_name_en": "Advanced Language programming",
      "course_type": "必修",
      "category": "专业核心",
      "credits": 3.0,
      "hours": 48,
      "teacher": "袁帅鹏",
      "college": "经济管理学院",
      "campus": "校本部",
      "capacity": 69,
      "enrolled": 63,
      "select_time": "2026-01-08 15:07:11",
      "select_method": "必修",
      "schedule_html": "<div>...</div>",
      "status": {
        "lottery": false,
        "need_pay": false,
        "need_approve": false,
        "can_drop": true,
        "drop_deadline": "2026-01-15 23:59:00"
      }
    }
  ]
}
```

