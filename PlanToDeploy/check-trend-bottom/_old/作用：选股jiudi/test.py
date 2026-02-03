"""
快速测试脚本
测试数据获取和九底计算功能
"""
import sys
import pandas as pd
from pathlib import Path

# 设置UTF-8编码输出
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from data_fetcher import StockDataFetcher
from td_sequential import get_td_signal_info, analyze_resonance

print("=" * 60)
print("🧪 三周期九底系统测试")
print("=" * 60)

# 测试1：获取股票列表
print("\n[测试1] 获取股票列表...")
fetcher = StockDataFetcher()
stock_list = fetcher.get_stock_list()

if stock_list is not None and len(stock_list) > 0:
    print(f"✅ 成功获取 {len(stock_list)} 只股票")
    print(f"前5只股票：")
    print(stock_list.head(5).to_string(index=False))
else:
    print("❌ 获取股票列表失败")
    sys.exit(1)

# 测试2：获取单只股票的三周期数据
print("\n[测试2] 获取单只股票的三周期K线数据...")

# 选择一只成熟的股票（000001平安银行）
target_stock = stock_list[stock_list['code'] == '000001']
if len(target_stock) == 0:
    # 如果没有000001，选择第一只主板股票（6或0开头）
    target_stock = stock_list[(stock_list['code'].str.startswith('6')) | (stock_list['code'].str.startswith('0'))].head(1)

test_code = target_stock.iloc[0]['code']
test_name = target_stock.iloc[0]['name']
print(f"测试股票：{test_code} - {test_name}")

daily_df, weekly_df, monthly_df = fetcher.get_multi_period_data(test_code)

if daily_df is not None:
    print(f"✅ 日K数据：{len(daily_df)} 条")
    print(f"✅ 周K数据：{len(weekly_df)} 条")
    print(f"✅ 月K数据：{len(monthly_df)} 条")

    # 显示最近数据
    print(f"\n日K最近3天：")
    print(daily_df.tail(3)[['close', 'volume']])
else:
    print(f"❌ 获取 {test_code} 数据失败")
    sys.exit(1)

# 测试3：计算TD序列
print("\n[测试3] 计算TD序列（九底）...")
daily_signal = get_td_signal_info(daily_df)
weekly_signal = get_td_signal_info(weekly_df)
monthly_signal = get_td_signal_info(monthly_df)

print(f"✅ 日K当前序列：{daily_signal['current_buy']} (是否九底：{daily_signal['is_buy_setup']})")
print(f"✅ 周K当前序列：{weekly_signal['current_buy']} (是否九底：{weekly_signal['is_buy_setup']})")
print(f"✅ 月K当前序列：{monthly_signal['current_buy']} (是否九底：{monthly_signal['is_buy_setup']})")

# 测试4：分析共振
print("\n[测试4] 分析三周期共振...")
resonance = analyze_resonance(daily_signal, weekly_signal, monthly_signal)

print(f"共振等级：{resonance['resonance_level']}")
print(f"九底周期数：{resonance['jiudi_cycles']}")
print(f"日K有效：{resonance['daily_valid']}")
print(f"周K有效：{resonance['weekly_valid']}")
print(f"月K有效：{resonance['monthly_valid']}")

if resonance['is_resonance']:
    print("🔥🔥🔥 发现三周期九底共振！🔥🔥🔥")
else:
    print("当前股票未达到三周期共振")

print("\n" + "=" * 60)
print("✅ 所有测试通过！系统运行正常")
print("=" * 60)
