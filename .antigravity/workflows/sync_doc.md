---
description: 代码 → 文档回环同步 — Next.js + FastAPI（含 GEB FORBIDDEN 检查）
---

## 触发时机

每次代码变更后运行此工作流，保持代码‑文档同构。
**必须在 `/review` 之后、`/git_commit` 之前运行。**

---

## 阶段 0：GEB FORBIDDEN 强制检查（前置拦截）

**在执行任何文档同步之前，先拦截违禁行为。**
发现 Fatal 级违规 → 立即停止，修复后才能继续。

### 死罪检查（Fatal — 发现即停止）

// turbo
**FATAL-001/002/003/004 基础数据采集（所有检查的客观基准）**
CommandLine: git diff --name-only HEAD

// turbo
**FATAL-002/004: 查看本次新增文件**
CommandLine: git diff --diff-filter=A --name-only HEAD

// turbo
**FATAL-003: 查看本次删除文件**
CommandLine: git diff --diff-filter=D --name-only HEAD

// turbo
**FATAL-002: 扫描新增文件是否缺少 [PROTOCOL] 标记（客观检查，不可幻觉）**
CommandLine: git diff --diff-filter=A --name-only HEAD | findstr /i ".ts .tsx .py .js" > tmp_new_files.txt && for /f %f in (tmp_new_files.txt) do findstr /m "PROTOCOL" %f || echo "[MISSING PROTOCOL] %f"

// turbo
**FATAL-004: 检查新增文件所在目录是否有 CLAUDE.md**
CommandLine: git diff --diff-filter=A --name-only HEAD | findstr /i ".ts .tsx .py .js" > tmp_new_files.txt && for /f %f in (tmp_new_files.txt) do if not exist "%~dpfCLAUDE.md" echo "[MISSING L2] %~dpf"

// turbo
**FATAL-003: 检查被删除文件对应 L2 CLAUDE.md 是否已更新**
CommandLine: git diff --diff-filter=D --name-only HEAD

> ⚠️ **对照上方命令输出逐条处理**：
> - `[MISSING PROTOCOL]` 开头的行 → FATAL-002，立即补充 L3 头部
> - `[MISSING L2]` 开头的行 → FATAL-004，立即创建对应 CLAUDE.md
> - 被删除的文件 → 手动确认其父目录 CLAUDE.md 已清除对应条目（FATAL-003）


### 重罪检查（Severe — 警告后修复）

```
⚠ SEVERE-001 L3 过时
    本次修改的文件，其 [INPUT]/[OUTPUT]/[POS] 与当前代码是否仍然匹配？
    不匹配 → 警告，更新后继续

⚠ SEVERE-002 L2 不完整
    各目录的 CLAUDE.md 是否列出了该目录下所有文件？
    有未列入的文件 → 警告，追加后继续

⚠ SEVERE-003 L1 过时
    根 CLAUDE.md 的 <directory> 列表是否反映了当前的目录结构？
    不一致 → 警告，更新后继续

⚠ SEVERE-004 父级链接断裂
    L2 文档头部的「父级: {父路径}/CLAUDE.md」链接是否还有效？
    链接失效 → 警告，更新后继续
```

### 违规输出格式

```
⛔【GEB 违规】
  代码: [FATAL-00X / SEVERE-00X]
  位置: [文件/目录路径]
  描述: [违规内容]
  修复: [立即执行的修复步骤]
  状态: ✅ 已修复 / ❌ 需手动处理
```

---

## 阶段 1：L3 代码↔注释同步

**前端（TypeScript / TSX）**：
- 遍历 `frontend/src/**/*.ts|tsx`
- 校验 L3 头部字段与实际代码匹配：
  - `[INPUT]`：与 import / props 类型一致
  - `[OUTPUT]`：与 export / 返回值一致
  - `[POS]`：与文件实际路径一致
  - `[PROTOCOL]` 行：必须存在
- 不匹配 → 自动更新注释

**后端（Python）**：
- 遍历 `backend/**/*.py`（排除 `.venv/`）
- 校验 L3 头部字段：
  - `[INPUT]`：与 FastAPI Request Schema / 参数一致
  - `[OUTPUT]`：与 Response Schema 一致
  - `[POS]`：与实际文件路径一致
  - `[PROTOCOL]` 行：必须存在
- 不匹配 → 自动更新注释

---

## 阶段 2：L2 成员清单同步

**前端**：
- 对比 `frontend/src/` 实际文件列表 vs `frontend/CLAUDE.md` 成员清单
- 缺失条目 → 追加；冗余条目 → 删除并提示

**后端**：
- 对比 `backend/` 实际文件列表 vs `backend/CLAUDE.md` 成员清单
- 缺失条目 → 追加；冗余条目 → 删除并提示

---

## 阶段 3：L1 全局地图同步

- 若有顶级目录增删（如新增 `backend/routers/`）
- 自动更新根 `CLAUDE.md` 的 `<directory>` 列表

---

## 阶段 4：API 契约对齐

- 扫描 FastAPI 路由（`@app.get / .post / .put / .delete`）
- 生成或更新 `docs/api_contract.md`（METHOD、PATH、Request Schema、Response Schema）
- 检查 `frontend/` 的 fetch / axios 调用路径是否与后端一致
- 不一致 → 输出警告，等待手动确认

---

## 同步完成输出格式

```
✅【文档同步完成】

🔴 Fatal 违规:   [无 / X 处（已全部修复）]
⚠️  Severe 警告:  [无 / X 处（已全部修复）]

📜 L3 更新:
  ~ [文件路径]  ← [更新字段]

📁 L2 更新:
  ~ [CLAUDE.md 路径]  ← [追加/删除了哪些条目]

🗺️  L1 更新:   [无变动 / 已更新]
📋 API 契约:   [无变动 / 已更新 docs/api_contract.md]
```

// turbo
完成后提交
CommandLine: git add . && git commit -m "🔄 Sync GEB 文档 (L1/L2/L3 + API 契约)"

