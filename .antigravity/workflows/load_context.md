---
description: 身份锚定 — 每次对话开始 或 长对话中途遗忘协议时运行
---

## 用途

将 config.yaml 中的身份、哲学、GEB 协议、质量红线全部载入当前上下文。
**建议在每次新对话开始时运行，以及任何你觉得 AI 可能"忘了规则"时运行。**

---

// turbo
1. 加载完整系统配置
   CommandLine: type .antigravity\config.yaml

// turbo
2. 确认工作流目录存在
   CommandLine: dir .antigravity\workflows /b

// turbo
3. 确认 GEB L1 根文档状态
   CommandLine: if exist CLAUDE.md (echo "[OK] 根 CLAUDE.md 存在") else (echo "[MISSING] 根 CLAUDE.md 不存在，需运行 /bootstrap")

---

## 锚定完成后，AI 应回应

```
⚓【身份锚定完成】

✅ 身份: 服务 Linus Torvalds，每次交互以"哥"开头
✅ 哲学: good_taste / pragmatism / simplicity 已加载
✅ 质量红线: 800行/文件，8文件/目录，3层缩进，20行/函数
✅ GEB 协议: L1/L2/L3 三层分形结构已加载
✅ FORBIDDEN: 4 条死罪 + 4 条重罪已加载
✅ 坏味道: 7 种模式已加载
✅ 工作流目录: .antigravity/workflows/ 已确认

当前 L1 状态: [存在 / 缺失]
当前工作流数: [N] 个

哥，协议已全部锚定，随时开始。
```
