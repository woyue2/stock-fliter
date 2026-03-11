import os
import csv
import re
import argparse
import sys
import shutil
from collections import Counter, defaultdict
from pathlib import Path

def parse_raw_to_formatted(raw_file_path, archieve_dir):
    with open(raw_file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    global_stats = []
    parsed_data = []
    current_category = ""
    current_category_stats = ""

    for line in lines:
        # replace tabs with commas if tab separated
        if '\t' in line:
            parts = line.split('\t')
        else:
            parts = line.split(',')
            
        first_part = parts[0].strip()
        
        if first_part.startswith('涨停个数') or first_part.startswith('总晋级率') or \
           first_part.startswith('总炸板率') or first_part.startswith('总竞价涨幅'):
            if '：' in first_part:
                k, v = first_part.split('：', 1)
                global_stats.append((k.strip(), v.strip()))
            else:
                k = '涨停个数'
                v = first_part.replace('涨停个数', '').strip()
                global_stats.append((k, v))
                
        elif '连板' in first_part or '首板' in first_part:
            m = re.match(r'^([^ ]+)\s+(.*)$', first_part)
            if m:
                current_category = m.group(1)
                current_category_stats = m.group(2)
            else:
                current_category = first_part
                current_category_stats = ""
                
        elif first_part == '代码':
            pass
            
        else:
            if len(parts) >= 4:
                code = parts[0].strip()
                if code.isdigit():
                    code = code.zfill(6)
                name = parts[1].strip()
                time = parts[2].strip()
                reason = ",".join(parts[3:]).strip()
                parsed_data.append((current_category, code, name, time, reason, current_category_stats))

    filename = os.path.basename(raw_file_path)
    archieve_path = os.path.join(archieve_dir, filename)
    
    with open(archieve_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['全局指标', '数值', '', '', '', ''])
        for stat in global_stats:
            writer.writerow([stat[0], stat[1], '', '', '', ''])
        
        writer.writerow([])
        writer.writerow(['连板梯队', '代码', '股票名称', '首次涨停', '涨停原因', '梯队统计'])
        for row in parsed_data:
            writer.writerow(row)
            
    return archieve_path, len(parsed_data)

def get_keywords(file_path):
    category_keywords = defaultdict(Counter)
    total_keywords = Counter()
    total_count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        found_header = False
        for row in reader:
            if not row: continue
            if row[0] == '连板梯队' or (len(row) > 2 and row[2] == '股票名称'):
                found_header = True
                continue
            if not found_header: continue
            if len(row) < 5: continue
            
            tier = row[0].strip()
            reason_str = row[4].strip()
            if not reason_str: continue
            
            keywords = [k.strip() for k in reason_str.split('+') if k.strip()]
            category_keywords[tier].update(keywords)
            total_keywords.update(keywords)
            total_count += 1
            
    return total_keywords, category_keywords, total_count

def process_pipeline():
    base_dir = '/mnt/f/QIANQIAN/stock-fliter/连板天梯'
    raw_dir = os.path.join(base_dir, 'raw')
    archieve_dir = os.path.join(base_dir, 'archieve')
    
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(archieve_dir, exist_ok=True)
    
    raw_files = sorted([f for f in os.listdir(raw_dir) if f.endswith('.csv')])
    archieve_files = sorted([f for f in os.listdir(archieve_dir) if f.endswith('.csv')])
    
    if not raw_files:
        print(f"Error: {raw_dir} 中没有找到 csv 文件。请先放入当日数据。")
        return
        
    latest_raw = raw_files[-1]
    raw_path = os.path.join(raw_dir, latest_raw)
    
    print(f"[*] 发现新数据: {latest_raw}，正在格式化并移入 archieve...")
    archieve_path, today_total_count = parse_raw_to_formatted(raw_path, archieve_dir)
    
    # Optional: remove from raw after processing to keep it clean
    os.remove(raw_path)
    print(f"[*] 格式化完成，已移动至: {archieve_path}")
    
    # Get today's stats
    today_total_kw, today_cat_kw, _ = get_keywords(archieve_path)
    
    # Get yesterday's stats (for comparison)
    # Re-read archieve files after moving the new one
    updated_archieve_files = sorted([f for f in os.listdir(archieve_dir) if f.endswith('.csv')])
    yesterday_total_kw = None
    if len(updated_archieve_files) >= 2:
        yesterday_file = updated_archieve_files[-2]  # previous one
        y_path = os.path.join(archieve_dir, yesterday_file)
        yesterday_total_kw, _, yesterday_total_count = get_keywords(y_path)
        print(f"[*] 发现昨日数据: {yesterday_file}，将进行对比分析。")
        
    print("\n" + "="*50)
    print("## 连板天梯深度分析报告")
    print("="*50 + "\n")
    
    # 1. 自动分析：主线逻辑预测
    print("### 💡 1. 潜在主线逻辑预测 (未来 2-3 天)")
    top_overall = today_total_kw.most_common(5)
    print(f"今日最强核心共识概念：")
    for kw, count in top_overall:
        print(f" - **{kw}** ({count}只)")
    print("> **AI解盘**：上述高频板块具有明显的资金虹吸效应。尤其是同时占据高标梯队和首板数量的概念，最有潜力在未来几天持续发酵，成为明确主线，建议优先关注其中的前排换手龙。")
    print()

    # 2. 自动分析：补涨逻辑扩散
    print("### 🚀 2. 补涨逻辑扩散研判 (高低切)")
    high_tiers = [t for t in today_cat_kw.keys() if t != '首板']
    high_keywords = set()
    for t in high_tiers:
        high_keywords.update(today_cat_kw[t].keys())
        
    first_tier_keywords = set(today_cat_kw['首板'].keys())
    
    spreading = high_keywords.intersection(first_tier_keywords)
    if spreading:
        print("发现以下题材存在明显的**高低切（补涨扩散）**迹象（高标连板与首板同时出现）：")
        for kw in spreading:
            high_count = sum(today_cat_kw[t][kw] for t in high_tiers)
            low_count = today_cat_kw['首板'][kw]
            print(f" - **{kw}** (上行梯队 {high_count}只, 首板 {low_count}只)")
        print("> **AI解盘**：这些题材的龙头已经在上方打出高度，底层资金正在按图索骥挖掘首板补涨。可重点潜伏首板中叠加其他热门属性、市值适中且换手健康的个股。")
    else:
        print("未发现明显受高标带动的首板补涨逻辑概念。前排与后排呈现断层或各炒各的。")
    print()

    # 3. 自动分析：题材强度对比 (与昨日)
    print("### 📊 3. 题材情绪强度对比 (与上一交易日)")
    if yesterday_total_kw:
        print(f"昨日总涨停数：{yesterday_total_count}只 | 今日总涨停数：{today_total_count}只")
        trend = "增强 📈" if today_total_count >= yesterday_total_count else "退潮 📉"
        print(f"整体情绪评价：**{trend}**\n")
        
        print("昨日热点今日留存情况：")
        y_top = yesterday_total_kw.most_common(5)
        for kw, y_count in y_top:
            t_count = today_total_kw.get(kw, 0)
            if t_count > y_count:
                print(f" - **{kw}**: {y_count}只 -> {t_count}只 (爆发发酵 ⬆️)")
            elif t_count > 0:
                print(f" - **{kw}**: {y_count}只 -> {t_count}只 (延续/分歧 ➡️)")
            else:
                print(f" - **{kw}**: {y_count}只 -> 0只 (直接被淘汰 ❌)")
        print("> **AI解盘**：发酵增强的题材可继续格局做T，被直接淘汰的题材说明仅是支线轮动一日游，切忌次日接盘。")
    else:
        print("缺少昨日(之前的) CSV 文件用于情绪对比。")
    print()

    # 4. 自动分析：梯队结构探测 (主线确认)
    print("### 🪜 4. 完整梯队结构探测 (主线确认)")
    ladder_stats = defaultdict(set)
    for t, kws in today_cat_kw.items():
        for kw in kws:
            ladder_stats[kw].add(t)
            
    # Filter keywords that appear in at least 2 distinct tiers (including at least one higher than 1st board)
    vibrant_ladders = []
    for kw, tiers in ladder_stats.items():
        if len(tiers) >= 2:
            # Check if it has a high-tier presence
            has_high = any('连板' in t for t in tiers)
            if has_high:
                vibrant_ladders.append((kw, sorted(list(tiers), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 1)))
                
    if vibrant_ladders:
        print("检测到以下具有**梯队层次感**的主线题材（跨多连板身位）：")
        # Sort by number of tiers covered
        vibrant_ladders.sort(key=lambda x: len(x[1]), reverse=True)
        for kw, tiers in vibrant_ladders:
            tier_str = " -> ".join(tiers)
            print(f" - **{kw}** (身位覆盖: {tier_str})")
        print("> **AI解盘**：这种“排队式”分布是确立主线题材的核心标准。覆盖层级越深（跨越首板、二板、三板等），说明该题材的资金合力越强，抗分歧能力也越强。")
    else:
        print("今日暂无明显具有梯队层次感的题材。市场表现为散兵游勇模式。")
    print()

    # Detailed dump
    print("### 📎 附录：各梯队详细分布")
    tiers = sorted(today_cat_kw.keys(), reverse=True) 
    for t in tiers:
        if not t: continue
        print(f"\n#### {t}")
        common = today_cat_kw[t].most_common(15)
        print(", ".join([f"{kw}({c})" for kw, c in common]))

if __name__ == "__main__":
    process_pipeline()
