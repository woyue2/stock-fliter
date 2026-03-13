"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/compare.py, 对比旧预期和机器新预期
[INPUT]: 0306-板块预期.csv, output/Analyzed_*.csv
[OUTPUT]: comparison_result.csv
"""
import pandas as pd
import os

def compare():
    # Load original expected data
    orig_df = pd.read_csv('0306-板块预期.csv')
    
    # Load analyzed data
    industry_df = pd.read_csv('output/Analyzed_0306Table_3820行业.csv')
    concept_df = pd.read_csv('output/Analyzed_0306Table_1184概念.csv')
    
    # Combine industry and concept, prioritizing industry if duplicates exist (though unlikely for names)
    analyzed_df = pd.concat([industry_df, concept_df]).drop_duplicates(subset=['板块'])
    
    # Merge on expected names
    # Note: Sometimes TongDaXin names have prefixes or slightly diff names, we'll try direct match first
    # Many TongDaXin names might not perfectly match, so we will use contains or exact match.
    
    # Add aliases mapping for mismatched names
    aliases = {
        '港口航运': '航运港口',
        '油气采服': '油服工程',
        '钢铁': '普钢',
        '建筑材料': '装修建材',
        '文化传媒': '影视院线', # 或传媒相关
        '福建': '海峡西岸', # 概念可能叫海峡西岸或福建自贸区
        '卫星导航': '卫星通信', # 或者是 北斗导航
        '煤炭概念': '煤炭开采',
        'PCB概念': '印制电路板',
        '液冷服务器': '液冷概念',
        '短剧游戏': '短剧互动游戏'
    }
    
    comparison = []
    
    for _, row in orig_df.iterrows():
        name = str(row['板块']).strip()
        search_name = aliases.get(name, name)
        
        # Exact match
        match = analyzed_df[analyzed_df['板块'] == search_name]
        
        # If no exact match, try contains
        if match.empty:
            match = analyzed_df[analyzed_df['板块'].str.contains(search_name, na=False)]
            
        # Try original name if alias fail
        if match.empty and search_name != name:
             match = analyzed_df[analyzed_df['板块'].str.contains(name, na=False)]
             
            
        if not match.empty:
            match_row = match.iloc[0]
            
            orig_strength = row['主力强度']
            new_strength = match_row['主力强度']
            
            orig_behavior = str(row['主力行为']).strip()
            new_behavior = str(match_row['主力行为']).strip()
            
            orig_expect = str(row['预期']).strip()
            new_expect = str(match_row['预期']).strip()
            
            comparison.append({
                '板块': name,
                '匹配名称': match_row['板块'],
                '原主力强度': orig_strength,
                '新主力强度': new_strength,
                '强度差值': round(float(new_strength) - float(orig_strength), 2) if not pd.isna(orig_strength) and not pd.isna(new_strength) else 'N/A',
                '原主力行为': orig_behavior,
                '新主力行为': new_behavior,
                '行为是否一致': '是' if orig_behavior in new_behavior or new_behavior in orig_behavior else '否',
                '原预期': orig_expect,
                '新预期': new_expect
            })
        else:
            comparison.append({
                '板块': name,
                '匹配名称': '未找到',
                '原主力强度': row['主力强度'],
                '新主力强度': '',
                '强度差值': '',
                '原主力行为': str(row['主力行为']).strip(),
                '新主力行为': '',
                '行为是否一致': '-',
                '原预期': str(row['预期']).strip(),
                '新预期': ''
            })
            
    comp_df = pd.DataFrame(comparison)
    comp_df.to_csv('comparison_result.csv', index=False, encoding='utf-8-sig')
    
    # Analyze differences
    found = comp_df[comp_df['匹配名称'] != '未找到']
    not_found = comp_df[comp_df['匹配名称'] == '未找到']
    
    print(f"\n总计查找: {len(orig_df)} 个板块")
    print(f"成功匹配: {len(found)} 个")
    print(f"未匹配到: {len(not_found)} 个 (可能名称在通达信中有差异，如'军工'vs'国防军工')")
    
    if len(found) > 0:
        # Check strength difference
        found['强度差值_abs'] = pd.to_numeric(found['强度差值'], errors='coerce').abs()
        large_diff = found[found['强度差值_abs'] > 0.5]
        
        print(f"\n强度差值大于0.5的板块有 {len(large_diff)} 个:")
        if not large_diff.empty:
             print(large_diff[['板块', '原主力强度', '新主力强度', '强度差值']].to_string())
 # ---
        
    print("\n完整对比结果已导出到 comparison_result.csv")
    
    # ---------------- 核心方向结果判定 ----------------
    print("\n================ 终极方向判定对齐率 ================")
    
    def normalize_dir(text):
        text = str(text).strip()
        if any(x in text for x in ['涨', '反弹']): return 'UP'
        elif any(x in text for x in ['跌', '回落', '横盘']): return 'DOWN'
        else: return 'UNKNOWN'
        
    found['原方向'] = found['原预期'].apply(normalize_dir)
    found['新方向'] = found['新预期'].apply(normalize_dir)
    
    valid_dirs = found[(found['原方向'] != 'UNKNOWN') & (found['新方向'] != 'UNKNOWN')]
    
    if len(valid_dirs) > 0:
        match_count = sum(valid_dirs['原方向'] == valid_dirs['新方向'])
        print(f"参与对比的有效方向板块数量: {len(valid_dirs)} 个")
        print(f"最终结果结论 (涨跌方向) 吻合数量: {match_count} 个")
        print(f"🔥 最终结果方向命中率: {(match_count / len(valid_dirs) * 100):.1f}%\n")
        
        diffs = valid_dirs[valid_dirs['原方向'] != valid_dirs['新方向']]
        if not diffs.empty:
            print("--- 方向产生分歧的板块 (原作者看涨，机器看跌，或相反) ---")
            for _, r in diffs.iterrows():
                print(f"{r['板块']}: 原作者[{r['原预期']}] ➡️ 自动判定[{r['新预期']}]")
    else:
        print("未提取到足够的有效预期方向进行比对。")

if __name__ == '__main__':
    compare()
