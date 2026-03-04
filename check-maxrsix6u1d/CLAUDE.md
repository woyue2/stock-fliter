# check-maxrsix6u1d/CLAUDE.md

[PROTOCOL]: 变更时更新此头部，然后检查父级 /CLAUDE.md

## 模块定位

**MAxRSIx6U1D及趋势共振**：对日均线长期向上且没有暴涨暴跌的股票进行筛选，结合指标共振、回撤分析和网格分析进行高胜率验证。

## 目录结构

```
check-maxrsix6u1d/
├── main.py               ← 入口，CLI 参数解析
├── pipeline.py           ← 流程控制（调用多个 analyzers，合并数据）
├── data_loader.py        ← 数据加载
├── CLAUDE.md             ← (L2) 局部架构说明
├── indicators.py         ← 常用技术指标 (基础)
├── analyzers/
│   ├── ma_alignment_analyzer.py
│   ├── trend_analyzer.py
│   └── grid_analyzer.py
├── combiners/
│   └── momentum_combiner.py
├── reporters/
│   ├── html_reporter.py
│   └── markdown_reporter.py
└── README.md
```

## 运行

```bash
cd check-maxrsix6u1d
python main.py              # 全量（耗时较长）
python main.py --test       # 测试10只
python main.py --analyzers 1,3  # 指定运行分析器 (1:MA排列 3:趋势)
```

## 关键约束

- 数据预处理统一使用 `data_loader.py` 加载。
- 并行或串行计算流必须通过 `pipeline.py` 进行数据传递和衔接。
- 禁止子模块内部调用互相循环依赖。
