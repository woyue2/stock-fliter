import csv

hot_concepts = ['储能', '算力租赁', '存储芯片', '商业航天', '算电协同', '机器人概念', '央企', '液冷', '算力']

stocks_in_img = [
    '藏格矿业', '徐工机械', '中钨高新', '宁波银行', '荣盛石化', 
    '蓝思科技', '迈瑞医疗', '中航电测', '包钢股份', '宝钢股份',
    '中国石化', '三一重工', '北方稀土', '中国船舶', '巨化股份',
    '万华化学', '江西铜业', '江淮汽车', '中金黄金', '山东黄金',
    '福耀玻璃', '中航沈飞', '恒立液压', '国泰君安', '中国铝业',
    '拓普集团', '紫金矿业', '韦尔股份', '华友钴业', '洛阳钼业',
    '金山办公', '寒武纪'
]

# We also check the names directly in case they are different (e.g., 豪威集团 implies 韦尔股份)
csv_path = '/mnt/f/QIANQIAN/stock-fliter/所有板块/所有股票行业分类；主营；概念 (1).csv'

matched = []

with open(csv_path, 'r', encoding='gbk') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if len(row) < 14: continue
        name = row[1].strip()
        concepts = row[7].split(';')
        
        # Check if the stock is in our list
        # using substring match to handle variations
        is_in_img = any(s in name for s in stocks_in_img)
        # Handle special cases in the image
        if '中航成飞' in name or '豪威' in name:
            is_in_img = True
            
        if is_in_img:
            # Check overlap with hot concepts
            overlap = set(hot_concepts) & set(concepts)
            if overlap:
                matched.append((name, row[0][:6], row[13], overlap))

print(f"找到 {len(matched)} 只包含当前热门概念的股票:")
for m in matched:
    print(f"- {m[0]} ({m[1]}) | 热点: {', '.join(m[3])} | 行业: {m[2]}")

