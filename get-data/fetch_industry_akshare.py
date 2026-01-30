# -*- coding: utf-8 -*-
"""
使用 akshare 获取股票行业信息并更新 selected_stocks_all.csv
"""
import sys
from pathlib import Path
import pandas as pd
import akshare as ak
from tqdm import tqdm
import time

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "selected_stocks_all.csv"


def get_stock_industry_map():
    """
    获取所有股票的行业信息映射
    使用 akshare 的 stock_info_a_code_name 获取股票基本信息
    """
    print("正在从 akshare 获取股票行业信息...")
    try:
        # 获取A股股票信息（包含行业）
        stock_info_df = ak.stock_info_a_code_name()
        
        # 创建代码到行业的映射
        industry_map = {}
        if 'code' in stock_info_df.columns and 'industry' in stock_info_df.columns:
            for _, row in stock_info_df.iterrows():
                code = str(row['code']).zfill(6)
                industry = str(row.get('industry', ''))
                industry_map[code] = industry
        
        print(f"[OK] 成功获取 {len(industry_map)} 只股票的行业信息")
        return industry_map
    except Exception as e:
        print(f"[ERROR] 获取行业信息失败: {e}")
        print("尝试使用备用方法...")
        return get_industry_from_individual_stock()


def get_industry_from_individual_stock():
    """
    备用方法：从个股信息中获取行业
    """
    try:
        # 获取沪深京A股列表
        stock_zh_a_spot_df = ak.stock_zh_a_spot_em()
        
        industry_map = {}
        if '代码' in stock_zh_a_spot_df.columns and '行业' in stock_zh_a_spot_df.columns:
            for _, row in stock_zh_a_spot_df.iterrows():
                code = str(row['代码']).zfill(6)
                industry = str(row.get('行业', ''))
                industry_map[code] = industry
        
        print(f"[OK] 备用方法成功获取 {len(industry_map)} 只股票的行业信息")
        return industry_map
    except Exception as e:
        print(f"[ERROR] 备用方法也失败: {e}")
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
    print("\n[INFO] 行业分布统计（Top 10）:")
    industry_counts = df['industry'].value_counts().head(10)
    for industry, count in industry_counts.items():
        if industry:
            print(f"  {industry}: {count} 只")
    
    empty_count = len(df[df['industry'] == ''])
    if empty_count > 0:
        print(f"\n[WARN] {empty_count} 只股票未找到行业信息")
    
    print("\n[OK] 完成！")
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("股票行业信息更新工具 (使用 akshare)")
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

