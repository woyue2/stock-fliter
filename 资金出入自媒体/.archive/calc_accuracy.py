"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/calc_accuracy.py, 计算新旧预期的对比命中率
[INPUT]: comparison_result.csv
[OUTPUT]: 控制台打印命中率报告
"""
import pandas as pd

def calc_accuracy():
    try:
        df = pd.read_csv('comparison_result.csv')
        # 只要成功匹配到的
        valid_df = df[df['匹配名称'] != '未找到'].copy()
        
        # 将原预期和新预期统一化，提取核心方向
        # 上涨类: "上涨", "微涨", "超跌反弹"
        # 下跌/回落类: "下跌", "微跌", "冲高回落", "微跌或回落", "继续下跌", "横盘" (偏弱势)
        
        def normalize_direction(exp_str):
            exp_str = str(exp_str).strip()
            if any(x in exp_str for x in ['涨', '反弹']):
                return 'UP'
            elif any(x in exp_str for x in ['跌', '回落', '横盘']):
                return 'DOWN'
            else:
                return 'UNKNOWN'
                
        valid_df['orig_dir'] = valid_df['原预期'].apply(normalize_direction)
        valid_df['new_dir'] = valid_df['新预期'].apply(normalize_direction)
        
        # 过滤掉无法识别的方向（如都是空值）
        filtered_df = valid_df[(valid_df['orig_dir'] != 'UNKNOWN') & (valid_df['new_dir'] != 'UNKNOWN')]
        
        total = len(filtered_df)
        match_count = sum(filtered_df['orig_dir'] == filtered_df['new_dir'])
        
        # 详细情况
        match_detail = filtered_df[filtered_df['orig_dir'] == filtered_df['new_dir']]
        diff_detail = filtered_df[filtered_df['orig_dir'] != filtered_df['new_dir']]
        
        print(f"\n======== 预期方向命中率评估 ========")
        print(f"参与评估的有效板块数量: {total}")
        print(f"方向一致(都看涨/都看跌): {match_count}")
        print(f"最终大方向命中率: {(match_count / total * 100):.1f}%\n")
        
        print("--- ✅ 判断一致的板块 (共 %d 个) ---" % len(match_detail))
        for _, row in match_detail.iterrows():
            print(f"- {row['板块']}: 原[{row['原预期']}] ➡️ 新[{row['新预期']}]")
            
        print("\n--- ❌ 产生分歧的板块 (共 %d 个) ---" % len(diff_detail))
        for _, row in diff_detail.iterrows():
            print(f"- {row['板块']}: 原[{row['原预期']}] ➡️ 新[{row['新预期']}]")

    except Exception as e:
        print("计算命中率出错:", e)

if __name__ == '__main__':
    calc_accuracy()
