# -*- coding: utf-8 -*-
"""
测试网格分析器
"""
from analyzers.grid_analyzer import GridAnalyzer, GridConfig
from pathlib import Path

# 使用自定义配置
config = GridConfig(
    lookback_days=120,
    min_bars=120,
    horizons=[5, 20, 60],
    bb_windows=[20],
    num_stds=[2.0],
    quantiles=[0.2, 0.3, 0.4],
    quantile_windows=[60, 120],
    vol_ratio_thresholds=[1.0, 1.2, 1.5]
)

print("参数配置：")
print(f"  bb_windows: {config.bb_windows}")
print(f"  num_stds: {config.num_stds}")
print(f"  quantiles: {config.quantiles}")
print(f"  quantile_windows: {config.quantile_windows}")
print(f"  vol_ratio_thresholds: {config.vol_ratio_thresholds}")
print(f"  horizons: {config.horizons}")

analyzer = GridAnalyzer(
    limit=100,  # 只测试100只股票
    output_dir=Path("output/debug"),
    horizon=20,
    config=config,
    end_date="2026-01-23"
)

# 构建参数网格
param_grid = analyzer._build_param_grid()
print(f"\n参数网格大小: {len(param_grid)}")
print(f"预期总行数: {len(param_grid) * len(config.horizons)}")

print("\n开始运行网格测试（100只股票）...")
result_df, max_date = analyzer.run()

print(f"\n结果DataFrame形状: {result_df.shape}")
print(f"结果列: {list(result_df.columns)}")
print(f"数据最新日期: {max_date}")

if not result_df.empty:
    print("\n前5行结果:")
    print(result_df.head())
else:
    print("\n⚠️ 结果DataFrame为空！")
