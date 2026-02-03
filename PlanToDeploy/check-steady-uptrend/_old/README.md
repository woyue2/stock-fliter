# 老版本文件说明

此目录包含已被新架构替代的老版本Python脚本。这些文件不再被 `run.bat` 和 `main.py` 调用。

## 已移动的文件

### 老版本主要脚本
- **xuanxue_134_filter.py** - 老版本玄学联合筛选脚本
  - 被替代为：`combiners/xuanxue_combiner.py`
  
- **scan_steady_uptrend.py** - 老版本稳步上升扫描脚本
  - 被替代为：`analyzers/steady_uptrend_analyzer.py`
  
- **trend_rules_analyzer.py** - 老版本趋势规则分析脚本
  - 被替代为：`analyzers/trend_analyzer.py`

### 辅助工具脚本
- **generate_xuanxue_html.py** - 老版本HTML生成脚本
  - 被替代为：`reporters/html_reporter.py`
  
- **analyze_hit_rate.py** - 命中率分析工具
  - 功能已整合到新架构的报告系统中
  
- **check_steady_overlap.py** - 股票重叠检查工具
  - 辅助分析工具，不在主流程中
  
- **organize_output.py** - 输出整理工具
  - 输出管理已整合到 `pipeline.py` 中
  
- **validate_strategy.py** - 策略验证工具
  - 辅助验证工具，不在主流程中

## 新架构说明

当前项目使用模块化架构：

```
check-steady-uptrend/
├── main.py                    # 入口文件
├── pipeline.py               # 流程管理
├── data_loader.py           # 数据加载
├── indicators.py            # 技术指标
├── mystic_indicators.py     # 玄学指标
├── utils.py                 # 工具函数
├── grid_test_vol_contraction.py  # 网格测试
├── analyzers/               # 分析器模块
│   ├── steady_uptrend_analyzer.py
│   ├── trend_analyzer.py
│   └── grid_analyzer.py
├── combiners/               # 组合器模块
│   └── xuanxue_combiner.py
└── reporters/               # 报告生成器
    ├── markdown_reporter.py
    └── html_reporter.py
```

## 如何使用

新架构统一通过 `run.bat` 或直接运行 `python main.py` 启动，无需单独运行各个脚本。

保留这些文件的原因：
1. 代码参考 - 保留原始实现逻辑
2. 回退选项 - 如果新架构出现问题，可以回退
3. 历史记录 - 了解项目演进过程
