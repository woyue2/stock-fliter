# check-zhulistrength

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

## 概述
主力强度与资金效率分析模块 (A*B*C Logic)。
基于三层博弈：
- A (主力强度)：资金进攻意愿
- B (散户净额)：市场背离验证（真实验证）
- C (资金效率/成交容量)：预期效果过滤

## 成员清单
- `main.py`: CLI 入口 [INPUT: Args -> Config / OUTPUT: Execution Trigger]
- `pipeline.py`: 调度中枢 [INPUT: Config -> Trigger / OUTPUT: File I/O]
- `data_loader.py`: 数据装载 [INPUT: SQLite/CSV -> DataFrame / OUTPUT: Standardized DF]
- `analyzers/strength_analyzer.py`: 核心分析 [INPUT: DataFrame -> Logic / OUTPUT: Analyzed Flags]
- `reporters/markdown_reporter.py`: 报告生成 [INPUT: Result DF -> Markdown / OUTPUT: .md File]
