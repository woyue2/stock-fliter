# -*- coding: utf-8 -*-
"""
[L3] get_industry_util.py
[ROLE]: 获取行业映射信息的底层工具 (AkShare 版)
[INPUT]: AkShare API
[OUTPUT]: selected_stocks_all.csv
[PROTOCOL]: 变更时更新此头部，然后检查 L2/CLAUDE.md

获取股票行业信息工具
使用 akshare 获取行业信息并保存到 selected_stocks_all.csv
"""
import sys
from pathlib import Path
import pandas as pd
import akshare as ak
from tqdm import tqdm
import time

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "selected_stocks_all.csv"


def get_stock_industry_map():
    """
    获取所有股票的行业信息映射
    使用 akshare 的 stock_zh_a_spot_em 获取实时行情（包含行业）
    """
    print("正在从 akshare 获取股票行业信息...")
    
    # 尝试多次获取
    for attempt in range(3):
        try:
            print(f"尝试 {attempt + 1}/3...")
            # 获取沪深京A股实时行情（包含行业）
            stock_df = ak.stock_zh_a_spot_em()
            
            # 创建代码到行业的映射
            industry_map = {}
            if '代码' in stock_df.columns and '行业' in stock_df.columns:
                for _, row in stock_df.iterrows():
                    code = str(row['代码']).zfill(6)
                    industry = str(row.get('行业', ''))
                    if industry and industry != 'nan':
                        industry_map[code] = industry
            
            print(f"[OK] 成功获取 {len(industry_map)} 只股票的行业信息")
            return industry_map
        except Exception as e:
            print(f"[ERROR] 尝试 {attempt + 1} 失败: {e}")
            if attempt < 2:
                print("等待5秒后重试...")
                time.sleep(5)
    
    print("[ERROR] 所有尝试均失败")
    return {}


def update_industry_info():
    """
    更新 CSV 文件中的行业信息
    """
    if not CSV_PATH.exists():
        print(f"[ERROR] 错误: 找不到文件 {CSV_PATH}")
        return False
    
    print(f"[INFO] 读取文件: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, dtype=str)
    
    print(f"[INFO] 当前股票数量: {len(df)}")
    
    # 获取行业信息映射
    industry_map = get_stock_industry_map()
    
    if not industry_map:
        print("[ERROR] 无法获取行业信息，退出")
        return False
    
    # 更新行业列
    print("[INFO] 正在更新行业信息...")
    industries = []
    found_count = 0
    
    for _, row in tqdm(df.iterrows(), total=len(df), desc="更新进度"):
        code = str(row['code']).zfill(6)
        industry = industry_map.get(code, '')
        industries.append(industry)
        if industry:
            found_count += 1
    
    df['industry'] = industries
    
    print(f"[OK] 成功匹配 {found_count}/{len(df)} 只股票的行业信息")
    
    # 保存文件
    print(f"[INFO] 保存到: {CSV_PATH}")
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    
    # 显示统计信息
    print("\n[INFO] 行业分布统计（Top 15）:")
    industry_counts = df[df['industry'] != '']['industry'].value_counts().head(15)
    for industry, count in industry_counts.items():
        print(f"  {industry}: {count} 只")
    
    empty_count = len(df[df['industry'] == ''])
    if empty_count > 0:
        print(f"\n[WARN] {empty_count} 只股票未找到行业信息")
    
    print("\n[OK] 完成！")
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("股票行业信息获取工具 (使用 akshare)")
    print("=" * 60)
    print()
    
    success = update_industry_info()
    
    if success:
        print("\n[OK] 行业信息更新成功！")
        print(f"[INFO] 文件位置: {CSV_PATH}")
    else:
        print("\n[ERROR] 行业信息更新失败")
        sys.exit(1)


if __name__ == "__main__":
    main()

