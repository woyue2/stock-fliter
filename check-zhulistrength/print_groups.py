import pandas as pd
import glob
import os

list_of_files = glob.glob('output/Analyzed_THS_*.csv')
latest_file = max(list_of_files, key=os.path.getctime)
df = pd.read_csv(latest_file)

print("============ 🎯 狙击机会 (买点) ============")
buy_strong_mask = df['主力行为'].str.contains('抢筹|建仓', na=False) & ~df['主力行为'].str.contains('假|错杀', na=False)
buy_strong = df[buy_strong_mask].sort_values(by='主力强度', ascending=False)
gold_mask = df['主力行为'].str.contains('错杀', na=False)
gold_list = df[gold_mask].sort_values(by='主力强度', ascending=True)

print(f"--- 1. 强买点 ({len(buy_strong)}个) ---")
print(buy_strong[['板块', '主力行为', '主力强度']].to_string(index=False))
print(f"\n--- 2. 恐慌错杀买点 ({len(gold_list)}个) ---")
print(gold_list[['板块', '主力行为', '主力强度']].to_string(index=False))


print("\n============ 🛡️ 坚定持股 (防洗盘) ============")
hold_mask = df['主力行为'].str.contains('真洗盘', na=False)
hold_list = df[hold_mask].sort_values(by='散户净额(反推)', ascending=True)
print(f"--- 3. 真洗盘 ({len(hold_list)}个) ---")
print(hold_list[['板块', '主力行为', '主力强度']].to_string(index=False))


print("\n============ 🛑 避险止损 (逃顶/避坑) ============")
sell_mask = df['主力行为'].str.contains('出货|假|诱多', na=False) & ~df['主力行为'].str.contains('错杀', na=False)
sell_list = df[sell_mask].sort_values(by='主力强度', ascending=True)

# 细分一下：
out_mask = sell_list['主力行为'].str.contains('出货', na=False)
fake_mask = sell_list['主力行为'].str.contains('假|诱多', na=False)

print(f"--- 4. 真出货 ({len(sell_list[out_mask])}个) ---")
print(sell_list[out_mask][['板块', '主力行为', '主力强度']].to_string(index=False))
print(f"\n--- 5. 陷阱/诱多 ({len(sell_list[fake_mask])}个) ---")
print(sell_list[fake_mask][['板块', '主力行为', '主力强度']].to_string(index=False))

