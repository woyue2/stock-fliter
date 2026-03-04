---
name: impl_quality
description: |
  实现质量内联 Skill。
  在 /implement 结束前，自动内联执行 review 自检 + sync_doc 文档检查。
  包含：代码品味自检、Next.js 前端规范、FastAPI 后端规范、日志规范、GEB 文档同步检查。
  目标：把原来需要 3 个回合（implement + review + sync_doc）压缩为 1 个回合。
---

# Impl Quality Skill — 实现质量内联

本 Skill 通过 `/implement` Step 0 显式加载后生效。
加载后，在代码写完前自动过以下所有检查，实现末尾附上检查报告。
用户不需要单独调用 `/review` 或 `/sync_doc`。
**检查报告的最终输出格式以 `implement.md` 为准。**

---

## 内联执行顺序

```
1. 写代码（正常 implement）
2. [自动] 品味自检 → 代码层面（前后端通用）
3. [自动] Next.js 前端规范检查（如果涉及 frontend/）
4. [自动] FastAPI 后端规范检查（如果涉及 backend/）
5. [自动] GEB 文档检查（FATAL 拦截 + SEVERE 提示）
6. 输出：代码 + 末尾附检查报告
```

---

## 品味自检（代码层面，implement 完成后自动执行）

以 Linus 的眼光过一遍，每项标记 ✅/⚠️/❌：

```yaml
品味检查项:
  函数长度:
    规则: 每个函数 ≤ 20 行
    违反: 提取子函数，说明提取理由

  嵌套深度:
    规则: ≤ 3 层缩进
    违反: 提前 return 或提取函数消除

  分支数量:
    规则: 同一函数 if/else ≤ 3 个
    违反: 用数据驱动或策略模式替换

  重复代码:
    规则: 相同逻辑不允许出现 2 次以上
    违反: 提取公共函数

  命名质量:
    规则: 变量/函数名能说明意图，不需要注释才能理解
    违反: 重命名并解释

  副作用:
    规则: 函数不应有隐式副作用
    违反: 标注 [UNCERTAIN] 并告警
```

---

## FastAPI 后端规范（涉及 backend/ 时自动检查）

### 目录结构约束（可长期演进）

```
app/
├── main.py                # 入口，只做 app 挂载
├── core/                  # 全局配置（config, security, logging）
├── api/v1/endpoints/      # 路由层（只做 HTTP 转发，不写业务）
├── schemas/               # Pydantic 请求/响应模型
├── services/              # 业务逻辑层（核心，唯一写业务的地方）
├── models/                # ORM 模型
├── db/                    # 数据库 session
└── dependencies/          # FastAPI 依赖注入
```

### 路由层铁律

```
❌ 禁止在 endpoints/ 里写业务逻辑
❌ 禁止在 endpoints/ 里直接操作数据库
✅ endpoints/ 只做：参数验证 → 调用 service → 返回响应
```

### API 版本管理

```
✅ 使用 APIRouter + 前缀分组（/api/v1/）
❌ 不在生产环境暴露 /docs（Swagger UI）
✅ 保留 /openapi.json 供工具使用
```

---

## 日志规范（涉及任何节点/服务时自动检查）

### 禁止行为

```
❌ 在节点/服务层混用 print（可观测性不一致）
❌ 异常被 except 吞掉不打印（定位问题会极难）
❌ 失败时直接返回空结果而不记录原因
```

### 正确做法

```python
# ✅ 使用项目已有 logger（继承根 logger，不重新创建）
import logging
logger = logging.getLogger(__name__)

# ✅ 结构化日志：记录关键上下文
logger.info("开始抓取", extra={"url": url, "cookie_count": len(cookies)})
logger.warning("无新增内容", extra={"scroll_count": n})
logger.error("抓取失败", exc_info=True)  # exc_info=True 打印完整堆栈

# ✅ 异常必须打印堆栈，不能只返回空
try:
    result = crawl()
except Exception as e:
    logger.error("节点执行失败: %s", e, exc_info=True)
    return {}  # 返回空可以，但必须先 logger.error
```

### 覆盖要求

```
必须覆盖的关键上下文（抓不到信息=排障失败）：
  - 入口参数（URL、Cookie 数量、请求体摘要）
  - 关键中间结果（解析条数、滚动次数）
  - 最终输出（返回条数、耗时）
  - 所有 except 分支（必须有 exc_info=True）
```

---

## Next.js 前端规范（涉及 frontend/ 时自动检查）

### Server / Client 组件边界（最重要）

```
核心原则：'use client' 边界尽量推迟到叶子节点

✅ 默认写 Server Component（无 'use client'）
✅ 只有以下情况才加 'use client'：
   - 使用 useState / useReducer / useRef
   - 使用 useEffect / 事件监听
   - 使用浏览器 API（window, localStorage 等）
   - 需要动态导入且 ssr: false

❌ 禁止在 Server Component 里 import 带副作用的客户端模块
❌ 禁止把 'use client' 标注在根 layout.tsx（污染整棵树）

本项目约定：
  - layout.tsx       → Server Component（不加 'use client'）
  - page.tsx         → 根据是否有交互决定（有则加）
  - components/      → 尽量 Server，交互子组件单独加 'use client'
  - store.ts / hooks → 必须 'use client'
```

### 组件设计约束

```yaml
组件大小:
  规则: 单个 .tsx 文件 ≤ 150 行（含 JSX）
  违反: 把独立 UI 块提取为 components/ 子组件

Props 接口:
  规则: 每个组件必须有明确的 Props 类型定义
  违反: 补充 interface XxxProps { ... } 并应用
  示例:
    ✅ function ActionBtn({ icon, label }: ActionBtnProps)
    ❌ function ActionBtn(props: any)

单一职责:
  规则: 组件只做一件事（展示 or 交互 or 数据获取，不混用）
  违反: 拆分为展示组件 + 容器组件

内联样式:
  规则（本项目约定）: 可以用 inline style，但超过 5 个属性的样式块
             必须提取为具名常量或 CSS Module
  违反:
    ❌ style={{ ...20个属性... }}（直接在 JSX 里）
    ✅ const cardStyle: React.CSSProperties = { ...20个属性... }
       <div style={cardStyle}>
```

### TypeScript 严格约束

```
❌ 禁止使用 any（包括 as any）
   替代：用 unknown + 类型收窄，或补充正确接口

❌ 禁止隐式 undefined（不能假设值一定存在）
   替代：用可选链 ?. 或提前判断

✅ 所有 API 响应必须有对应的 TypeScript 接口
✅ 组件 Props 必须有接口定义（不允许内联匿名类型超过 3 个字段）
✅ useState 的泛型必须显式标注（不能靠推断）
   示例:
     ✅ useState<Prize | null>(null)
     ❌ useState(null)  ← 类型会推断为 null，后续赋值报错
```

### React Hooks 规范

```
useEffect:
  ❌ 禁止空依赖数组糊弄（[] 只有在真正只需运行一次时才用）
  ❌ 禁止在 useEffect 里直接写异步函数（会吞错误）
  ✅ 正确的异步写法：
     useEffect(() => {
       const load = async () => { ... };
       load();
     }, [deps]);

useCallback / useMemo:
  ✅ 传给子组件的函数必须用 useCallback 包裹（避免重渲染）
  ❌ 不要过度 useMemo（简单计算不值得）

命名:
  ✅ 自定义 Hook 必须以 use 开头
  ✅ 事件处理函数必须以 handle 开头（handleSpin, handleWin）
```

### 前端日志约束

```
❌ 禁止在生产代码里留 console.log（调试完必须删）
❌ 禁止 console.log 打印完整对象（JSON.stringify 也不行）
✅ 合法使用场景（仅开发环境）：
   if (process.env.NODE_ENV === 'development') {
     console.log('[Debug]', ...);
   }

✅ 真正的错误必须用 console.error（方便 Sentry 等工具捕获）
✅ 关键业务异常应通过 Error Boundary 处理，不要悄悄吞掉
```

### Next.js App Router 约束

```
路由结构:
  ✅ 每个路由目录必须配套 loading.tsx（防止 Suspense 缺失）
  ✅ 每个路由目录必须配套 error.tsx（防止页面白屏）
  ❌ 禁止在 page.tsx 里写数据获取逻辑（抽到 Server Component 或 service 层）

导航:
  ✅ 内部跳转使用 next/link（不用 window.location.href，除非必须强制刷新）
  ✅ 动态导入使用 next/dynamic（有 SSR 问题的组件加 ssr: false）

metadata:
  ✅ 每个 page.tsx 必须导出 metadata 或 generateMetadata
  ❌ 不允许页面无标题（SEO 基本要求）
```

---

## GEB 文档检查（内联版，implement 末尾自动执行）

### FATAL 级拦截（发现即停止，必须先修复）

```
□ FATAL-001: 改了代码，有没有检查对应 L3 头部？
□ FATAL-002: 新建文件，有没有写 L3 头部注释？
□ FATAL-003: 删了文件，有没有更新 L2 成员清单？
□ FATAL-004: 新建模块目录，有没有创建 L2 CLAUDE.md？
```

### SEVERE 级提示（本次任务内修复）

```
□ SEVERE-001: L3 头部和实际代码是否一致？
□ SEVERE-002: L2 成员清单是否包含所有文件？
□ SEVERE-003: L1 目录结构是否反映了实际变化？
□ SEVERE-004: 父级链接是否完整？
```

### 文档同步动作（自动执行的写操作）

```
如果 FATAL 全部通过：
  → 自动更新涉及的 L3 文件头
  → 自动更新涉及的 L2 CLAUDE.md 成员清单
  → 如果 L1 结构有变化，自动更新 /CLAUDE.md
  → 输出：已同步文件列表
```

---

## 检查报告格式

> ⚠️ 报告的最终输出格式以 `implement.md` 的模板为准（基于 Q1-Q9 命令输出填写）。
> 以下仅为规则参考，不是输出模板。

```
---
🔍【内联质量检查报告】（基于 Q1-Q9 命令实际输出填写）

代码品味:
  □/✅ 函数长度   □/✅ 嵌套深度   □/✅ 分支数
  □/✅ 重复代码   □/✅ 命名质量   □/✅ 副作用

前端规范（如涉及 frontend/）:
  □/✅ 'use client'最小化   □/✅ Props有接口   □/✅ 无any   □/✅ 无console.log
  □/✅ 组件≤150行          □/✅ hooks规范   □/✅ 有metadata

后端规范（如涉及 backend/）:
  □/✅ 路由层无业务逻辑   □/✅ 日志结构化   □/✅ 异常有堆栈

GEB 文档:
  FATAL: □ 001 □ 002 □ 003 □ 004  → 全通过 / [编号] 拦截
  SEVERE: □ 001 □ 002 □ 003 □ 004 → 全通过 / [编号] 需修复

已同步文档: [列表或"无变化"]
---
```
