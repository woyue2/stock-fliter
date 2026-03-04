# AGENTS

## 架构最优分配：混合架构

本项目采用 `Skill + Workflow` 混合模式，判定维度为：
- 修改频率（高/中/低）
- 决策权重（AI 自动执行 / 需要人工拍板）

核心原则：
- 高频且无需人工决策：下沉为 `Skill`（需显式读取后生效）
- 存在关键人工决策点：保留为 `Workflow`（作为流程地图与确认手册）
- `implement` 采用混合形态：`Workflow` 保留骨架，`review/sync_doc` 内嵌进 `Skill`

---

## 决策矩阵（修改频率 × 决策权重）

| 工作流/能力 | 决策权在谁 | 改动频率 | 最优形态 | 理由 |
|---|---|---|---|---|
| `load_context` | AI 自己 | 低 | Skill | 纯上下文加载，没有决策点 |
| `config.yaml` 协议 | AI 自己 | 低 | Skill | 身份/哲学/红线应通过 Skill 显式读取后生效 |
| `analyze` | 你确认 | 中 | Workflow | 需求分析结论需要你拍板 |
| `debug` | 你确认 | 高 | Workflow | bug 高频，根因列表需要你验证 |
| `design` | 你拍板 | 中 | Workflow | 方案选择是关键人工决策点 |
| `implement` | AI 执行 | 高 | Skill 约束 + Workflow 框架 | 执行频繁，保留阶段框架并自动执行质量约束 |
| `review` | AI 自检 | 高 | Skill（内嵌） | 合并进 `implement` 自动执行，减少中断 |
| `sync_doc` | AI 执行 | 高 | Skill（内嵌） | 合并进 `implement` 自动执行，确保代码文档同构 |
| `git_commit` | 你确认 | 高 | Workflow | commit message 与提交边界需人工确认 |
| `bootstrap` | AI 执行 | 极低 | Workflow | 初始化低频一次性，透明可审计更重要 |

---

## 最终分配结论

核心结论：`3 Skill + 5 Workflow` 混合

### Skills（需显式读取后生效）
- `.antigravity/skills/geb_protocol/SKILL.md`
  - 合并 `config.yaml + load_context` 语义
- `.antigravity/skills/oop_phase/SKILL.md`
  - 面向对象三期约束
- `.antigravity/skills/impl_quality/SKILL.md`
  - 将 `review + sync_doc` 约束内嵌进实现流程

### Workflows（需要你参与决策，保留为手册/索引）
- `.antigravity/workflows/analyze.md`
  - 你确认需求理解
- `.antigravity/workflows/debug.md`
  - 你确认根因
- `.antigravity/workflows/design.md`
  - 你拍板方案（关键决策点）
- `.antigravity/workflows/implement.md`
  - 保留执行框架，`review/sync_doc` 由 Skill 自动内嵌
- `.antigravity/workflows/git_commit.md`
  - 你确认 commit 内容

---

## 执行约束

- `bootstrap` 仅作为初始化流程索引，不参与常规循环执行。
- 常规开发默认路径：`analyze -> design -> implement -> git_commit`。
- `implement` 阶段必须自动带出 `impl_quality` 约束（含 review 与 sync_doc）。
- 未触发人工决策点时，AI 在显式读取所需 Skill 后直接推进，不增加额外交互。
