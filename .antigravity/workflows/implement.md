---
description: 代码实现 — 功能开发 或 Bug 修复（精准实现，最小副作用）
---

> 🧠 **依赖 Skill**：本工作流**必须先读取** `impl_quality` Skill（Step 0 强制执行）。
> ⚠️ **若跳过 Step 0，视为违反协议**：review + sync 将不会被内联执行。
> 实现结束后**无需单独调用 `/review` 或 `/sync_doc`**，品味自检 + GEB 文档检查已内联于末尾。

## 用途

接在 `/design` 推荐方案确认后执行。
目标：按设计方案精准实现，最小副作用，实现完成时**同步输出质量检查报告**（内联 review + sync_doc）。

---

## 模式判定（自动识别）

| 入口 | 模式 | 核心原则 |
|------|------|---------|
| 接在功能开发 `/design` 后 | **🚀 功能模式** | 按计划新建文件，修改已有文件时最小化 |
| 接在 Bug 修复 `/design` 后 | **🐛 修复模式** | 严格最小改动，不引入任何新代码逻辑 |
| 独立调用 | 请说明是"新增功能"还是"修复 Bug" | — |

---

## 🚀 功能模式（新增功能时适用）

### 实现前：Step 0 — 加载 impl_quality Skill（⚠️ 必须最先执行，不可跳过）

> 这一步是让实现质量规则真正进入上下文。若跳过，后续品味自检和 GEB 文档检查将形同虚设。

// turbo
**Step 0: 加载 impl_quality Skill（进入任何代码操作之前）**
CommandLine: type .antigravity\skills\impl_quality\SKILL.md

---

### 实现前：GEB 逆向流（进入代码前必读）

在写任何代码之前，**先读文档，让文档告诉你现有的契约**：

// turbo
**逆向流 Step 1: 读取目标目录的 L2 文档（不可跳过）**
CommandLine: if exist frontend\src\CLAUDE.md (type frontend\src\CLAUDE.md) else (echo "[MISSING L2] frontend/src/CLAUDE.md 不存在，实现完成后需创建")

// turbo
**逆向流 Step 2: 读取后端目录的 L2 文档**
CommandLine: if exist backend\CLAUDE.md (type backend\CLAUDE.md) else (echo "[MISSING L2] backend/CLAUDE.md 不存在，实现完成后需创建")

// turbo
**逆向流 Step 3: 确认目标文件当前 L3 头部状态**
CommandLine: git diff --name-only HEAD

> 📋 对照上方命令输出：
> - `[MISSING L2]` → 标记，实现完成后立即补充（FATAL-004）
> - 现有文件已列出 → 实现前先理解其 L3 契约（INPUT/OUTPUT/POS），再动手



---

### 实现前：文件计划声明

**在写任何代码之前**，先声明：

```
📋【实现计划】

新建文件:
  - frontend/src/app/[route]/page.tsx    ← [原因]
  - backend/routers/[module].py          ← [原因]

修改文件:
  - frontend/src/app/layout.tsx          ← [修改原因，改动范围描述]
  - backend/main.py                      ← [修改原因，改动范围描述]

不会改动:
  - [其他相关文件名]                     ← 明确排除，避免误改
```

等待确认后再开始编码。

### 实现时：代码规则

```yaml
新建文件:
  ✅ 按 design.md 推荐方案新建所需文件
  ✅ 文件顶部 **必须** 插入 L3 契约头部（否则触发 FATAL-002）：
     ```ts
     /**
      * [INPUT]:    依赖 {模块} 的 {具体能力}
      * [OUTPUT]:   对外提供 {导出的函数/组件/类型}
      * [POS]:      {所属模块} 的 {角色定位}，被 {谁} 消费
      * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
      */
     ```
     Python 版本：
     ```python
     """
     [INPUT]:    依赖 {模块} 的 {具体能力}
     [OUTPUT]:   对外提供 {函数/类/常量}
     [POS]:      {所属模块} 的 {角色定位}
     [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
     """
     ```

修改已有文件:
  ✅ 改动范围限制在 design 方案描述的范围内
  ✅ 每处修改用注释标注原因：
     # [IMPL] 原因: 为支持 X 功能，新增此路由
     // [IMPL] 原因: 将 props 传入子组件以实现 Y

  ❌ 不顺带修改"看不顺眼"的代码
  ❌ 不重命名与本次功能无关的变量/函数
  ❌ 不调整无关代码的格式/缩进

新增依赖:
  ✅ 如果功能本身必须引入新依赖，可以引入
  ✅ 但必须先声明：
     "需要引入 [库名 vX.X.X]，用途：[具体用途]，是否同意？"
  ❌ 不引入可以用现有依赖替代的新库
```

---

## 🐛 修复模式（Bug 修复时适用）

### 实现前：Step 0 — 加载 impl_quality Skill（⚠️ 必须最先执行，不可跳过）

> 与功能模式完全相同，修复模式也必须先加载 Skill，否则末尾的品味自检和 GEB 检查不会被执行。

// turbo
**Step 0: 加载 impl_quality Skill（进入任何代码操作之前）**
CommandLine: type .antigravity\skills\impl_quality\SKILL.md

---

### 实现前：变更范围声明

```
📋【修复计划】

修改文件:
  - [文件路径]   ← 修复：[对应 debug.md 中的哪条根因]

不会改动:
  - [其他文件]   ← 明确排除
```

### 实现时：代码规则

```yaml
修改范围:
  ✅ 只修改 debug.md 根因分析指向的位置
  ✅ 每处改动标注原因（与根因对应）：
     # [FIX] 根因: 未校验空值，导致 TypeError
     // [FIX] 根因: 异步请求未等待，导致状态竞争

  ❌ 绝对不新增与修复无关的逻辑
  ❌ 绝对不重构周边代码（哪怕它写得很烂）
  ❌ 绝对不引入新依赖

不确定的地方:
  ✅ 在代码注释中明确标出：
     # [UNCERTAIN] 不确定此处是否还有调用方，需人工确认
```

---

## 两种模式共同规则

### 1. 不确定项处理

```
如果有不确定的地方（无论功能还是修复），必须：
  1. 在代码中注释标出：[UNCERTAIN] + 描述不确定什么
  2. 在实现完成后的输出中，单独列出所有 [UNCERTAIN] 条目
  3. 不要"猜测"后默默实现，猜测结果必须显式声明
```

### 2. 关于优化/重构/新依赖的处理

```
发现需要优化/重构/引入新依赖时，统一格式：

💡【建议】（不阻塞当前实现）
  类型:  [优化 / 重构 / 新依赖]
  位置:  [文件路径:行号]
  描述:  [发现了什么问题，建议怎么处理]
  优先级: [高 / 中 / 低]
  是否同意引入？（是/否）

  → 未收到同意前，继续按原有方式实现，不做任何改动
```

### 3. 注释格式规范

```
[IMPL]      ← 新增功能：标注在功能相关的新代码旁
[FIX]       ← Bug 修复：标注在修复相关的改动旁
[UNCERTAIN] ← 不确定：标注在需要人工确认的地方
[TODO]      ← 遗留：标注在已知但暂不处理的问题
```

---

## ⚡ 实现完成后：强制质量检查（// turbo，不可跳过）

> ⚠️ **以下步骤必须在输出"实现完成"报告之前全部执行。**
> 有命令输出 = 有证据。跳过任何一步 = 违反协议。

---

### 🔍 前端检查（涉及 frontend/ 时执行）

// turbo
**Q1: ESLint 静态检查**
CommandLine: cd frontend && npx next lint --quiet 2>&1 | head -50

// turbo
**Q2: TypeScript 类型检查**
CommandLine: cd frontend && npx tsc --noEmit 2>&1 | head -50

// turbo
**Q3: 扫描遗留 console.log（生产禁用）**
CommandLine: grep -rn "console\.log" frontend/src --include="*.tsx" --include="*.ts" | grep -v "NODE_ENV"

> - Q1/Q2 有新增 ERROR → **必须修复后才能继续**（存量旧 warning 可标注跳过）
> - Q3 有输出 → 逐条确认是否为调试遗留，若是则删除

---

### 🔍 后端检查（涉及 backend/ 时执行）

// turbo
**Q4: Python 语法检查（所有 .py 文件）**
CommandLine: find backend/ -name "*.py" -exec python -m py_compile {} + 2>&1 && echo "[OK] syntax pass"

// turbo
**Q5: 扫描裸 print（生产禁用）**
CommandLine: grep -rn "^\s*print(" backend/ --include="*.py"

> - Q4 有报错 → **必须修复**
> - Q5 有输出 → 替换为 `logger.info/warning/error`

---

### 🔍 GEB 文档检查（每次必执行）

// turbo
**Q6: 查看本次变更文件清单（含未暂存的新文件）**
CommandLine: git diff --name-only HEAD && git ls-files --others --exclude-standard

// turbo
**Q7: 筛选需要 L3 头部检查的代码文件**
CommandLine: (git diff --name-only HEAD && git ls-files --others --exclude-standard) | grep -E "\.(tsx|ts|py)$"

> 对照 Q7 的输出，逐文件确认：
> - ✅ 有 `[INPUT]/[OUTPUT]/[POS]/[PROTOCOL]` 头部 → FATAL-002 通过
> - ❌ 缺失 → 立即补充，**不得继续**

// turbo
**Q8: 检查 L2 文档最后更新时间（判断是否需要同步）**
CommandLine: git log -1 --format="%ar" -- frontend/CLAUDE.md backend/CLAUDE.md 2>&1

> Q8 输出时间 > 当前改动时间 → 需要更新 L2 文档（SEVERE-002 / FATAL-003）

// turbo
**Q9: 检查 L1 根 CLAUDE.md 最后更新时间（⚠️ 最容易被遗忘的 SEVERE-003）**
CommandLine: git log -1 --format="%ar %s" -- CLAUDE.md

// turbo
**Q9b: 对照实际目录结构（看是否有新目录未录入 CLAUDE.md）**
CommandLine: Get-ChildItem -Path . -Directory -Depth 0 | Select-Object -ExpandProperty Name

> **Q9 判断规则（逐一核对）**：
> 对比 Q9b 的实际目录列表 vs `CLAUDE.md` 里目录结构图的条目：
> - 有新目录未在 CLAUDE.md 里出现 → **SEVERE-003，触发 Q10**
> - 有目录描述过时 → **SEVERE-003，触发 Q10**
> - 全部一致 → ✅ L1 通过，跳过 Q10

---

### ⛔ Q10: GEB 正向流强制修复（检测到 L1/L2 过时时执行，不是可选的）

> **谁来守护 CLAUDE.md？—— Q10。**
> 检测（Q6-Q9）发现问题后，如果不修复就输出报告，等于协议失效。
> Q10 是"牙齿"：检测到即修复，修复完才能继续。

```
Q10 触发条件（任一命中即执行）：
  - Q8 显示 L2 文档早于本次代码改动 → 更新 L2
  - Q9 显示 L1 目录结构不一致 → 更新 L1
  - Q7 显示有新文件缺少 L3 头部 → 补写 L3

Q10 执行动作（不是建议，是强制写操作）：
  1. 立即打开对应的 CLAUDE.md 或文件头部
  2. 执行更新（目录结构/成员清单/L3 头部）
  3. 更新完成后，在报告中标注：
     "✅ Q10 已修复：[列出修复的文件和内容]"

Q10 未执行时的阻塞规则：
  - 如果 Q8/Q9 检测到问题，但 Q10 没有执行修复：
    → 报告状态标记为 ⛔ BLOCKED（不是 ✅）
    → 禁止输出"实现完成"
    → 禁止进入 /git_commit
```

---

### 📋 自检报告输出规则

以上 Q1-Q10 **全部执行完毕后**，按实际命令输出填写下方报告模板。
**不允许填写未执行命令的结果（即不能凭感觉填 ✅）。**
**如果 Q10 被触发但未执行修复，报告状态必须为 ⛔ BLOCKED。**

---

## 实现完成后的输出格式（固定）

```
✅【实现完成】— [功能模式 / 修复模式]

📁 文件变更清单:

  新建:
    + frontend/src/app/xxx/page.tsx
    + backend/routers/xxx.py

  修改:
    ~ frontend/src/app/layout.tsx    ← [改动摘要]
    ~ backend/main.py                ← [改动摘要]

⚠️ 不确定项 [UNCERTAIN]:
  1. [文件:行号] — [不确定描述，需人工确认]

💡 发现的建议（未实现，等待确认）:
  1. [类型] [位置] — [描述]

🧪 验证步骤:
  1. [运行命令或操作步骤]
  2. [期望结果]
  3. [如何判断成功]

---
🔍【内联质量检查报告】（基于 Q1-Q10 命令实际输出填写，禁止凭感觉填 ✅）

代码品味（Q1-Q3 前端 / Q4-Q5 后端）:
  □/✅ 函数长度(≤20行)   □/✅ 嵌套深度(≤3层)   □/✅ 分支数(≤3个)
  □/✅ 重复代码           □/✅ 命名质量           □/✅ 副作用隔离

GEB 文档（Q6-Q9 检测 + Q10 修复）:
  FATAL: □ 001 □ 002 □ 003 □ 004  → [全通过 / 编号拦截]
  SEVERE: □ 001 □ 002 □ 003 □ 004 → [全通过 / 编号已由Q10修复]

Q10 修复记录:
  [未触发 / ✅ 已修复：列出修改的文件 / ⛔ BLOCKED：未修复，禁止继续]

已同步文档: [列表或"无变化"]
---

下一步: /git_commit（review + sync_doc 已内联完成）
```

---

## 验证步骤规范

每次实现完成后，必须提供以下至少一项验证：

| 场景 | 验证方式 |
|------|---------|
| 前端 UI 变更 | 列出操作步骤 + 期望看到的界面状态 |
| 后端 API 变更 | 提供 curl 命令或 FastAPI `/docs` 测试步骤 |
| 逻辑修复 | 提供触发原 Bug 的复现步骤 + 确认修复的验证步骤 |
| 数据处理 | 提供输入样例 + 期望输出 |

---

## 与其他工作流的关系

```
功能开发链（优化后 4 回合）:
  analyze → design → implement（功能模式，内联 review+sync_doc）→ git_commit

Bug 修复链（优化后 4 回合）:
  debug → design → implement（修复模式，内联 review+sync_doc）→ git_commit

注：/review 和 /sync_doc 工作流保留，可在需要单独执行时手动调用。
```
