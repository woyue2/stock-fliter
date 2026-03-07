import pandas as pd
import os
import glob
import re
from datetime import datetime

def gen_pro_report():
    print("================ 🚀 极简量化终端生成器 V3.0 ================")
    
    # 1. 找到最新的分析结果
    list_of_files = glob.glob('output/Analyzed_THS_*.csv')
    if not list_of_files:
        print("❌ 找不到分析结果文件，请先运行 run_daily_scan.py")
        return
    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"📂 读取数据: {latest_file}")
    
    # 2. 读取数据
    df = pd.read_csv(latest_file)
    
    # 3. 精细分类逻辑：全面覆盖买点、防洗跑、避险三类需求
    # =========================================================
    
    # 修复数据陷阱：金额带单位（万、亿）无法直接按数值系统排序
    def parse_amount(val):
        if pd.isna(val) or val == '-':
            return 0.0
        val_str = str(val).strip()
        try:
            if '万' in val_str:
                return float(val_str.replace('万', '')) * 10000
            elif '亿' in val_str:
                return float(val_str.replace('亿', '')) * 100000000
            else:
                return float(val_str)
        except:
            return 0.0

    df['散户净额_数值'] = df['散户净额(反推)'].apply(parse_amount)

    # ① 狙击机会 (买点): 抢筹、建仓 (主力扫货) + 恐慌错杀 (超跌反弹)
    buy_strong_mask = df['主力行为'].str.contains('抢筹|建仓', na=False) & ~df['主力行为'].str.contains('假|错杀', na=False)
    buy_strong = df[buy_strong_mask].sort_values(by='主力强度', ascending=False)
    
    # 修复 collision：如果包含错杀，必须排除“假”前缀
    gold_mask = df['主力行为'].str.contains('错杀', na=False) & ~df['主力行为'].str.contains('假洗盘|假建仓|假抢筹|诱多', na=False)
    gold_list = df[gold_mask].sort_values(by='主力强度', ascending=True)
    
    buy_list = pd.concat([buy_strong, gold_list])

    # ② 坚定持股 (防洗盘): 真洗盘 (散户交出筹码，主力没走)
    hold_mask = df['主力行为'].str.contains('真洗盘', na=False)
    # 使用转换后的纯数值进行真实金额大小排序
    hold_list = df[hold_mask].sort_values(by='散户净额_数值', ascending=True)

    # ③ 避险止损 (逃顶): 真出货 + 诱多/假抢筹/假洗盘等陷阱
    sell_mask = df['主力行为'].str.contains('出货|假|诱多', na=False) & ~df['主力行为'].str.contains('错杀', na=False)
    sell_list = df[sell_mask].sort_values(by='主力强度', ascending=True)

    # 4. 读取 HTML 模板
    template_path = 'quant_minimalist.html'
    if not os.path.exists(template_path):
        print(f"❌ 找不到模板文件: {template_path}")
        return
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # 5. 通用卡片生成函数
    def build_cards_html(data_list):
        if data_list.empty:
            return '<div style="padding: 20px; text-align: center; color: var(--text-secondary); font-size: 12px;">- 暂无符合条件的板块 -</div>'
            
        html = ""
        for _, row in data_list.iterrows():
            behavior = str(row['主力行为'])
            intensity = float(row['主力强度'])
            
            # 定制化卡片样式
            if any(x in behavior for x in ['抢筹', '建仓', '错杀']) and '假' not in behavior or '错杀' in behavior:
                theme_class = "up"
                price_class = "price-up"
            elif '真洗盘' in behavior:
                theme_class = "up"
                price_class = ""
            else:
                theme_class = "down"
                price_class = "price-down"

            detail_tag = row['备注警示'] if pd.notna(row['备注警示']) and row['备注警示'] != "" else behavior
            intensity_color = ""

            # 状态文案精雕
            if '错杀' in behavior:
                status_text = "🎯 黄金坑低吸"
                intensity_color = "#00f59b" # 用绿色（我们模板的主多颜色）
                price_class = "price-up"
            elif '抢筹' in behavior:
                status_text = "🔥 主力爆买"
            elif '建仓' in behavior:
                status_text = "📈 缓慢吸纳"
            elif '真洗盘' in behavior:
                status_text = "🛡️ 震荡洗浮筹"
                intensity_color = "#40a9ff" # 蓝色代表中性偏多
                price_class = ""
            elif '假' in behavior or '诱多' in behavior:
                status_text = "☢️ 诱多陷阱"
            else:
                status_text = "⚠️ 警惕撤退"

            intensity_style = f"color: {intensity_color};" if intensity_color else ""
            bar_width = min(abs(intensity) * 10, 100)
            if '洗盘' in behavior:
                bar_width = max(20, min(60, bar_width)) # 限制最低视觉长度

            card = f"""
            <div class="card {theme_class}">
                <div class="card-top">
                    <div class="sector-info">
                        <h3>{row['板块']}</h3>
                        <span class="sector-tag">{detail_tag}</span>
                    </div>
                    <div class="main-value {price_class}" style="{intensity_style}">
                        <div class="pct">{intensity:+.2f}</div>
                        <div style="font-size: 10px; font-family: 'JetBrains Mono'; opacity: 0.7;">主力强度</div>
                    </div>
                </div>
                <div class="strength-bar-container">
                    <div class="bar-label">
                        <span>SIGNAL</span>
                        <span>{status_text}</span>
                    </div>
                    <div class="bar-bg">
                        <div class="bar-fill" style="width: {bar_width}%; {'background: '+intensity_color if intensity_color else ''}"></div>
                    </div>
                </div>
            </div>
            """
            html += card
        return html

    # 6. 替换模板变量
    date_str = datetime.now().strftime("%Y.%m.%d %H:%M")
    avg_intensity = df['主力强度'].mean()
    emo_value = f"{50 + avg_intensity * 5:.1f}%"
    emo_class = "price-up" if avg_intensity > 0 else "price-down"

    replacements = {
        "{{REPORT_TITLE}}": "QUANT_RADAR_PRO",
        "{{REPORT_DATE}}": date_str,
        "{{SUBTITLE}}": "Actionable Insights",
        "{{MAIN_TITLE}}": "主力动向<br>作战图谱",
        "{{EMO_CLASS}}": emo_class,
        "{{EMO_VALUE}}": emo_value,
        "{{TOTAL_SECTORS}}": str(len(df)),
        "{{CARDS_BUY}}": build_cards_html(buy_list),
        "{{CARDS_HOLD}}": build_cards_html(hold_list),
        "{{CARDS_SELL}}": build_cards_html(sell_list)
    }

    final_html = template
    for key, val in replacements.items():
        final_html = final_html.replace(key, val)

    # 7. 保存结果
    output_path = f'output/Pro_Report_{datetime.now().strftime("%m%d_%H%M")}.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)

    print(f"\n✅ 极简终端报告生成完成！")
    print(f"👉 预览文件: {os.path.abspath(output_path)}")

if __name__ == '__main__':
    gen_pro_report()
