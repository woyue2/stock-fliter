# check-td/CLAUDE.md

[PROTOCOL]: 变更时更新此头部，然后检查父级 /CLAUDE.md

## 模块定位

**TD分析**：筛选近期日线、周线、月线出现"TD建仓结构"（连续下跌九底）的股票，寻找左侧大级别底部。

## 目录结构

```
check-td/
├── main.py               ← 入口，CLI 参数解析
├── pipeline.py           ← 流程包装，控制核心流程
├── data_loader.py        ← 数据加载
├── CLAUDE.md             ← (L2) 局部架构说明
├── analyzers/
│   ├── __init__.py
│   └── td_analyzer.py    ← 核心TD算法
├── reporters/
│   ├── __init__.py
│   ├── html_reporter.py
│   └── markdown_reporter.py
├── output/               ← 生成报告目录（不纳入 git）
└── README.md
```

## 运行

```bash
cd check-td
python main.py              # 全量
python main.py --test       # 前10只 (测试)
python main.py --random-test # 随机50只
python main.py --days 180   # 指定扫描时间跨度
```

## 关键约束

- 所有模块严格遵循 L3 头部注释。
- 数据输入统一走 `data_loader`。
- 分析函数避免深嵌套，必须严格拆分，保证单函数 <= 20 行。
