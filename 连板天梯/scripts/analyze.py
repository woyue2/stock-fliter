import os
import csv
import re
import argparse
import sys
import shutil
from collections import Counter, defaultdict
from pathlib import Path

# Mapping of cities or keywords to provinces
KEYWORD_TO_PROVINCE = {
    '北京': '北京', '上海': '上海', '天津': '天津', '重庆': '重庆',
    '河北': '河北', '山西': '山西', '辽宁': '辽宁', '吉林': '吉林', '黑龙江': '黑龙江',
    '江苏': '江苏', '浙江': '浙江', '安徽': '安徽', '福建': '福建', '江西': '江西', '山东': '山东',
    '河南': '河南', '湖北': '湖北', '湖南': '湖南', '广东': '广东', '海南': '海南',
    '四川': '四川', '贵州': '贵州', '云南': '云南', '陕西': '陕西', '甘肃': '甘肃', '青海': '青海',
    '内蒙古': '内蒙古', '广西': '广西', '西藏': '西藏', '宁夏': '宁夏', '新疆': '新疆',
    '深圳': '广东', '青岛': '山东', '宁波': '浙江', '厦门': '福建', '大连': '辽宁',
    '南京': '江苏', '苏州': '江苏', '无锡': '江苏', '江阴': '江苏', '泰州': '江苏', '南通': '江苏',
    '杭州': '浙江', '金华': '浙江', '烟台': '山东', '潍坊': '山东', '济南': '山东',
    '郑州': '河南', '洛阳': '河南',
    '西安': '陕西', '宝鸡': '陕西',
    '广州': '广东', '珠海': '广东', '东莞': '广东', '佛山': '广东',
    '成都': '四川', '绵阳': '四川',
    '长沙': '湖南', '株洲': '湖南',
    '武汉': '湖北', '襄阳': '湖北',
    '合肥': '安徽', '马鞍山': '安徽',
    '福州': '福建', '泉州': '福建',
    '南昌': '江西', '昆明': '云南',
    '哈尔滨': '黑龙江', '沈阳': '辽宁', '长春': '吉林', '呼和浩特': '内蒙古'
}

import json

# Load mapping from external JSON
MAP_FILE = os.path.join(os.path.dirname(__file__), 'region_map.json')
try:
    with open(MAP_FILE, 'r', encoding='utf-8') as f:
        STOCK_MAPPING = json.load(f)
except Exception:
    STOCK_MAPPING = {}

def get_region(code, name, reason):
    # 1. Manual mapping (external JSON)
    if code in STOCK_MAPPING:
        return STOCK_MAPPING[code]
    
    # 2. Specific keywords (State-owned)
    m = re.search(r'([^\+ ]+)(国资|国企)', reason)
    if m:
        city_or_prov = m.group(1)
        for k, p in KEYWORD_TO_PROVINCE.items():
            if k in city_or_prov:
                return p
    
    # 3. Combined string check
    combined = name + " " + reason
    for k, p in KEYWORD_TO_PROVINCE.items():
        if k in combined:
            return p
            
    # 4. Central entities
    if '央企' in reason or '国家电投' in reason:
        return '北京'
    
    # 5. Name prefix heuristics
    provinces = ['江苏', '浙江', '山东', '福建', '广东', '海南', '四川', '湖南', '湖北', '河南', 
                 '河北', '山西', '陕西', '吉林', '广西', '甘肃', '西藏', '新疆', '安徽', '江西', 
                 '青海', '贵州', '云南', '北京', '上海', '天津', '重庆']
    for p in provinces:
        if name.startswith(p):
            return p
    if name.startswith('内蒙'): return '内蒙古'
    if name.startswith('宁夏'): return '宁夏'
    if name.startswith('黑龙'): return '黑龙江'
    
    return "未知"

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
                # Detection: If it's a pre-formatted CSV, the 'Code' is in parts[1]
                # If it's raw software text, the 'Code' is in parts[0]
                if len(parts) >= 6 and parts[1].isdigit() and len(parts[1]) == 6:
                    # This is likely a pre-formatted CSV
                    code = parts[1].strip()
                    name = parts[2].strip()
                    # Remove any existing region suffix from name if re-processing
                    name = re.sub(r'\(.*?\)$', '', name)
                    time = parts[3].strip()
                    reason = parts[4].strip()
                else:
                    code = parts[0].strip()
                    if code.isdigit():
                        code = code.zfill(6)
                    name = parts[1].strip()
                    time = parts[2].strip()
                    reason = ",".join(parts[3:]).strip()
                
                region = get_region(code, name, reason)
                display_name = f"{name}({region})"
                
                parsed_data.append((current_category, code, display_name, time, reason, current_category_stats))

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

def get_region_stats(file_path):
    regions = Counter()
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        found_header = False
        for row in reader:
            if not row: continue
            if row[0] == '连板梯队' or (len(row) > 2 and row[2] == '股票名称'):
                found_header = True
                continue
            if not found_header: continue
            if len(row) < 3: continue
            
            name_with_region = row[2].strip()
            m = re.search(r'\(([^)]+)\)$', name_with_region)
            if m:
                regions[m.group(1)] += 1
    return regions

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

    # 5. 自动分析：区域热力分布
    print("### 📍 5. 区域热力分布 (省份垂直统计)")
    region_stats = get_region_stats(archieve_path)
    if region_stats:
        top_regions = region_stats.most_common(8)
        print("今日活跃涨停个股的地区分布：")
        for reg, count in top_regions:
            print(f" - **{reg}**: {count} 只")
        print(f"> **AI解盘**：地区属性有时会触发区域性的政策预期或国资重组预期。当某一地区（如{'、'.join([r for r, c in top_regions[:3]])}）出现异常聚集时，可关注该地区其他尚未起涨的同属性个股。")
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
