# -*- coding: utf-8 -*-
import os
import pandas as pd
import akshare as ak
import time
from pathlib import Path
from tqdm import tqdm

# 配置路径
BASE_DIR = Path("/mnt/f/QIANQIAN/stock-fliter")
CSV_PATH = BASE_DIR / "get-data" / "data" / "selected_stocks_all.csv"
OUT_DIR = BASE_DIR / "analyze-sector-rotation" / "data" / "sector_minutes"

def synthesize_sector_minute(sector_name, sample_limit=5):
    """
    通过聚合个股分时数据，合成板块的分时走势
    """
    print(f"🚀 开始合成板块 [{sector_name}] 的分时数据...")
    
    # 1. 寻找板块成员
    if not CSV_PATH.exists():
        print(f"❌ 找不到股票总表: {CSV_PATH}")
        return
    
    df_all = pd.read_csv(CSV_PATH, dtype=str)
    # 查找包含该概念的股票
    mask = df_all['concepts'].fillna('').str.contains(sector_name)
    members = df_all[mask]
    
    if members.empty:
        print(f"❌ 未找到属于 [{sector_name}] 的样本股")
        return
    
    print(f"📋 该板块共有 {len(members)} 只成分股，选取前 {sample_limit} 只进行采样...")
    sample_codes = members['code'].tolist()[:sample_limit]
    
    all_minutes = []
    
    # 2. 抓取样本股分时
    for code in tqdm(sample_codes, desc="抓取分时数据"):
        symbol = f"sh{code}" if code.startswith('6') else f"sz{code}"
        try:
            # 使用新浪接口获取分时数据 (Period '1' means 1 minute)
            # stock_zh_a_minute returns historical minute data if not specified, 
            # let's use recent data.
            df = ak.stock_zh_a_minute(symbol=symbol, period='1', adjust='qfq')
            if df is not None and not df.empty:
                # 只保留最后 240 个点（一天的交易时间是 240 分钟）
                df = df.tail(240).copy()
                df['day'] = pd.to_datetime(df['day'])
                # 计算相对于开盘（当日起始）的涨幅
                first_price = df.iloc[0]['close']
                df[f'pct_{code}'] = (df['close'] - first_price) / first_price * 100
                df = df.set_index('day')[[f'pct_{code}']]
                all_minutes.append(df)
        except Exception as e:
            print(f"⚠️ 抓取 {code} 失败: {e}")
        time.sleep(0.2) 
    
    if not all_minutes:
        print("❌ 抓取完成，但未获得有效数据")
        return

    # 3. 数据聚合
    print("📊 正在合成板块强度指标...")
    sector_df = pd.concat(all_minutes, axis=1)
    # 填充缺失值（插值）
    sector_df = sector_df.interpolate(method='linear')
    # 计算所有样本的平均涨幅作为板块强度指标 (Strength Index)
    sector_df['sector_strength'] = sector_df.mean(axis=1)
    
    # 4. 保存结果
    today_str = time.strftime("%Y-%m-%d")
    save_path = OUT_DIR / f"{sector_name}_{today_str}.csv"
    sector_df.to_csv(save_path)
    
    print(f"✅ 合成完毕！数据已保存至: {save_path}")
    print("\n【板块分时强度预览 (最后10个时间点)】")
    print(sector_df[['sector_strength']].tail(10))
    
    return sector_df

if __name__ == "__main__":
    # 以“光通信”为例，因为特发信息就在这里
    synthesize_sector_minute("光通信", sample_limit=8)
