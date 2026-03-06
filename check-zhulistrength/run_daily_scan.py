"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/run_daily_scan.py, 整合版每日同花顺盘后策略运行入口
[INPUT]: input/ 目录下的热点表与资金表 (自动识别 .csv 或被转换的 .xls)
[OUTPUT]: output/ 目录下的当天分析结果 CSV
"""
import pandas as pd
import os
import glob

def format_money(val):
    if pd.isna(val) or val == 0: return "0"
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 100000000:
        return f"{sign}{val/100000000:.2f}亿"
    elif val >= 10000:
        return f"{sign}{val/10000:.2f}万"
    return f"{sign}{val:.2f}"

def ensure_csv(file_path):
    """确保输入的是 CSV，如果是同花顺 xls 则转换"""
    if file_path.endswith('.csv'):
        return file_path
        
    csv_path = file_path.replace('.xls', '.csv')
    if os.path.exists(csv_path):
        return csv_path
        
    # 转换 xls (实为带格式的文本文件)
    print(f"正在转换表格: {os.path.basename(file_path)}")
    try:
        df = pd.read_csv(file_path, sep='\t', encoding='gbk')
        if len(df.columns) <= 1:
            df = pd.read_csv(file_path, sep=',', encoding='gbk')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
        if len(df.columns) <= 1:
            df = pd.read_csv(file_path, sep=',', encoding='utf-8')
    
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    return csv_path

def run_daily_scan():
    print("================ 启动【A*B*C量化】每日盘后扫描 ================")
    
    input_dir = 'input/'
    if not os.path.exists(input_dir):
        print(f"❌ 找不到 {input_dir} 目录。")
        return

    # 自动识别当天的表格
    redian_files = glob.glob(os.path.join(input_dir, '*redian*'))
    money_files = glob.glob(os.path.join(input_dir, '*money*'))
    
    if not redian_files or not money_files:
        print("❌ input/ 目录下缺少【热点表】或【资金表】。请确保是从同花顺导出了这俩文件并塞了进来。")
        return
        
    redian_path = ensure_csv(redian_files[0])
    money_path = ensure_csv(money_files[0])
        
    try:
        # 1. 加载热点指数表
        df_redian = pd.read_csv(redian_path)
        
        # 2. 加载资金明细表 (含表头行处理)
        df_money = pd.read_csv(money_path)
        if '实时大单统计' in df_money.columns and df_money.iloc[0].astype(str).str.contains('LIURU').any():
            df_money = df_money.iloc[1:].copy() 
            
        df_money['大单净额'] = pd.to_numeric(df_money['实时大单统计.2'], errors='coerce').fillna(0)
        df_money['中单净额'] = pd.to_numeric(df_money['实时中单统计.2'], errors='coerce').fillna(0)
        
        # 3. 按板块名称合并
        df_redian['板块名称'] = df_redian['板块名称'].astype(str).str.strip()
        df_money['板块名称'] = df_money['Unnamed: 1'].astype(str).str.strip()
        
        df_merge = pd.merge(df_redian, df_money, on='板块名称', how='inner')
        print(f"✅ 数据加载成功，共匹配 {len(df_merge)} 个板块进行策略研判。")
        
        results = []
        
        for idx, row in df_merge.iterrows():
            name = row['板块名称']
            
            try:
                pct_chg = float(str(row['涨幅_x']).replace('%', ''))
            except:
                pct_chg = 0.0
                
            total_amount = pd.to_numeric(row['总金额'], errors='coerce')
            main_amount = pd.to_numeric(row['主力金额'], errors='coerce')
            
            if pd.isna(total_amount) or total_amount == 0:
                continue
                
            main_ratio = (main_amount / total_amount) * 100
            
            big_net = row['大单净额']
            mid_net = row['中单净额']
            retail_net = -(big_net + mid_net) # 反推散户净额
            
            mid_ratio = (mid_net / total_amount) * 100
            
            # --- 核心判定逻辑树 ---
            behavior, prediction, warning = "未知", "未知", ""
            
            # A > 3 (抢筹)
            if main_ratio > 3:
                if retail_net < 0:
                    behavior = "真抢筹"
                    prediction = "冲高回落" if pct_chg > 5 else "上涨"
                    warning = "涨幅透支风险" if pct_chg > 5 else ""
                else:
                    behavior = "假抢筹"
                    prediction = "下跌/冲高回落"
                    warning = "散户跟风，提防诱多"
                if mid_ratio > 1.5 and prediction == "上涨":
                    warning += " (中单跟风过重)"

            # 1 <= A <= 3 (建仓)
            elif 1 <= main_ratio <= 3:
                if retail_net < 0:
                    behavior = "真建仓"
                    prediction = "上涨"
                else:
                    behavior = "假建仓"
                    prediction = "冲高回落"
                    
            # -1 <= A < 1 (洗盘)
            elif -1 <= main_ratio < 1:
                if retail_net > 0:
                    behavior = "假洗盘/诱多"
                    prediction = "微跌或回落"
                else:
                    behavior = "真洗盘"
                    prediction = "上涨"
                    
            # A < -1 (出货)
            else:
                if retail_net < 0:
                    behavior = "假出货/恐慌错杀"
                    prediction = "超跌反弹"
                    warning = "情绪底/散户被洗错杀"
                else:
                    behavior = "真出货"
                    prediction = "继续下跌"
                    warning = "主力真实派发"
                    
            results.append({
                '代码': str(row.get('Unnamed: 0', '')),
                '板块': name,
                '涨幅': f"{pct_chg}%",
                '成交额': format_money(total_amount),
                '主力净额': format_money(main_amount),
                '散户净额(反推)': format_money(retail_net),
                '主力强度': round(main_ratio, 2),
                '主力行为': behavior,
                '预期': prediction,
                '中单占比(参考)': f"{round(mid_ratio, 2)}%",
                '备注警示': warning
            })
            
        res_df = pd.DataFrame(results)
        
        out_dir = './output'
        os.makedirs(out_dir, exist_ok=True)
        # 截取热点文件名里的日期，如果没有就以 'daily' 命名
        import re
        date_match = re.search(r'\d{4}|\d{8}', os.path.basename(redian_path))
        date_str = date_match.group() if date_match else "daily"
        
        out_path = os.path.join(out_dir, f'Analyzed_THS_{date_str}.csv')
        
        # 结果按强度排序输出更好看
        res_df.sort_values(by='主力强度', ascending=False, inplace=True)
        
        res_df.to_csv(out_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ 策略扫描完成! 过滤后的报告已就绪:\n 👉 {os.path.abspath(out_path)}\n")
        
        print(f"[{date_str}] - 最强『真抢筹/真建仓』榜单先睹为快:")
        focus = res_df[(res_df['主力行为'].isin(['真抢筹', '真建仓'])) & (res_df['预期'] == '上涨')].head(8)
        print(focus[['板块', '涨幅', '主力强度', '散户净额(反推)', '主力行为', '备注警示']].to_markdown(index=False))
        
    except Exception as e:
        print(f"执行出错: {e}")

if __name__ == '__main__':
    run_daily_scan()
