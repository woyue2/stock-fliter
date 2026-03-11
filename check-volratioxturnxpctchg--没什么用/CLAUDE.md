# check-volratioxturnxpctchg/CLAUDE.md

[PROTOCOL]: 变更时更新此头部，然后检查父级 /CLAUDE.md

## 模块定位

**量比×换手率×涨跌幅 组合筛选**：收盘后全市场扫描，纯日线数据驱动。
筛选同时满足以下 6 项条件的股票：量比 4~10、涨跌幅 3%~8%、价格 >4 元、
换手率 2%~15%、总金额 2亿~20亿、当日收涨。

## 目录结构

```
check-volratioxturnxpctchg/
├── CLAUDE.md              ← L2 文档（本文件）
├── 策略.md                ← 策略说明
├── main.py                ← 入口，CLI 参数解析
├── pipeline.py            ← 流程包装（并行/串行扫描）
├── reporter.py            ← Reporter 类（包装 reporters/ 的两个生成器）
├── data_loader.py         ← 股票列表 + 日线数据加载（含 turn/amount/pctChg）
├── analyzers/
│   ├── __init__.py        ← 暴露 StockAnalyzer
│   └── surge_analyzer.py  ← 6 项过滤条件核心逻辑
├── reporters/
│   ├── markdown_reporter.py
│   └── html_reporter.py
└── output/                ← 生成报告目录（不纳入 git）
```

## 运行

```bash
cd check-volratioxturnxpctchg
python main.py              # 全量扫描
python main.py --limit 50   # 测试 50 只
python main.py --end-date 2026-03-04
python main.py --no-open    # 不自动打开浏览器
```

## 筛选条件

| 条件 | 字段 | 范围 |
|------|------|------|
| 量比 | volume / 5日均量 | 4 < VR < 10 |
| 涨跌幅 | pctChg | 3% < x < 8% |
| 价格 | close | > 4 元 |
| 换手率 | turn | 2% < x < 15% |
| 总金额 | amount | 2亿 < x < 20亿 |
| 当日涨 | pctChg | > 0% |

## 关键约束

- 纯日线数据驱动，不依赖分钟线
- 不直接依赖 `check-*` 其他模块（仅依赖 `util/` 和 `get-data/data/`）
- `surge_analyzer.py` 是业务核心，阈值通过模块级常量管理
