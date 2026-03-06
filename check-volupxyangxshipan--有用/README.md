# check-volupxyangxshipan

VolUp x Yang x Shipan筛选模块（最小可用版）。

筛选规则（按个股最新交易日口径）：

1. 昨天放量：`volume[-1] > volume[-2] && volume[-1] > volume[-3] && volume[-1] > volume[-4]`
2. 今天阳线：`close[0] > open[0]`
3. 同时满足 1 和 2 才命中

其中：
- `0` 表示该股票 CSV 的最新交易日
- `-1` 表示倒数第二个交易日（昨天）
- 每只股票至少需要最近 5 个交易日数据

## 使用方式

```bash
# 全量扫描
python check-volupxyangxshipan/main.py

# 测试模式（前 10 只）
python check-volupxyangxshipan/main.py --test --no-open

# 指定数量
python check-volupxyangxshipan/main.py --limit 50 --no-open

# 不生成 HTML
python check-volupxyangxshipan/main.py --no-html
```

## 输出

输出目录结构：

`check-volupxyangxshipan/output/YYYY-MM-DD/HH-MM-SS/`

主要文件：
- `volupxyangxshipan.csv`
- `summary_YYYYMMDD_HHMMSS.md`
- `summary_YYYYMMDD_HHMMSS.html`

并会追加写入：
- `get-data/data/stocks_index/<日期>/stocks_index.csv`

固定索引字段：
- `模块 = VolUp x Yang x Shipan`
- `策略级别 = 昨放量+今阳线`
