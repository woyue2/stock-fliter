"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/gen_media_report.py, 专门为自媒体流量设计的爆款内容提取脚本
[INPUT]: output/Analyzed_THS_*.csv
[OUTPUT]: output/Media_Ready_Report.md, 公众号/小红书模板文案
"""
import pandas as pd
import os
import glob

def gen_media_report():
    print("================ 🚀 启动自媒体【爆款流量】筛选引擎 ================")
    
    # 找到最新的分析结果
    list_of_files = glob.glob('output/Analyzed_THS_*.csv')
    if not list_of_files:
        print("❌ 找不到分析结果文件，请先运行 run_daily_scan.py")
        return
        
    # 提取日期标记
    import re
    date_match = re.search(r'\d{4}|\d{8}', os.path.basename(latest_file))
    date_str = date_match.group() if date_match else "Daily"
    
    df = pd.read_csv(latest_file)
    
    # --- 核心过滤逻辑 ---
    # ... (与之前一致，仅在输出时体现日期)
    
    # --- 开始生成自媒体文案 ---
    report_path = f'output/Media_Report_{date_str}.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 📅 【{date_str}】量化雷达：主力底牌揭秘\n\n")
        f.write("> 声明：本报告由独家量化引擎生成，只抓取极致数据，决不谈论银行/蓝筹等模棱两可的板块！\n\n")
        
        # 1. 红榜
        f.write("## 🔥 绝密红榜：散户割肉，主力爆买\n")
        f.write(f"今日共锁定 {len(df)} 个行业，仅以下板块符合“高纯度抢筹”标准：\n\n")
        if not win_list.empty:
            for _, row in win_list.iterrows():
                f.write(f"- **{row['板块']}** ｜ 强度: `{row['主力强度']}` ｜ 净额: `{row['主力净额']}` ｜ 判定: `🔥{row['主力行为']}`\n")
        else:
            f.write("- 今日无符合极端建仓标准的板块，建议空仓观望。\n")
            
        # 2. 黑榜
        f.write("\n## ☠️ 避雷黑榜：诱多陷阱或真实撤退\n")
        f.write("不管涨得有多好，只要主力在偷跑，坚决不接最后一棒！\n\n")
        if not loss_list.empty:
            for _, row in loss_list.iterrows():
                # 对于假抢筹也就是诱多的，特别标注
                tag = "⚠️诱多陷阱" if row['主力行为'] == '假抢筹' else "🔴真实撤退"
                f.write(f"- **{row['板块']}** ｜ 强度: `{row['主力强度']}` ｜ 判定: `{tag}`\n")
        else:
            f.write("- 今日暂无大资金大规模出逃迹象。\n")

        # 3. 黄金坑
        if not gold_list.empty:
            f.write("\n## 💡 冰点反转：恐慌错杀黄金坑\n")
            f.write("散户已绝望离场，跌出来的机会，主力正在暗处等待反弹。\n\n")
            for _, row in gold_list.iterrows():
                f.write(f"- **{row['板块']}** ｜ 逻辑: `散户恐慌净流出，主力顺势洗盘` ➡️ `🎯看多反弹`\n")

        f.write("\n---\n💬 **你想知道你手里的板块今天在演哪出戏吗？**\n评论区留言，量化雷达为你单点扫描！\n")

    print(f"\n✅ 爆款内容筛选完成！\n👉 请查看: {os.path.abspath(report_path)}")
    print("\n--- 预览内容 ---")
    print(open(report_path, 'r', encoding='utf-8').read())

if __name__ == '__main__':
    gen_media_report()
