"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/gen_radial_report.py, 量化雷达坐标轴终端（V5黑金版）自动化数据引擎
[INPUT]: output/Analyzed_THS_*.csv
[OUTPUT]: output/Radial_Report_*.html
"""
import pandas as pd
import os
import glob
import json
from datetime import datetime

def gen_radial_report():
    print("================ 🚀 径向终端生成器 V5.0 (黑金版) ================")
    
    # 获取脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, 'output')
    
    # 1. 找到最新的分析结果
    list_of_files = glob.glob(os.path.join(output_dir, 'Analyzed_THS_*.csv'))
    if not list_of_files:
        print(f"❌ 找不到分析结果文件，请检查目录: {output_dir}")
        return
    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"📂 读取数据: {latest_file}")
    
    # 2. 读取数据
    df = pd.read_csv(latest_file)
    
    # 3. 数据分类逻辑 (对齐 playground5 结构)
    # 创建绝对强度用于排序
    df['abs_intensity'] = df['主力强度'].abs()

    # ① 策略狙击: 错杀 (按绝对强度从大到小排)
    snipe_mask = df['主力行为'].str.contains('错杀', na=False) & ~df['主力行为'].str.contains('假|诱多', na=False)
    snipe_df = df[snipe_mask].sort_values(by='abs_intensity', ascending=False)

    # ② 核心持仓: 真洗盘 (按绝对强度从大到小排)
    hold_mask = df['主力行为'].str.contains('真洗盘', na=False)
    hold_df = df[hold_mask].sort_values(by='abs_intensity', ascending=False)

    # ③ 避险雷达: 诱多/假洗盘/假出货 (按绝对强度从大到小排)
    trap_mask = df['主力行为'].str.contains('假|诱多', na=False) & ~df['主力行为'].str.contains('错杀', na=False)
    trap_df = df[trap_mask].sort_values(by='abs_intensity', ascending=False)

    def df_to_items(target_df):
        items = []
        for _, row in target_df.iterrows():
            items.append({
                "name": row['板块'],
                "val": f"{row['主力强度']:+.2f}"
            })
        return items

    def calc_sentiment(target_df, positive_is_good=True):
        if target_df.empty: return "0.0%"
        if positive_is_good:
            pos_count = (target_df['主力强度'] > 0).sum()
        else:
            pos_count = (target_df['主力强度'] < 0).sum()
        return f"{(pos_count / len(target_df) * 100):.1f}%"

    # 4. 构建数据结构
    radial_data = [
        {
            "title": "恐慌错杀监测",
            "color": "#00F59B",
            "sentiment": calc_sentiment(snipe_df),
            "items": df_to_items(snipe_df)
        },
        {
            "title": "主力典型洗盘",
            "color": "#40A9FF",
            "sentiment": calc_sentiment(hold_df),
            "items": df_to_items(hold_df)
        },
        {
            "title": "诱多陷阱预警",
            "color": "#FF4D6D",
            "sentiment": calc_sentiment(trap_df, positive_is_good=False),
            "items": df_to_items(trap_df)
        }
    ]

    # 5. 读取模板并注入
    template_path = os.path.join(base_dir, 'radial_terminal_template.html')
    if not os.path.exists(template_path):
        print(f"❌ 找不到模板文件: {template_path}")
        return
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    final_html = template.replace('"__RADIAL_DATA__"', json.dumps(radial_data, ensure_ascii=False))

    # 6. 保存报告
    timestamp = datetime.now().strftime("%m%d_%H%M")
    output_path = os.path.join(output_dir, f'Radial_Report_{timestamp}.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)

    print(f"\n✅ 径向终端报告已生成: {output_path}")
    print(f"👉 预览地址: {os.path.abspath(output_path)}")

if __name__ == '__main__':
    gen_radial_report()
