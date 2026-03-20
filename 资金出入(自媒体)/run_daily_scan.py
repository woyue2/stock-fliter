# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  input/ 目录下的表格 (支持红盘/资金分开的双表，或导出的一体化单表)
# OUTPUT: output/ 目录下的当天分析结果 CSV
# POS:    check-zhulistrength/run_daily_scan.py
# -*- coding: utf-8 -*-
"""
整合版每日同花顺盘后策略运行入口
"""
import pandas as pd
import os
import glob
import re

def format_money(val):
    if pd.isna(val) or val == 0: return "0"
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 100000000:
        return f"{sign}{val/100000000:.2f}亿"
    elif val >= 10000:
        return f"{sign}{val/10000:.2f}万"
    return f"{sign}{val:.2f}"

def load_ths_table(file_path):
    """加载同花顺导出的 xls (实为带格式的文本文件) 或 csv"""
    print(f"正在读取: {os.path.basename(file_path)}")
    try:
        # 尝试常用编码和逻辑
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, encoding='utf-8-sig')
        else:
            # XLS 通常是 GBK 编码的制表符分隔文件
            df = pd.read_csv(file_path, sep='\t', encoding='gbk')
            if len(df.columns) <= 1:
                df = pd.read_csv(file_path, sep=',', encoding='gbk')
    except Exception as e:
        print(f"  读取失败: {e}")
        return None
    
    # 清洗表头：如果第一行是列名描述（如 '代码','名称'），排除掉
    if len(df) > 0 and df.iloc[0].astype(str).str.contains('代码|名称|LIURU').any():
        df.columns = df.iloc[0].astype(str)
        df = df.iloc[1:].reset_index(drop=True)
    
    # 清理列名中的空白
    df.columns = [str(c).strip() for c in df.columns]
    return df

def analyze_df(df, source_name):
    """核心研判逻辑"""
    # 1. 字段映射 (适配不同导出习惯)
    mapping = {
        '板块名称': ['名称', '板块名称', 'Unnamed: 1'],
        '涨幅': ['涨幅', 'Unnamed: 3'],
        '总金额': ['金额', '总金额', 'Unnamed: 21'],
        '主力净额': ['净流入', '主力金额', 'Unnamed: 5', '实时大单统计.2'],
        '大单净额': ['实时大单统计.2', 'JINGE_x', '大单净额'],
        '中单净额': ['实时中单统计.2', 'JINGE_y', '中单净额']
    }
    
    def find_col(keys):
        for k in keys:
            if k in df.columns: return k
        return None

    col_name = find_col(mapping['板块名称'])
    col_pct = find_col(mapping['涨幅'])
    col_total = find_col(mapping['总金额'])
    col_main = find_col(mapping['主力净额'])
    col_big = find_col(mapping['大单净额'])
    col_mid = find_col(mapping['中单净额'])

    if not all([col_name, col_pct, col_total, col_main]):
        print(f"  ❌ 文件 {source_name} 关键字段缺失 (需 名称, 涨幅, 金额, 净流入)")
        return None

    results = []
    for _, row in df.iterrows():
        try:
            name = str(row[col_name]).strip()
            if name in ['代码', '名称', 'nan', '']: continue
            
            # 数值解析
            def to_num(v):
                if pd.isna(v): return 0.0
                s = str(v).replace('%', '').replace(',', '').replace('+', '')
                if s == '--' or s == '': return 0.0
                try: return float(s)
                except: return 0.0

            pct_chg = to_num(row[col_pct])
            total_amount = to_num(row[col_total])
            main_amount = to_num(row[col_main])
            big_net = to_num(row[col_big]) if col_big else main_amount
            mid_net = to_num(row[col_mid]) if col_mid else 0.0
            
            if total_amount == 0: continue
            
            # 计算强度指标
            main_ratio = (main_amount / total_amount) * 100
            mid_ratio = (mid_net / total_amount) * 100
            retail_net = -(big_net + mid_net) # 简化反推
            
            # --- 判定逻辑 ---
            behavior, prediction, warning = "观察", "震荡", ""
            
            if main_ratio > 3:
                if retail_net < 0:
                    behavior = "真抢筹" if pct_chg > 0.5 else "主力暗中吸筹"
                    prediction = "上涨"
                    warning = "股价暂未跟随" if pct_chg <= 0.5 else ("涨幅透支风险" if pct_chg > 5 else "")
                else:
                    behavior = "假抢筹"
                    prediction = "看跌/震荡"
                    warning = "散户跟风严重"
            elif 1 <= main_ratio <= 3:
                if retail_net < 0:
                    behavior = "真建仓"
                    prediction = "上涨"
                else:
                    behavior = "假建仓"
                    prediction = "走弱"
            elif -1 <= main_ratio < 1:
                behavior = "真洗盘" if retail_net <= 0 else "诱多洗盘"
                prediction = "上涨" if retail_net <= 0 else "微跌"
            else: # < -1
                if retail_net < 0:
                    behavior = "恐慌错杀"
                    prediction = "反弹"
                else:
                    behavior = "真出货" if pct_chg < -0.2 else "高位派发"
                    prediction = "继续下跌"

            results.append({
                '代码': str(row.get('代码', row.get('Unnamed: 0', ''))),
                '板块': name,
                '涨幅': f"{pct_chg}%",
                '成交额': format_money(total_amount),
                '主力净额': format_money(main_amount),
                '主力强度': round(main_ratio, 2),
                '散户净额(反推)': format_money(retail_net),
                '主力行为': behavior,
                '预期': prediction,
                '备注警示': warning
            })
        except Exception as e:
            continue

    return pd.DataFrame(results)

def run_daily_scan():
    print("================ 启动【A*B*C量化】每日扫描 ================")
    input_dir = 'input/'
    out_dir = 'output/'
    os.makedirs(out_dir, exist_ok=True)

    # 获取所有待处理文件
    xls_files = glob.glob(os.path.join(input_dir, '*.xls'))
    csv_files = glob.glob(os.path.join(input_dir, '*.csv'))
    
    # 优先处理文件名包含数字（日期）的文件
    process_list = sorted(xls_files + csv_files, key=lambda x: re.search(r'\d+', x).group() if re.search(r'\d+', x) else "0")

    if not process_list:
        print("❌ input/ 目录下没有发现可扫描的表格。")
        return

    for file_path in process_list:
        # 跳过旧版 redian/money 对文件 (如果已经有整合版)
        if 'redian' in file_path.lower() or 'money' in file_path.lower():
            if any(('_gn_' in f.lower() or '_hy_' in f.lower()) and re.search(r'\d+', f) == re.search(r'\d+', file_path) for f in process_list):
                 print(f"  跳过旧版分体表: {os.path.basename(file_path)}")
                 continue

        df_raw = load_ths_table(file_path)
        if df_raw is None: continue
        
        res_df = analyze_df(df_raw, os.path.basename(file_path))
        if res_df is not None and len(res_df) > 0:
            # 生成输出文件名
            date_match = re.search(r'\d+', os.path.basename(file_path))
            date_str = date_match.group() if date_match else "scan"
            type_str = "GN" if "gn" in file_path.lower() else ("HY" if "hy" in file_path.lower() else "RES")
            
            out_path = os.path.join(out_dir, f'Analyzed_{type_str}_{date_str}.csv')
            res_df.sort_values(by='主力强度', ascending=False, inplace=True)
            res_df.to_csv(out_path, index=False, encoding='utf-8-sig')
            
            print(f"✅ 完成: {os.path.basename(file_path)} -> {os.path.basename(out_path)}")
            
            # 打印 Top 5
            print(f"--- {os.path.basename(file_path)} 强势榜单 ---")
            top = res_df.head(5)
            if not top.empty:
                print(top[['板块', '涨幅', '主力强度', '主力行为', '预期']].to_markdown(index=False))
            print("\n")

if __name__ == '__main__':
    run_daily_scan()
