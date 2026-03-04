# check-indicator-combo/CLAUDE.md

[PROTOCOL]: 变更时更新此头部，然后检查父级 /CLAUDE.md

## 模块定位

**指标组合筛选**：23 种策略组合（TD9/MACD金叉/稳步上升/放量突破/阴线 的排列组合），
输出命中任意策略的股票列表及其所属策略。

原名 `check-new-indicators`，Phase 3 重构后对齐标准架构。

## 目录结构

```
check-indicator-combo/
├── main.py               ← 入口，CLI 参数解析
├── pipeline.py           ← 流程包装（Phase 3 新建）
├── reporter.py           ← Reporter 类（包装 reporters/ 的两个生成器）
├── data_loader.py        ← 股票列表 + 日线数据加载
├── analyzers/
│   ├── __init__.py       ← 暴露 StockAnalyzer
│   └── combo_analyzer.py ← 23 种策略核心逻辑（原 analyzer.py）
├── reporters/
│   ├── html_reporter.py  ← HTML 报告（极简 iframe 风格）
│   └── markdown_reporter.py
├── tests/
│   ├── test_report.py
│   └── test_td9_macd_gold.py
└── output/               ← 生成报告目录（不纳入 git）
```

## 运行

```bash
cd check-indicator-combo
python main.py              # 全量
python main.py --limit 50   # 测试50只
python main.py --end-date 2026-03-01
```

## 策略分级

| 级别 | 数量 | 代表策略 |
|------|------|---------|
| 强信号 | 11种 | TD9+MACD金叉+放量突破 |
| 中信号 | 6种  | MACD金叉+放量突破 |
| 观察  | 4种  | TD9或MACD金叉 |

## 关键约束

- `reporters/html_reporter.py` 超 1000 行，属于 GEB 预警区，Phase 4 拆分
- `analyzers/combo_analyzer.py` 是业务核心，**只允许添加策略，不改现有策略逻辑**
- 不直接依赖 `check-*` 其他模块（仅依赖 `util/`）
