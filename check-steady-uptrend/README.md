# 股票筛选系统 - 重构版

该系统用于A股市场的技术分析筛选，支持多种分析策略的组合使用。

## 快速开始

```bash
# 方式1：双击运行
run.bat

# 方式2：命令行运行
python main.py --skip-fetch    # 使用已有分析结果
python main.py                 # 完整分析流程
```

## 系统架构

```
check-steady-uptrend/
├── main.py              # 主程序入口
├── pipeline.py          # 分析流水线
├── utils.py             # 工具函数
├── data_loader.py       # 数据加载
├── indicators.py        # 技术指标
├── mystic_indicators.py # 玄学指标
├── analyzers/           # 分析器模块
│   ├── steady_uptrend_analyzer.py   # 稳步上升分析
│   ├── trend_analyzer.py            # 趋势分析
│   └── grid_analyzer.py             # 网格测试
├── combiners/           # 组合器模块
│   └── xuanxue_combiner.py          # 玄学联合筛选
├── reporters/           # 报告生成器
│   ├── markdown_reporter.py         # MD报告
│   └── html_reporter.py             # HTML报告
└── output/              # 输出目录（按日期/时间组织）
```

## 分析器说明

### 1. 稳步上升分析 (代号: 1)

判断股票是否处于稳定上升趋势：
- 均线多头排列（MA5 > MA10 > MA20 > MA30 > MA60）
- 价格站在所有均线之上
- 60日最大回撤在可控范围内

### 2. 趋势分析 (代号: 3)

包含三种趋势规则：
- **趋势跟随**: MA20 > MA60，斜率为正，价格 > MA20
- **上升回撤**: 上升趋势中的回调，RSI在40-55区间
- **波动收缩突破**: 布林带收窄后突破，放量确认

### 3. 网格测试 (代号: 4)

对波动收缩突破参数进行网格搜索优化，找出最优参数组合。

### 4. 玄学指标 (代号: x)

基于连续阳线模式的信号：
- **6连阳+1阴**: 10天窗口内存在此模式
- **连续6阳**: 最近6天全部阳线

## 玄学指标优先级

| 优先级 | 标记 | 条件 | 含义 |
|--------|------|------|------|
| 1 | ⭐买入 | 6连阳后阴线 | 最佳买入机会，立即行动 |
| 2 | ★等待 | 第6天阳线 | 等明天回调再买 |
| 3 | 无标记 | 其他情况 | 普通信号 |

## 组合策略

系统支持多种分析器的组合：

| 组合代号 | 说明 | 组合条件 |
|----------|------|----------|
| 134 | 最严格 | 稳步上升 + 趋势分析 + 网格测试 |
| 13 | 稳步+趋势 | 稳步上升 + 趋势分析 |
| 34 | 趋势+网格 | 趋势分析 + 网格测试 |
| 14 | 稳步+网格 | 稳步上升 + 网格测试 |
| 1 | 仅稳步 | 稳步上升 |
| 4 | 仅网格 | 网格测试 |

每种组合同时支持两种玄学条件：
- `_6`: 连续6天阳线
- `_61`: 近10天6涨1跌

## 命令行参数

```bash
python main.py [选项]

选项:
  --skip-fetch          跳过数据获取，使用已有分析结果
  --only-report         仅生成报告（需要已有分析结果）
  --analyzers ANALYZERS 指定分析器: 1=稳步上升, 3=趋势, 4=网格, x=玄学
  --limit LIMIT         限制扫描股票数量
  --output-dir DIR      输出目录
  --grid-horizon N      网格测试收益周期（默认20天）
```

## 输出文件

每次运行会在 `output/YYYY-MM-DD/HH-MM-SS/` 目录下生成：

### CSV文件
- `xuanxue_XXX_N只_baseon_MMDDYYYY_YYYYMMDD_HHMMSS.csv`

### MD报告
- `xuanxue_XXX_N只_baseon_MMDDYYYY_YYYYMMDD_HHMMSS.md`
- `summary_report_YYYYMMDD_HHMMSS.md`

### HTML报告
- `xuanxue_XXX_N只_YYYYMMDD_HHMMSS.html` - 可交互，点击股票直接打开东方财富页面
- `summary_YYYYMMDD_HHMMSS.html` - 总览页面

## 旧版脚本（兼容）

以下脚本仍可单独使用：

```bash
# 稳步上升扫描
python scan_steady_uptrend.py --only-signal

# 趋势分析
python trend_rules_analyzer.py --limit 100

# 网格测试
python grid_test_vol_contraction.py

# 玄学联合筛选（旧版）
python xuanxue_134_filter.py
```

## 数据来源

系统使用 `just-stock-down/data/` 目录下的本地数据，不执行任何数据抓取。

## 更新日志

### v2.0 (2026-01-29)
- 重构代码架构，分离分析器/组合器/报告生成器
- 新增HTML报告，支持交互式查看
- 优化优先级显示，追涨改为等待
- 新增主程序入口 main.py

### v1.0
- 初始版本，包含各独立分析脚本

