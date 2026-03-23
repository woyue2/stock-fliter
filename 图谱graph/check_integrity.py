import json

result_file = 'a_result.json'
stock_file = 'a_stock.txt'

# 1. Load target stock list
with open(stock_file, 'r', encoding='utf-8') as f:
    target_stocks = set(json.load(f))

valid_records = []
invalid_lines = 0
duplicates = 0

# 2. Parse results
with open(result_file, 'r', encoding='utf-8') as f:
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
            valid_records.append(record)
        except json.JSONDecodeError:
            invalid_lines += 1

# 3. Analyze completeness
found_stocks = []
for r in valid_records:
    if '股票代码' in r:
        found_stocks.append(r['股票代码'])
    else:
        # 尝试查找其他可能表示代码的字段，以防格式变更
        pass

found_stocks_set = set(found_stocks)

if len(found_stocks) != len(found_stocks_set):
    duplicates = len(found_stocks) - len(found_stocks_set)

missing_stocks = target_stocks - found_stocks_set

# 4. Report
print(f"--- 数据完整性检查报告 ---")
print(f"目标股票总数: {len(target_stocks)}")
print(f"文件中的总有效记录数 (包含重复): {len(valid_records)}")
print(f"解析失败的无效行数: {invalid_lines}")
print(f"文件中的唯一股票总数: {len(found_stocks_set)}")
print(f"重复抓取的记录数: {duplicates}")
print(f"缺失的股票数量: {len(missing_stocks)}")

if missing_stocks:
    print(f"\n抽样显示前10个缺失的股票代码: {list(missing_stocks)[:10]}")

if missing_stocks or invalid_lines > 0 or duplicates > 0:
    # 把缺失或失败的写到 missing_stocks.txt 里方便回炉重造
    with open('missing_stocks.txt', 'w', encoding='utf-8') as f:
        json.dump(list(missing_stocks), f, ensure_ascii=False)
    print("\n注: 已将缺失股票的代码保存到 missing_stocks.txt 以备日后重新抓取。")
else:
    print("\n恭喜！所有数据均已完整抓取，没有任何遗漏。")
