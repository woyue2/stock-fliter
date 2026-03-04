# 技术方案 (How)

## 1. 架构设计
采用模块化分层架构，位于 `check-new-indicators/` 目录：

```
check-new-indicators/
├── main.py            # 入口脚本，负责流程控制
├── data_loader.py     # 数据加载层 (封装对原始数据的读取)
├── analyzer.py        # 核心分析层 (实现6种策略逻辑)
├── reporter.py        # 报告生成层 (CSV -> MD/HTML)
└── output/            # 结果输出目录
```

核心依赖：`util/indicators_lib.py` (提供基础指标计算)

## 2. 详细设计

### 2.1 数据加载 (data_loader.py)
- 复用或适配现有的数据加载逻辑（如 `get-data` 或其他模块的 loader）。
- 确保能正确读取每日 K 线数据。

### 2.2 策略实现 (analyzer.py)
基于 `util.indicators_lib` 实现以下逻辑：
1. **移植指标**: 确认 `check_volume_breakout` 和 `check_macd_golden_cross_below_zero` 可用。
2. **策略分类**:
   - **Strong Buy**: `steady_uptrend`=True AND `volume_breakout`=True
   - **Potential**: `steady_uptrend`=False AND `macd_gold_cross_below_zero`=True
   - **Steady Only**: `steady_uptrend`=True AND `volume_breakout`=False
   - **Watch List (Left)**: 基于 TD9 或 MACD 底背离（作为辅助列或独立列表）。

### 2.3 报告生成 (reporter.py)
- **CSV**: 包含股票代码、名称、各项指标值、所属策略分类。
- **Markdown**: 分类展示各策略选出的股票列表。
- **HTML**: 使用简单模板展示表格和高亮信息。

## 3. 风险评估
- **数据路径风险**: 不同模块间的数据路径可能不一致，需统一配置。
- **规避**: 在 `data_loader.py` 中使用相对路径或配置查找逻辑，确保能找到 `data/` 目录。

## 4. 依赖变更
- 无新增第三方库依赖，仅使用 `pandas`, `numpy` 和项目内部 `util`。
