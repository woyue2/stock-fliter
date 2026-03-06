"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/run_strategy.py, 主力强度 A*B*C 策略核心判定逻辑
[INPUT]: 真实数据/*.csv
[OUTPUT]: output/Analyzed_*.csv
"""
import pandas as pd
import os

def parse_money(val_str):
    if pd.isna(val_str): return 0
    val_str = str(val_str).strip()
    sign = 1
    if val_str.startswith('-'):
        sign = -1
        val_str = val_str[1:]
    if '亿' in val_str:
        return sign * float(val_str.replace('亿', '')) * 100000000
    elif '万' in val_str:
        return sign * float(val_str.replace('万', '')) * 10000
    else:
        try:
            return sign * float(val_str)
        except:
            return 0

def format_money(val):
    if val == 0: return ""
    sign_str = "-" if val < 0 else ""
    val = abs(val)
    if val >= 100000000:
        return f"{sign_str}{val/100000000:.2f}亿"
    elif val >= 10000:
        return f"{sign_str}{val/10000:.2f}万"
    else:
        return f"{sign_str}{val:.2f}"

def analyze_strategy(file_path):
    print(f"\n================ 开始分析: {os.path.basename(file_path)} ================")
    
    try:
        df = pd.read_csv(file_path)
        
        # 结果集
        results = []
        
        for index, row in df.iterrows():
            # 获取数值，注意清理潜在的空值
            try:
                name = str(row['名称']).strip()
                pct_chg = float(row['涨幅%'])
                
                # A 维度：主力强度 (超大单 + 大单净占比)
                main_ratio = float(row['超大单净占比%']) + float(row['大单净占比%'])
                
                # B 维度：散户情绪 (小单净占比)
                retail_ratio = float(row['小单净占比%'])
                
                # C 维度：中单情绪 (中单净占比，验证纯度)
                mid_ratio = float(row['中单净占比%'])
                
                # **根据公式反推总成交额**
                # 成交额 = 某项净额 / 某项占比
                amount = 0
                if float(row['小单净占比%']) != 0:
                    net_amount = parse_money(row['小单净额'])
                    amount = net_amount / (float(row['小单净占比%']) / 100)
                elif float(row['大单净占比%']) != 0:
                    net_amount = parse_money(row['大单净额'])
                    amount = net_amount / (float(row['大单净占比%']) / 100)
                elif float(row['超大单净占比%']) != 0:
                    net_amount = parse_money(row['超大单净额'])
                    amount = net_amount / (float(row['超大单净占比%']) / 100)
                
                amount_str = format_money(abs(amount))
                
            except Exception:
                continue # 跳过无效行

            behavior = "未知"
            prediction = "未知"
            warning = ""
            
            # ---------------- 判定逻辑树 ----------------
            
            # 1. 抢筹区 (A > 3)
            if main_ratio > 3:
                if retail_ratio < 0:
                    behavior = "真抢筹"
                    prediction = "上涨"
                    if pct_chg > 5:
                        prediction = "冲高回落"
                        warning = "涨幅过大，有透支风险"
                else:
                    behavior = "假抢筹"
                    prediction = "下跌/冲高回落"
                    warning = "散户跟风买入，主力可能反手"
                    
                # 叠加中单惩罚判定
                if mid_ratio > 1.5 and prediction == "上涨":
                    warning += " (注意：中单跟风较重，纯度打折扣)"

            # 2. 建仓区 (1 <= A <= 3)
            elif 1 <= main_ratio <= 3:
                if retail_ratio < 0:
                    behavior = "真建仓"
                    prediction = "上涨"
                else:
                    behavior = "假建仓"
                    prediction = "冲高回落"
                    
            # 3. 洗盘区 (-1 <= A < 1)
            elif -1 <= main_ratio < 1:
                # 强度大于 0 但散户在买，往往拉不动
                if retail_ratio > 0:
                    behavior = "假洗盘/诱多"
                    prediction = "微跌或回落"
                else:
                    behavior = "真洗盘"
                    prediction = "上涨"
                    
            # 4. 出货区 (A < -1)
            else:
                if retail_ratio < 0:
                    behavior = "假出货/恐慌错杀"
                    prediction = "超跌反弹"
                    warning = "极度恐慌"
                else:
                    behavior = "真出货"
                    prediction = "继续下跌"
                    warning = "主力真实撤退"
            
            # --- 保存结果 ---
            results.append({
                '序号': index + 1,
                '板块': name,
                '涨幅': f"{pct_chg}%",
                '成交额': amount_str,
                '主力净额': str(row.get('主力净流入', '')).strip(),
                '散户净额': str(row.get('小单净额', '')).strip(),
                '主力强度': round(main_ratio, 2),
                '主力行为': behavior,
                '预期': prediction,
                '中单情绪(参考)': round(mid_ratio, 2),
                '备注警示': warning
            })
            
        res_df = pd.DataFrame(results)
        
        # 保存到当前目录的 output/ 里
        out_dir = './output'
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            
        out_name = f"Analyzed_{os.path.basename(file_path)}"
        out_path = os.path.join(out_dir, out_name)
        
        res_df.to_csv(out_path, index=False, encoding='utf-8-sig')
        
        print(f"分析完成! 共处理 {len(res_df)} 个板块。")
        print(f"完整报告已生成至: {os.path.abspath(out_path)}")
        
    except Exception as e:
        print(f"分析出错: {e}")

def main():
    files = [
        '真实数据/0306Table_1184概念.csv',
        '真实数据/0306Table_3820行业.csv'
    ]
    for f in files:
        if os.path.exists(f):
            analyze_strategy(f)
        else:
            print(f"找不到数据文件 {f}，请确认之前已转成了 CSV。")

if __name__ == '__main__':
    main()
