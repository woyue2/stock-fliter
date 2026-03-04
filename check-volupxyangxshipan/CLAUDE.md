# check-volupxyangxshipan/CLAUDE.md

[PROTOCOL]: 变更时更新此头部，然后检查父级 /CLAUDE.md

## 模块定位

**VolUp x Yang x Shipan筛选**：策略为"昨放量（昨量 > 前3天均量）+ 今阳线"，附带试盘行为识别。

Phase 6 补全结构，分离分析逻辑到 `analyzers/`。

## 目录结构

```
check-volupxyangxshipan/
├── main.py               ← 入口，CLI 参数解析
├── pipeline.py           ← 流程包装（收集命中+全市场数据）
├── data_loader.py        ← 股票列表 + 日线数据加载
├── shipan_logic.py       ← 试盘行为识别
├── 策略.md               ← 策略逻辑详细说明
├── analyzers/
│   ├── __init__.py       ← 暴露 evaluate_stock, empty_result_df
│   └── volup_yang_shipan_analyzer.py ← 策略核心逻辑（Phase 6 从 pipeline.py 提取）
├── reporters/
│   ├── __init__.py
│   ├── html_reporter.py
│   └── markdown_reporter.py
├── README.md
└── output/               ← 生成报告目录（不纳入 git）
```

## 运行

```bash
cd check-volupxyangxshipan
python main.py              # 全量
python main.py --test       # 前10只 (测试)
python main.py --date 2026-03-01
python main.py --no-open    # 不自动打开浏览器
```

## 策略说明

| 条件 | 说明 |
|------|------|
| 昨放量 | 昨日成交量 > 前2日、前3日、前4日成交量 |
| 今阳线 | 今日收盘 > 开盘 |
| 试盘次数 | 识别主力试盘行为（来自 shipan_logic.py）|

## 关键约束

- `analyze_shipan_behavior` 在 `shipan_logic.py`，不属于 analyzers 职责不拆分
- `volup_yang_shipan_analyzer.py` 只含策略判断，**不含 IO/网络操作**
- HTML 输出格式（列定义/分组方式）与 check-td 保持一致风格
