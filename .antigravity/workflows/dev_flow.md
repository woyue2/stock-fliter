---
description: 开发主干流程 — 混合架构（3 Skill + 5 Workflow，速度与质量均衡）
---

## 架构概览

```
Skills（需显式读取才能生效，不会自动激活）:
  ├── geb_protocol   ← 身份 + 哲学 + GEB 协议
  ├── oop_phase      ← 三期设计约束（探索/增长/冻结）← /design 开始前读取
  └── impl_quality   ← 实现质量内联（review + sync_doc 自动内嵌）← /implement 开始前读取

Workflows（需要人工决策的节点，保留为手册）:
  ├── analyze        ← 你确认需求理解
  ├── debug          ← 你确认根因
  ├── design         ← 你拍板方案（最关键人工决策点）
  ├── implement      ← AI 执行 + 自动内联品味自检/GEB 检查
  └── git_commit     ← 你确认 commit 内容
```

---

## 两条开发轨道（优化后：4 回合完成）

### 🚀 轨道 A — 功能开发

```
/analyze  →  /design  →  /implement  →  /git_commit
  你确认      你拍板     AI执行+自检     你确认commit
```

### 🐛 轨道 B — Bug 修复

```
/debug  →  /design fix  →  /implement fix  →  /git_commit
  你确认      你拍板        AI执行+自检        你确认commit
```

> 📌 `/review` 和 `/sync_doc` **不再需要单独调用**（已内联进 implement）。
> 如果需要单独进行文档审查或代码审查，仍可手动调用。

---

## 完整流程图

```
新任务
  │
  ├─── 是新功能 / 重构？
  │         │
  │         ▼
  │    ┌──────────────────────────────────┐
  │    │ 1. /analyze                      │
  │    │    需求完整性评分 + 追问循环      │  ← 评分<7分: 追问
  │    │    评分≥7分: 输出需求总结        │  ← 你确认 [回合 1]
  │    └──────────────┬───────────────────┘
  │                   │
  └─── 是 Bug / 报错？
            │
            ▼
       ┌──────────────────────────────────┐
       │ 1b. /debug                       │
       │     根因分析 + 概率标注          │  ← 只分析，不给方案
       │     输出：失败原因清单           │  ← 你确认 [回合 1]
       └──────────────┬───────────────────┘
                      │
            ┌─────────┘ ← 两条轨道在此汇合
            │
            ▼
       ┌──────────────────────────────────┐
       │ 2. /design                       │
       │    ≥3 个方案对比                 │  ← 功能模式 or 修复模式
       │    推荐最稳妥方案                │  ← 你拍板 [回合 2]（最关键点）
       └──────────────┬───────────────────┘
                      │ 方案确认
                      ▼
       ┌──────────────────────────────────┐
       │ 3. /implement                    │
       │    声明文件计划 → 实现代码       │
       │    [自动] 品味自检（impl_quality）│
       │    [自动] GEB 文档检查+同步      │  ← AI执行 [回合 3]
       │    输出：代码 + 质量检查报告     │
       └──────────────┬───────────────────┘
                      │ 代码完成 + 质量核验
                      ▼
       ┌──────────────────────────────────┐
       │ 4. /git_commit                   │
       │    按功能拆分 commit             │
       │    更新 docs/evolution.md        │  ← 你确认 [回合 4]
       └──────────────┬───────────────────┘
                      │
                      ▼
                   ✅ 完成
```

---

## 所有工作流快速索引

| 命令 | 文件 | 触发时机 | 人工决策？ | 输出 |
|------|------|---------|----------|------|
| `/analyze`    | `analyze.md`    | 接到新功能需求时 | ✅ 你确认 | 需求总结 + 成功标准 |
| `/debug`      | `debug.md`      | 遇到 Bug / 报错时 | ✅ 你确认 | 根因清单 + 概率标注 |
| `/design`     | `design.md`     | analyze 或 debug 完成后 | ✅ **你拍板** | ≥3方案对比 + 推荐 |
| `/implement`  | `implement.md`  | design 方案确认后 | 🤖 AI执行 | 代码 + 内联质量报告 |
| `/git_commit` | `git_commit.md` | implement 完成后 | ✅ 你确认 | 结构化 commits + evolution |
| `/review`     | `review.md`     | 需要单独代码审查时 | — | 品味自检（已内联，手动使用） |
| `/sync_doc`   | `sync_doc.md`   | 需要单独文档同步时 | — | GEB 文档同步（已内联，手动使用） |
| `/bootstrap`  | `bootstrap.md`  | 新项目/新模块初始化 | — | GEB 文档结构 |
| `/initialize` | `initialize.md` | 项目首次环境初始化 | — | Next.js + FastAPI 环境 |

---

## Skills 快速索引

| Skill | 路径 | 生效方式 | 作用 |
|-------|------|---------|------|
| `geb_protocol` | `.antigravity/skills/geb_protocol/SKILL.md` | **需显式读取**（手动调用） | 身份 + GEB 协议 |
| `oop_phase`    | `.antigravity/skills/oop_phase/SKILL.md`    | **需显式读取**（design Step 0 强制执行） | 三期设计约束 |
| `impl_quality` | `.antigravity/skills/impl_quality/SKILL.md` | **需显式读取**（implement Step 0 强制执行） | 品味自检 + GEB 文档 + 后端规范 |

---

## 每个阶段的严格职责边界

```yaml
analyze.md:
  读:  知识库、代码库、用户需求
  写:  ❌ 不写任何文件（只读）
  禁止: 给方案、写代码

debug.md:
  读:  报错信息、代码片段、git log
  写:  ❌ 不写任何文件（只读）
  禁止: 给修复方案、写代码

design.md:
  读:  analyze 或 debug 的输出
  写:  ❌ 不写任何文件（只读）
  禁止: 写具体代码实现

implement.md:
  读:  design 输出的推荐方案
  写:  frontend/src/**、backend/**（按计划）
  产出: 可运行的代码 + 内联质量检查报告
  禁止: 超出 design 计划范围的改动、未声明的新依赖
  内联: impl_quality Skill（review + sync_doc 自动完成）

git_commit.md:
  读:  git status、git diff
  写:  docs/evolution.md
  产出: 结构化 commits

review.md（手动使用）:
  读:  任意代码文件
  写:  可能补充 L3 头部 / 拆分函数
  禁止: 超出品味修复范围的重构

sync_doc.md（手动使用）:
  读:  任意代码文件
  写:  L1/L2/L3 CLAUDE.md
  禁止: 在 FATAL 级拦截未解决时继续
```

---

## 快捷使用卡

```bash
# 开发新功能（4 回合）
/analyze [需求描述]
/design
/implement        ← 自动内联 review + sync_doc
/git_commit

# 修复 Bug（4 回合）
/debug [报错信息 + 现象 + 代码片段]
/design fix
/implement fix    ← 自动内联 review + sync_doc
/git_commit

# 项目冷启动
/initialize
/bootstrap

# 单独使用（需要时）
/review           ← 手动代码审查
/sync_doc         ← 手动文档同步
```

---

## 工作流之间的数据传递规则

```
analyze → design:
  传递: 需求类型、关键目标、成功标准、涉及模块路径

debug → design:
  传递: 高概率根因（🔴）、涉及文件路径、信息缺口

design → implement:
  传递: 推荐方案描述、改动范围、成立前提

implement → git_commit:
  传递: 实际修改的文件路径 + 质量检查报告结论
       （GEB 文档已在 implement 内同步完成）
```

> 💡 **技巧**：每步完成后，把输出的总结段直接粘贴给下一步作为输入，
> 确保上下文不丢失，避免重复扫描代码库。
