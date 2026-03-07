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
    
    # 3. 核心逻辑：筛选出最值得展示的板块 (红榜/黑榜/黄金坑)
    # 红榜: 抢筹且强度高
    buy_list = df[df['主力行为'].str.contains('抢筹|建仓', na=False)].sort_values(by='主力强度', ascending=False).head(4)
    # 黑榜: 出货且强度低
    sell_list = df[df['主力行为'].str.contains('出货', na=False)].sort_values(by='主力强度', ascending=True).head(3)
    # 特殊: 黄金坑 (恐慌错杀)
    gold_list = df[df['主力行为'].str.contains('恐慌错杀', na=False)].head(2)

    all_show = pd.concat([buy_list, sell_list, gold_list])

    # 4. 读取 HTML 模板
    template_path = 'quant_minimalist.html'
    if not os.path.exists(template_path):
        print(f"❌ 找不到模板文件: {template_path}")
        return
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # 5. 生成卡片 HTML
    cards_html = ""
    for _, row in all_show.iterrows():
        behavior = str(row['主力行为'])
        intensity = float(row['主力强度'])
        
        # 根据行为定义样式
        is_up = "抢筹" in behavior or "建仓" in behavior or "上涨" in behavior or "反弹" in behavior
        theme_class = "up" if is_up else "down"
        price_class = "price-up" if is_up else "price-down"
        
        # 细节文字
        detail_tag = row['备注警示'] if pd.notna(row['备注警示']) and row['备注警示'] != "" else behavior
        if "恐慌错杀" in behavior:
            status_text = "🎯 超跌反弹"
            intensity_color = "#40a9ff"
            theme_class = "up" # 黄金坑也是看多
            price_class = "" # 用蓝色
            intensity_style = f"color: {intensity_color};"
        elif "抢筹" in behavior:
            status_text = "🔥 极速涌入"
            intensity_style = ""
        elif "出货" in behavior:
            status_text = "⚠️ 警惕撤退"
            intensity_style = ""
        else:
            status_text = "📊 观察中"
            intensity_style = ""

        # 强度进度条占比 (限制在 0-100)
        bar_width = min(abs(intensity) * 10, 100) 
        
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
                        <div class="bar-fill" style="width: {bar_width}%; {'background: '+intensity_color if '恐慌错杀' in behavior else ''}"></div>
                    </div>
                </div>
            </div>
        """
        cards_html += card

    # 6. 替换模板变量
    date_str = datetime.now().strftime("%Y.%m.%d %H:%M")
    
    # 模拟情绪指数 (可以根据主力强度平均值计算)
    avg_intensity = df['主力强度'].mean()
    emo_value = f"{50 + avg_intensity * 5:.1f}%"
    emo_class = "price-up" if avg_intensity > 0 else "price-down"

    replacements = {
        "{{REPORT_TITLE}}": "QUANT_RADAR_PRO",
        "{{REPORT_DATE}}": date_str,
        "{{SUBTITLE}}": "Institutional Grade Insights",
        "{{MAIN_TITLE}}": "主力资金<br>研判雷达",
        "{{EMO_VAL_CLASS}}": emo_class, # 修复模板中可能的命名不一致
        "{{EMO_CLASS}}": emo_class,
        "{{EMO_VALUE}}": emo_value,
        "{{TOTAL_SECTORS}}": str(len(df)),
        "{{CARDS}}": cards_html
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
