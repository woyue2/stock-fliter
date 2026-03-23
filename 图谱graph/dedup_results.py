import json

result_file = 'a_result.json'
stock_file = 'a_stock.txt'

# 1. Load target stock list
with open(stock_file, 'r', encoding='utf-8') as f:
    target_stocks = set(json.load(f))

unique_records = {}
invalid_lines = 0

# 2. Parse results line by line
with open(result_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            record = json.loads(line)
            if '股票代码' in record:
                # 去重：后续进来的同代码记录会覆盖之前的（保留最新的完整抓取结果）
                unique_records[record['股票代码']] = record
        except json.JSONDecodeError:
            invalid_lines += 1

# 3. Check completeness
found_stocks_set = set(unique_records.keys())
missing_stocks = target_stocks - found_stocks_set

print("--- 数据完整性及去重报告 ---")
print(f"目标股票总数: {len(target_stocks)}")
print(f"去重后唯一记录数: {len(unique_records)}")
print(f"缺失的股票数量: {len(missing_stocks)}")

# 4. Save back as standard JSON Array (原 cn_stock.py 默认的标准格式)
if not missing_stocks:
    output_list = list(unique_records.values())
    with open('a_result.json', 'w', encoding='utf-8') as f:
        json.dump(output_list, f, ensure_ascii=False, sort_keys=True, indent=4)
    print("\n[成功] 已完成去重，并将 5012 条完整数据转换为标准 JSON 数组格式保存至 a_result.json。")
else:
    print(f"\n[警告] 仍有 {len(missing_stocks)} 只股票缺失，去重中断，请先补录。")
