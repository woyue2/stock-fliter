"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/gen_pro_report.py, 量化雷达自媒体报告（Pro版）自动化提取生成引擎
[INPUT]: output/Analyzed_THS_*.csv
[OUTPUT]: output/Pro_Report_*.html
"""
import pandas as pd
import os
import glob
import re
from datetime import datetime

def gen_pro_report():
    print("================ 🚀 极简量化终端生成器 V3.0 ================")
    
    # 获取脚本所在目录，确保从任何地方运行都能找到文件
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

    # ① 狙击机会 (买点): 抢筹、建仓、吸筹 (主力扫货) + 恐慌错杀 (超跌反弹)
    # 取最强势的板块
    buy_strong_mask = df['主力行为'].str.contains('抢筹|建仓|吸筹', na=False) & ~df['主力行为'].str.contains('假|错杀', na=False)
    buy_strong = df[buy_strong_mask].sort_values(by='主力强度', ascending=False)
    
    # 取跌得最惨的恐慌错杀板块
    gold_mask = df['主力行为'].str.contains('错杀', na=False) & ~df['主力行为'].str.contains('假洗盘|假建仓|假抢筹|诱多', na=False)
    gold_list = df[gold_mask].sort_values(by='主力强度', ascending=True)
    
    buy_list = pd.concat([buy_strong, gold_list])

    # ② 坚定持股 (防洗盘): 真洗盘
    hold_mask = df['主力行为'].str.contains('真洗盘', na=False)
    # 使用转换后的纯数值进行真实金额大小排序
    hold_list = df[hold_mask].sort_values(by='散户净额_数值', ascending=True)

    # ③ 避险止损 (逃顶): 真出货 + 诱多/假抢筹/假洗盘 + 减仓分歧
    sell_mask = df['主力行为'].str.contains('出货|假|诱多|分歧/减仓', na=False) & ~df['主力行为'].str.contains('错杀', na=False)
    sell_list = df[sell_mask].sort_values(by='主力强度', ascending=True)
    
    # 将避险止损进一步拆分为：真跑路 和 陷阱类
    sell_true_mask = sell_list['主力行为'].str.contains('出货|分歧/减仓', na=False)
    sell_fake_mask = sell_list['主力行为'].str.contains('假|诱多', na=False)
    sell_true_list = sell_list[sell_true_mask]
    sell_fake_list = sell_list[sell_fake_mask]

    # 4. 读取 HTML 模板
    template_path = os.path.join(base_dir, 'quant_minimalist.html')
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
            if any(x in behavior for x in ['抢筹', '建仓', '错杀', '吸筹']) and '假' not in behavior:
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
                intensity_color = "#00f59b"
                price_class = "price-up"
            elif '抢筹' in behavior:
                status_text = "🔥 主力爆买"
            elif '吸筹' in behavior:
                status_text = "🕵️ 隐秘吸筹"
                intensity_color = "#00f59b"
            elif '建仓' in behavior:
                status_text = "📈 缓慢吸纳"
            elif '洗盘' in behavior:
                # 极端预判：主力洗盘期间，如果强度为负（股价在磨或者是微跌），则标记为暴力洗盘
                if intensity < 0:
                    status_text = "⚠️ 暴力洗盘 (极限施压)"
                    intensity_color = "#ff4d6d" # 使用预警红，突出其极限性
                else:
                    status_text = "🛡️ 震荡洗浮筹"
                    intensity_color = "#40a9ff"
                price_class = ""
            elif '分歧/减仓' in behavior:
                status_text = "⚖️ 逢高减筹"
                intensity_color = "#ff4d6d"
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
                        <span>研判结果</span>
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

    # 6. 分页策略：每页最多 7 个卡片，且保持大板块不跨页混杂 (提升实战连贯性)
    pages_data = []
    
    # Page 1: 恐慌错杀 (最多 7 条)
    pages_data.append({"title": "1.1 恐慌错杀", "data": gold_list})
    
    # Page 2-4: 典型洗盘 (20 条拆成 3 页)
    pages_data.append({"title": "2.1 典型洗盘 (Page 1)", "data": hold_list.iloc[0:7]})
    pages_data.append({"title": "2.1 典型洗盘 (Page 2)", "data": hold_list.iloc[7:14]})
    pages_data.append({"title": "2.1 典型洗盘 (Page 3)", "data": hold_list.iloc[14:]})
    
    # Page 5-6: 陷阱预警 (11 条拆成 2 页)
    pages_data.append({"title": "3.1 陷阱预警 (Page 1)", "data": sell_fake_list.iloc[0:6]})
    pages_data.append({"title": "3.1 陷阱预警 (Page 2)", "data": sell_fake_list.iloc[6:]})

    # 7. 创建独立文件夹
    start_time = datetime.now().strftime("%m%d_%H%M")
    report_dir = os.path.join(output_dir, f'Report_{start_time}')
    os.makedirs(report_dir, exist_ok=True)
    
    num_pages = len(pages_data)
    
    for i, page in enumerate(pages_data):
        page_num = i + 1
        page_file = f"page_{page_num}.html"
        
        # 构造导航条
        nav_buttons = []
        for n in range(1, num_pages + 1):
            if n == page_num:
                nav_buttons.append(f'<span style="color: var(--accent-green); font-weight: 800; padding: 0 10px;">#{n}</span>')
            else:
                nav_buttons.append(f'<a href="page_{n}.html" style="color: var(--text-secondary); text-decoration: none; padding: 0 10px;">{n}</a>')
        
        pagination_html = "".join(nav_buttons)
        
        # 页面内容填充
        content_html = f"""
        <div class="sub-section-title" style="margin-top: 20px;">{page["title"]}</div>
        <div class="data-list">
            {"".join(build_cards_html(page["data"]))}
        </div>
        """
        
        # 简易替换逻辑
        page_content = template.replace('{{PAGINATION_LINKS}}', pagination_html)
        
        # 清除掉老模板中的大类别 section 骨架
        pattern = r'<!-- 区块.*?</div>\s+<div class="sub-section-title">.*?</div>\s+<div class="data-list">.*?</div>'
        page_content = re.sub(pattern, '', page_content, flags=re.S)
        
        # 在 phone-mockup 的 br 后面注入当前内容 (由于是多处 br，取第一个)
        page_content = page_content.replace('<div class="phone-mockup">\n        <br>', f'<div class="phone-mockup">\n        <br>\n{content_html}')

        with open(os.path.join(report_dir, page_file), 'w', encoding='utf-8') as f:
            f.write(page_content)

    print(f"\n✅ 多页报告已生成至文件夹: {report_dir}")
    print(f"👉 预览首页: {os.path.abspath(os.path.join(report_dir, 'page_1.html'))}")

if __name__ == '__main__':
    gen_pro_report()
