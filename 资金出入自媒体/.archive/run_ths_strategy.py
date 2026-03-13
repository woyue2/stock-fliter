"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/run_ths_strategy.py, 同花顺数据专项主力行为分析引擎
[INPUT]: 真实数据/Table-index-redian-0306-ths.csv, Table-money-0306-ths.csv
[OUTPUT]: output/Analyzed_THS_0306.csv
"""
import pandas as pd
import os

def format_money(val):
    if pd.isna(val) or val == 0: return "0"
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 100000000:
        return f"{sign}{val/100000000:.2f}亿"
    elif val >= 10000:
        return f"{sign}{val/10000:.2f}万"
    return f"{sign}{val:.2f}"

def run_ths_analysis():
    print("================ 启动同花顺(THS)数据融合分析引擎 ================")
    
    redian_path = '真实数据/Table-index-redian-0306-ths.csv'
    money_path = '真实数据/Table-money-0306-ths.csv'
    
    if not os.path.exists(redian_path) or not os.path.exists(money_path):
        print("❌ 找不到同花顺的 CSV 文件，请确保 convert_ths.py 已经成功运行。")
        return
        
    try:
        # 1. 加载热点指数表 (含总金额，主力金额)
        df_redian = pd.read_csv(redian_path)
        
        # 2. 加载资金明细表
        # 第一行(index=0)是子表头(如 LIURU, JINGE)，从第二行(index=1)开始是真实数据
        df_money = pd.read_csv(money_path)
        df_money = df_money.iloc[1:].copy() 
        
        # 确保我们要用的列被转成了数字
        # 实时大单统计.2 -> 大单净额
        # 实时中单统计.2 -> 中单净额
        df_money['大单净额'] = pd.to_numeric(df_money['实时大单统计.2'], errors='coerce').fillna(0)
        df_money['中单净额'] = pd.to_numeric(df_money['实时中单统计.2'], errors='coerce').fillna(0)
        
        # 3. 按板块名称合并 (合并前清理前后空格)
        df_redian['板块名称'] = df_redian['板块名称'].astype(str).str.strip()
        df_money['板块名称'] = df_money['Unnamed: 1'].astype(str).str.strip()
        
        df_merge = pd.merge(df_redian, df_money, on='板块名称', how='inner')
        print(f"成功合并了两份表的数据，共匹配到 {len(df_merge)} 个板块。")
        
        results = []
        
        for idx, row in df_merge.iterrows():
            name = row['板块名称']
            
            # 提取基础数据
            try:
                pct_chg_str = str(row['涨幅_x']).replace('%', '')
                pct_chg = float(pct_chg_str)
            except:
                pct_chg = 0.0
                
            total_amount = pd.to_numeric(row['总金额'], errors='coerce')
            main_amount = pd.to_numeric(row['主力金额'], errors='coerce')
            
            if pd.isna(total_amount) or total_amount == 0:
                continue
                
            # 【A维度】：主力强度 = (主力金额 / 总成交额) * 100
            main_ratio = (main_amount / total_amount) * 100
            
            # 【B维度】：反推散户净额
            # 根据买卖平衡零和博弈规则，如果市场粗略划分为大、中、小单
            # 那么 小单净额(散户) ≈ -(大单净额 + 中单净额)
            big_net = row['大单净额']
            mid_net = row['中单净额']
            retail_net = -(big_net + mid_net)
            
            # 【C维度】：中单情绪，这里用中单占总金额的比例
            mid_ratio = (mid_net / total_amount) * 100
            
            # ---- 核心判定逻辑树 (与之前保持一致) ----
            behavior = "未知"
            prediction = "未知"
            warning = ""
            
            # 1. 抢筹区 (A > 3)
            if main_ratio > 3:
                if retail_net < 0:
                    behavior = "真抢筹"
                    prediction = "上涨"
                    if pct_chg > 5:
                        prediction = "冲高回落"
                        warning = "涨幅过大，有透支风险"
                else:
                    behavior = "假抢筹"
                    prediction = "下跌/冲高回落"
                    warning = "散户跟风买入，主力可能反手"
                    
                if mid_ratio > 1.5 and prediction == "上涨":
                    warning += " (中单跟风较重)"

            # 2. 建仓区 (1 <= A <= 3)
            elif 1 <= main_ratio <= 3:
                if retail_net < 0:
                    behavior = "真建仓"
                    prediction = "上涨"
                else:
                    behavior = "假建仓"
                    prediction = "冲高回落"
                    
            # 3. 洗盘区 (-1 <= A < 1)
            elif -1 <= main_ratio < 1:
                if retail_net > 0:
                    behavior = "假洗盘/诱多"
                    prediction = "微跌或回落"
                else:
                    behavior = "真洗盘"
                    prediction = "上涨"
                    
            # 4. 出货区 (A < -1)
            else:
                if retail_net < 0:
                    behavior = "假出货/恐慌错杀"
                    prediction = "超跌反弹"
                    warning = "散户被洗出局时的错杀错跌"
                else:
                    behavior = "真出货"
                    prediction = "继续下跌"
                    warning = "主力真实撤退"
                    
            results.append({
                '代码': str(row.get('Unnamed: 0', '')),
                '板块': name,
                '涨幅': f"{pct_chg}%",
                '成交额': format_money(total_amount),
                '主力净额': format_money(main_amount),
                # 将反推出来的散户也放进来
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
        out_path = os.path.join(out_dir, 'Analyzed_THS_0306.csv')
        
        res_df.to_csv(out_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ 分析完成! 报告已生成至: {os.path.abspath(out_path)}")
        
        print("\n👀 【基于同花顺双表合并的几个典型判定】:")
        focus_df = res_df[res_df['主力行为'].isin(['真抢筹', '真洗盘', '假抢筹'])].head(8)
        print(focus_df[['板块', '涨幅', '主力强度', '散户净额(反推)', '主力行为', '预期']].to_markdown(index=False))
        
    except Exception as e:
        print(f"分析出错: {e}")

if __name__ == '__main__':
    run_ths_analysis()
