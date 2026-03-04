---
description: 结构化 Git 提交 + 演化日志同步
---

## 前置条件

- 已完成代码修改，但**尚未 `git add`**
- 执行此工作流前，先确保 `/implement` 已完成（含内联质量检查与文档同步）

---

## 步骤

### 1. 查看变更范围

// turbo
1. 查看当前 git 状态与 diff 摘要
   CommandLine: git status && git diff --stat

---

### 2. 按功能拆分 commit

2. **分析变更，按以下规则拆分暂存区**：

   - 每个 commit **只做一件事**（单一职责）
   - 拆分维度参考：
     | 变更类型 | 示例 |
     |----------|------|
     | 新功能   | 新增页面、新增 API 路由 |
     | Bug 修复 | 修复某个逻辑错误 |
     | 重构     | 提取公共组件、重命名变量 |
     | 文档     | 更新 CLAUDE.md、evolution.md |
     | 样式     | 调整 TailwindCSS 类名、UI 微调 |
     | 配置     | 修改 vite.config / next.config / .env |
     | 依赖     | 新增 / 升级 / 移除 npm 包或 pip 包 |

   - 对于每组变更，执行：
     ```bash
     git add <精确的文件路径>
     git commit -m "<结构化 commit message>"
     ```

---

### 3. 结构化 commit message 格式

```
<type>(<scope>): <subject>

[body - 可选，解释 WHY，不是 WHAT]

[footer - 可选，关联 issue 或 breaking change]
```

**type 枚举**：

| type     | 含义                         |
|----------|------------------------------|
| `feat`   | 新功能                       |
| `fix`    | Bug 修复                     |
| `refactor` | 重构（不改变外部行为）     |
| `docs`   | 仅文档变更                   |
| `style`  | 样式/格式（不影响逻辑）      |
| `chore`  | 构建/配置/依赖变更           |
| `test`   | 测试相关                     |
| `perf`   | 性能优化                     |

**scope 示例**（根据当前项目）：

| scope      | 含义               |
|------------|--------------------|
| `frontend` | Next.js 前端整体   |
| `backend`  | FastAPI 后端整体   |
| `ui`       | 组件 / 样式        |
| `api`      | API 路由 / Schema  |
| `auth`     | 认证模块           |
| `docs`     | 文档相关           |
| `config`   | 配置文件           |
| `deps`     | 依赖管理           |

**示例 commit message**：

```
feat(api): 新增 /api/users/bind 手机号绑定接口

原有邀请码输入错误率高（> 30%），改为手机号匹配方式。
需同步更新前端绑定表单和审核逻辑。

Closes #42
```

```
refactor(ui): 提取 Button 组件，统一样式 token

将散落在 5 个页面中的 button 样式收归为 Button.tsx，
消除重复，遵循 config.yaml 中"优先消除特殊情况"的哲学。
```

---

### 4. 更新 /docs/evolution.md（演化日志）

4. **规则**：
   - 日期格式：`# YYYY-MM-DD`（使用当前日期）
   - **如果当日日期标题已存在**：不重复创建，直接在该标题下追加新记录
   - **如果当日不存在**：在文件**顶部**（最新在前）插入新日期标题，再追加记录

5. **每段记录格式**：

```markdown
## 变动  <简短描述（≤ 20 字）>
### 原因  <WHY，解释动机>
### 影响  <改动涉及的范围 / 需要注意的事项>
```

6. **示例**（当日为 2026-03-02）：

```markdown
# 2026-03-02

## 变动  工作流从 Vite+React 改为 Next.js+FastAPI+TailwindCSS v4
### 原因  用户需求变更，需要全栈架构支撑 API 层
### 影响  initialize / bootstrap / sync_doc 工作流全部重写；前端框架从 Vite 切换为 Next.js App Router；后端新增 FastAPI 骨架
```

// turbo
7. 检查 /docs/evolution.md 是否存在，若不存在则创建
   CommandLine: if not exist docs mkdir docs && if not exist docs\evolution.md echo # Evolution Log > docs\evolution.md

8. 手动打开 `docs/evolution.md`，按上述规则追加当日记录

---

### 5. 提交文档变更

// turbo
9. 单独 commit 文档更新
   CommandLine: git add docs/evolution.md && git commit -m "docs(evolution): 记录 YYYY-MM-DD 变动"

---

### 6. 验证提交历史

// turbo
10. 查看最近 5 条 commit，确认结构清晰
    CommandLine: git log --oneline -5

---

## 速查卡

```
# 常用命令
git add <file>                         # 精确暂存
git add -p                             # 交互式分块暂存（推荐用于大改动）
git diff --staged                      # 确认暂存内容
git commit -m "type(scope): subject"   # 提交
git log --oneline -10                  # 查看历史
```
