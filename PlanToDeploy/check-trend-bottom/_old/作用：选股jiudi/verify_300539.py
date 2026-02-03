"""
验证300539横河精密的日K九底
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

print("=" * 80)
print("验证 300539 横河精密 的日K九底")
print("=" * 80)
print()

# 获取数据
fetcher = StockDataFetcher()
code = '300539'
name = '横河精密'

print(f"[1] 获取 {code} - {name} 的K线数据...")
daily_df, weekly_df, monthly_df = fetcher.get_multi_period_data(code)

if daily_df is None:
    print("❌ 无法获取数据")
    sys.exit(1)

print(f"✅ 日K数据：{len(daily_df)} 条")
print(f"✅ 周K数据：{len(weekly_df)} 条")
print(f"✅ 月K数据：{len(monthly_df)} 条")
print()

# 计算TD序列
print("[2] 计算TD序列...")
daily_signal = get_td_signal_info(daily_df)
weekly_signal = get_td_signal_info(weekly_df)
monthly_signal = get_td_signal_info(monthly_df)

print(f"✅ 日K当前序列：{daily_signal['current_buy']}")
print(f"✅ 周K当前序列：{weekly_signal['current_buy']}")
print(f"✅ 月K当前序列：{monthly_signal['current_buy']}")
print()

# 详细分析日K九底
print("[3] 详细分析日K九底...")
print(f"日K是否九底：{daily_signal['is_buy_setup']}")

# 获取最近的K线数据和序列
buy_sequence = daily_signal['buy_sequence']
recent_count = 20  # 显示最近20根K线

print()
print("最近20根K线的收盘价和TD序列：")
print("-" * 80)
print(f"{'日期':<12} {'收盘价':>10} {'TD序列':>8} {'说明':>20}")
print("-" * 80)

# 获取最近的数据
recent_df = daily_df.tail(recent_count).copy()
recent_seq = buy_sequence[-recent_count:] if len(buy_sequence) > recent_count else buy_sequence

for i in range(len(recent_df)):
    date = recent_df.index[i].strftime('%Y-%m-%d')
    close = recent_df['close'].iloc[i]
    seq = recent_seq[i]

    # 判断是否满足九底条件（收盘价 < 4根K线前）
    if i >= 4:
        close_4_ago = recent_df['close'].iloc[i-4]
        condition = close < close_4_ago
        condition_str = "✓" if condition else "✗"
    else:
        close_4_ago = None
        condition_str = "-"

    # 标注九底
    if seq >= 9:
        note = f"九底({seq})"
    elif seq >= 7:
        note = f"接近({seq})"
    elif seq > 0:
        note = f"序列{seq}"
    else:
        note = "-"

    print(f"{date:<12} {close:>10.2f} {seq:>8} {note:>20}")

print("-" * 80)
print()

# 检查九底的具体条件
print("[4] 九底条件验证...")
print("九底定义：连续9根K线的收盘价低于4根K线前的收盘价")
print()

# 找到最近的九底位置
if daily_signal['last_jiudi_count'] > 0:
    print(f"✅ 发现历史九底！")
    print(f"   日期：{daily_signal['last_jiudi_date']}")
    print(f"   收盘价：{daily_signal['last_jiudi_price']:.2f}")
    print(f"   序列值：{daily_signal['last_jiudi_count']}")
    print()

# 当前序列
print(f"当前序列分析：")
if daily_signal['current_buy'] >= 9:
    print(f"✅ 当前已达到九底！序列值 = {daily_signal['current_buy']}")
    print(f"   这说明：最近{daily_signal['current_buy']}根K线都满足九底条件")
else:
    print(f"⚠️  当前未达到九底，序列值 = {daily_signal['current_buy']}")
    print(f"   需要序列值 ≥ 9 才算九底")

print()
print("=" * 80)
print("验证结论：")
print("=" * 80)

if daily_signal['is_buy_setup']:
    print(f"✅ 确认：{code} - {name} 的日K确实达到九底！")
    print(f"   当前序列值：{daily_signal['current_buy']}")
    print(f"   分类正确：单周期九底")
else:
    print(f"❌ 错误：{code} - {name} 的日K未达到九底")
    print(f"   当前序列值：{daily_signal['current_buy']} (需要≥9)")
    if daily_signal['current_buy'] >= 7:
        print(f"   建议：应该分类为'接近九底'而非'单周期九底'")

print("=" * 80)
