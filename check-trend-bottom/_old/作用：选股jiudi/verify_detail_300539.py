"""
详细验证300539横河精密的9根K线对比
"""
import sys
import io
from pathlib import Path

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

from data_fetcher import StockDataFetcher
from td_sequential import get_td_signal_info
import pandas as pd

print("=" * 100)
print("详细验证 300539 横河精密 的日K九底 - 每一根K线的对比")
print("=" * 100)
print()

# 获取数据
fetcher = StockDataFetcher()
code = '300539'

daily_df, weekly_df, monthly_df = fetcher.get_multi_period_data(code)

# 获取最近的数据，找到九底的9根K线
daily_signal = get_td_signal_info(daily_df)
buy_sequence = daily_signal['buy_sequence']

# 找到序列值为9的位置
jiudi_indices = [i for i, x in enumerate(buy_sequence) if x >= 9]

if not jiudi_indices:
    print("❌ 未找到九底")
    sys.exit(1)

# 取最后一个九底位置
last_jiudi_idx = jiudi_indices[-1]

# 这9根K线的位置：从 last_jiudi_idx - 8 到 last_jiudi_idx
start_idx = last_jiudi_idx - 8
end_idx = last_jiudi_idx

print(f"九底位置：第{end_idx + 1}根K线（从0开始计数）")
print(f"9根K线范围：第{start_idx + 1}到第{end_idx + 1}根")
print()

# 提取这9根K线及前面4根（用于对比）
jiudi_range_start = start_idx - 4  # 多取4根用于对比
jiudi_df = daily_df.iloc[jiudi_range_start:end_idx + 1].copy()
jiudi_seq = buy_sequence[jiudi_range_start:end_idx + 1]

print("九底形成的详细过程（带对比）：")
print("-" * 100)
print(f"{'序号':<6} {'日期':<12} {'收盘价':>10} {'TD序列':>8} {'对比4根前日期':<15} {'对比4根前价格':>15} {'是否满足':>10}")
print("-" * 100)

for i in range(len(jiudi_df)):
    actual_idx = jiudi_range_start + i
    date = jiudi_df.index[i].strftime('%Y-%m-%d')
    close = jiudi_df['close'].iloc[i]
    seq = jiudi_seq[i]

    # 如果序列值>=1，需要对比4根前
    if seq >= 1 and actual_idx >= 4:
        compare_idx = actual_idx - 4
        compare_date = daily_df.index[compare_idx].strftime('%Y-%m-%d')
        compare_price = daily_df['close'].iloc[compare_idx]

        is_satisfied = close < compare_price
        satisfied_str = "✓ 是" if is_satisfied else "✗ 否"

        # 只显示序列1-9的
        if 1 <= seq <= 9:
            print(f"{seq:<6} {date:<12} {close:>10.2f} {seq:>8} {compare_date:<15} {compare_price:>15.2f} {satisfied_str:>10}")
    elif seq == 0:
        # 序列被打断，显示"---"
        if i >= 4:
            # 也可以显示对比
            compare_idx = actual_idx - 4
            compare_date = daily_df.index[compare_idx].strftime('%Y-%m-%d')
            compare_price = daily_df['close'].iloc[compare_idx]
            is_satisfied = close < compare_price
            satisfied_str = "✓ 是" if is_satisfied else "✗ 否（序列重置）"
            print(f"{'-':<6} {date:<12} {close:>10.2f} {seq:>8} {compare_date:<15} {compare_price:>15.2f} {satisfied_str:>10}")
        else:
            print(f"{'-':<6} {date:<12} {close:>10.2f} {seq:>8} {'---':<15} {'---':>15} {'---':>10}")

print("-" * 100)
print()
print("说明：")
print("  - TD序列>=1时，需要满足：当日收盘价 < 4个交易日前收盘价")
print("  - 如果满足，序列+1；如果不满足，序列重置为0")
print("  - 序列连续达到9，即为'九底'")
print()

print("=" * 100)
print("验证结论：")
print("=" * 100)

# 统计9根K线都满足了吗
print()
print("检查九底的9根K线是否都满足条件：")
all_satisfied = True
for seq_num in range(1, 10):  # 序列1-9
    idx_in_jiudi_df = seq_num + 3  # 因为前面有4根用于对比
    if idx_in_jiudi_df < len(jiudi_df):
        actual_idx = jiudi_range_start + idx_in_jiudi_df
        date = jiudi_df.index[idx_in_jiudi_df].strftime('%Y-%m-%d')
        close = jiudi_df['close'].iloc[idx_in_jiudi_df]
        compare_idx = actual_idx - 4
        compare_date = daily_df.index[compare_idx].strftime('%Y-%m-%d')
        compare_price = daily_df['close'].iloc[compare_idx]

        is_satisfied = close < compare_price
        status = "✓" if is_satisfied else "✗"
        if not is_satisfied:
            all_satisfied = False

        print(f"  序列{seq_num}（{date}）：{close:.2f} < {compare_price:.2f}（{compare_date}） [{status}]")

print()
if all_satisfied:
    print("✅ 所有9根K线都满足条件，九底成立！")
else:
    print("❌ 有K线不满足条件，九底不成立！")

print("=" * 100)
