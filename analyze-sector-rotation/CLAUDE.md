# analyze-sector-rotation/CLAUDE.md

[PROTOCOL]: 变更时更新此头部，然后检查父级 /CLAUDE.md

## 模块定位

**板块轮动分析**：通过聚合成员股分时数据，合成板块的实时强度曲线，识别资金在不同板块之间的轮动路径。

> ⚠️ 当前为**原型阶段**，不接入 `run_all_strategies.py` 主调度流程。

## 目录结构

```
analyze-sector-rotation/
├── CLAUDE.md              ← L2 文档（本文件）
├── README.md              ← 外部文档（使用说明）
├── prototype_minute.py    ← 核心函数（板块分时合成）
└── data/
    └── sector_minutes/    ← 合成结果输出（不纳入 git）
```

## 成员清单

- `prototype_minute.py` — 核心功能：`synthesize_sector_minute(sector_name, sample_limit)`

## 外部依赖

- `akshare` — 分时数据源
- `get-data/data/selected_stocks_all.csv` — 股票-概念映射（SSOT）

## 演进状态

| 状态 | 说明 |
|------|------|
| 🧪 原型 | 当前阶段，仅支持单板块手动触发 |
| 🎯 目标 | 成熟后迁移至 `util/minute_analysis/sector_synthesizer.py` |
