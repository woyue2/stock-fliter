# 更新日志：修复组合34筛选结果为0的问题

**更新时间**：2026-02-06
**问题**：组合34（趋势分析 + 网格测试）的筛选结果一直是0只，无法使用
**状态**：✅ 已修复并验证成功

---

## 📊 修改前后对比

### 修改前（使用严格参数）
| 组合 | 6连阳 | 近10天6涨1跌 |
|-----|-------|-------------|
| 组合34（原版） | 0只 | 0只 |
| 组合34（容忍版） | 0只 | 0只 |
| 仅网格测试 | 0只 | 0只 |

### 修改后（使用宽松参数）
| 组合 | 6连阳 | 近10天6涨1跌 |
|-----|-------|-------------|
| 组合34（原版） | **14只** | **46只** |
| 组合34（容忍版） | **500只** | **165只** |
| 仅网格测试 | **20只** | **48只** |

---

## 🔧 具体修改内容

### 1. 调整网格测试默认参数

**文件**：`analyzers/grid_analyzer.py`

**修改内容**：将参数从"严格"调整为"宽松"

```python
# 修改前（严格参数）
if self.quantiles is None:
    self.quantiles = [0.1, 0.2, 0.3]  # 波动率必须在历史最低10%-30%
if self.vol_ratio_thresholds is None:
    self.vol_ratio_thresholds = [1.2, 1.5, 1.8]  # 成交量必须放大1.2-1.8倍

# 修改后（宽松参数）
if self.quantiles is None:
    # 宽松参数：允许波动率在历史较低（而非极低）水平
    self.quantiles = [0.2, 0.3, 0.4]  # 波动率在历史较低20%-40%
if self.vol_ratio_thresholds is None:
    # 宽松参数：降低成交量放大要求
    self.vol_ratio_thresholds = [1.0, 1.2, 1.5]  # 成交量只需1.0-1.5倍
```

**原理说明**：
- `quantile`：布林带带宽的分位数阈值，值越大，允许的波动率越高
  - `0.1` → 只允许波动率在历史最低10%的时刻（极严格）
  - `0.4` → 允许波动率在历史较低40%的时刻（更宽松）
- `vol_ratio_threshold`：成交量放大倍数阈值，值越小，要求越低
  - `1.8` → 成交量必须放大1.8倍（严格）
  - `1.0` → 成交量只需大于平均值（宽松）

---

### 2. 优化参数选择逻辑

**文件**：`combiners/xuanxue_combiner.py`

**修改内容**：从只选平均收益最高改为平衡收益和信号数

```python
# 修改前：只选平均收益最高的参数
df = df.sort_values(by=["avg_return", "count"], ascending=[False, False])
row = df.iloc[0]

# 修改后：从前5名中选信号数最多的参数（平衡收益和覆盖面）
df_top5 = df.sort_values(by="avg_return", ascending=False).head(5)
row = df_top5.sort_values(by="count", ascending=False).iloc[0]
```

**原理说明**：
- 原逻辑：直接选择平均收益最高的参数，可能导致信号数很少
- 新逻辑：先筛选平均收益前5名的参数，再从中选择信号数最多的，平衡了收益和覆盖面

---

### 3. 修复 pipeline.py 中的重复代码和bug

**文件**：`pipeline.py`

**问题**：
- 存在3个重复的 `_run_grid_test` 方法定义
- 第3个版本中返回值解包错误：`df = analyzer.run()` 应该是 `df, max_date = analyzer.run()`

**修改内容**：
```python
# 修改前（错误）
df = analyzer.run()  # analyzer.run() 返回 tuple (df, max_date)
return AnalysisResult(name="grid_test", data=df, ...)

# 修改后（正确）
df, max_date = analyzer.run()  # 正确解包
return AnalysisResult(name="grid_test", data=df, ...)
```

**影响**：之前的错误导致 `grid_result.data` 是一个 tuple 而不是 DataFrame，导致后续处理失败。

---

### 4. 添加 end_date 过滤逻辑

**文件**：`combiners/xuanxue_combiner.py`

**修改内容**：在 `_has_vol_contraction_signal` 方法中添加 end_date 过滤

```python
# 添加前：直接加载全部数据
df = load_daily_data(code)

# 添加后：如果配置了end_date，需要过滤数据
df = load_daily_data(code)
if self.config.end_date:
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"] <= self.config.end_date].copy()
```

**原理说明**：
- 网格测试在计算最优参数时使用了 end_date 过滤后的数据
- 组合器在检查信号时也应该使用相同的时间范围，确保数据一致性

---

### 5. 添加 DataFrame 列检查

**文件**：`combiners/xuanxue_combiner.py`

**修改内容**：添加对 "horizon" 列的检查

```python
# 添加前：直接访问列，可能抛出 KeyError
df = df[df["horizon"] == self.config.grid_horizon].copy()

# 添加后：先检查列是否存在
if not isinstance(df, pd.DataFrame) or df.empty:
    return None
if "horizon" not in df.columns:
    return None
df = df[df["horizon"] == self.config.grid_horizon].copy()
```

---

### 6. 修复空DataFrame处理

**文件**：`analyzers/grid_analyzer.py`

**修改内容**：在 `_write_report` 方法中添加空DataFrame检查

```python
# 添加前：直接访问 df["horizon"]，可能抛出 KeyError
for h in self.config.horizons:
    h_df = df[df["horizon"] == h].copy()

# 添加后：先检查DataFrame是否为空或缺少列
if df.empty or "horizon" not in df.columns:
    lines.append("⚠️ 未找到有效的网格测试结果，请检查数据或参数配置。")
    return
for h in self.config.horizons:
    h_df = df[df["horizon"] == h].copy()
```

---

## 📈 修改后的完整结果

### 使用命令
```bash
python main.py --end-date 2026-02-05
```

### 主要组合结果

| 组合 | 条件 | 6连阳 | 近10天6涨1跌 | 说明 |
|-----|------|-------|-------------|------|
| **组合134** | 1+3+4 | 0只 | 2只 | 完整组合（最严格） |
| **组合13** | 1+3 | 1只 | 3只 | MAxRSIx6U1D + 趋势分析 |
| **组合34** | 3+4 | **14只** | **46只** | 趋势分析 + 网格测试 ⭐ |
| **组合3** | 3 | 31只 | 84只 | 仅趋势分析 |
| **组合1** | 1 | 1只 | 3只 | 仅MAxRSIx6U1D |
| **组合4** | 4 | 20只 | 48只 | 仅网格测试 |

### 容忍版结果（允许小跌<1.64%）

| 组合 | 6连阳 | 近10天6涨1跌 | 说明 |
|-----|-------|-------------|------|
| **组合34t** | **500只** | **165只** | 趋势分析 + 网格测试 ⭐ |
| 组合3t | 988只 | 297只 | 仅趋势分析 |
| 组合4t | 647只 | 176只 | 仅网格测试 |

---

## ✅ 验证方法

### 1. 快速测试（10只股票）
```bash
python main.py --end-date 2026-02-05 --test
```

### 2. 全量测试
```bash
python main.py --end-date 2026-02-05
```

### 3. 检查输出
运行完成后检查以下文件：
- `output/2026-02-05/*/xuanxue_34_6_*只_*.csv` - 组合34的6连阳结果
- `output/2026-02-05/*/xuanxue_34_61_*只_*.csv` - 组合34的近10天6涨1跌结果
- `output/2026-02-05/*/summary_*.html` - 总览HTML报告

---

## 🎯 总结

通过以上6项修改，成功解决了组合34筛选结果为0的问题：

1. ✅ 调整参数宽松度（从极严格改为合理宽松）
2. ✅ 优化参数选择逻辑（平衡收益和覆盖面）
3. ✅ 修复代码bug（返回值解包错误）
4. ✅ 添加数据一致性检查（end_date过滤）
5. ✅ 增强容错能力（DataFrame列检查）
6. ✅ 修复空数据处理（KeyError防护）

**组合34现在可以正常使用，能够筛选出合理数量的候选股票！**

---

## 📝 注意事项

### 日期格式
- ❌ 错误：`--end-date 2025-02-05` （过去的一年）
- ✅ 正确：`--end-date 2026-02-05` 或更晚
- ✅ 或者不使用 `--end-date` 参数（使用全部最新数据）

### 参数影响
- 使用宽松参数后，网格测试的信号数量增加，但平均收益可能会略微下降
- 这是为了在收益和覆盖面之间取得平衡
- 如果需要更严格的筛选，可以手动调整 `analyzers/grid_analyzer.py` 中的参数

### 性能说明
- 全量扫描约5000只股票，耗时约1-2分钟
- 主要时间消耗在趋势分析和MAxRSIx6U1D分析上
- 网格测试使用多进程并行，速度很快
