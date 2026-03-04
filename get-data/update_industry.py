# -*- coding: utf-8 -*-
"""
更新股票列表信息（行业、板块等）
读取 data/selected_stocks_all.csv，调用 BaoStock 获取行业信息，并保存回原文件。
"""
import sys
import pandas as pd
from pathlib import Path
import baostock as bs
import time
from tqdm import tqdm

# 添加项目根目录到路径以导入 util (如果有需要)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "selected_stocks_all.csv"

def login_baostock():
    lg = bs.login()
    if lg.error_code != '0':
        print(f"login respond error_code:{lg.error_code}")
        print(f"login respond  error_msg:{lg.error_msg}")
        return False
    return True

def logout_baostock():
    bs.logout()

def get_stock_industry(code):
    try:
        rs = bs.query_stock_industry(code=code)
        if rs.error_code == '0' and rs.next():
            # industry_classification, industry_code, industry, industry_alias
            # example: ['申万一级行业', 'SW1', '银行', '银行']
            # baostock returns: updateDate, code, code_name, industry, industryClassification
            # Actually query_stock_industry returns: code, code_name, industry, industryClassification
            # Let's check docs or response. 
            # Baostock docs: code, code_name, industry, industryClassification
            row = rs.get_row_data()
            if len(row) >= 4:
                return row[3] # industry
    except Exception as e:
        pass
    return ""

def main():
    if not CSV_PATH.exists():
        print(f"Error: {CSV_PATH} not found.")
        return

    print(f"Reading {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH, dtype=str)
    
    if "bs_code" not in df.columns:
        # Generate bs_code if missing
        df["bs_code"] = df["code"].apply(lambda x: f"sh.{x}" if x.startswith("6") else f"sz.{x}")

    print("Logging in to BaoStock...")
    if not login_baostock():
        return

    print("Fetching industry info...")
    industries = []
    
    # Check if industry column already exists to resume? 
    # For now, just refetch all to be safe and simple.
    
    total = len(df)
    for idx, row in tqdm(df.iterrows(), total=total):
        bs_code = row["bs_code"]
        ind = get_stock_industry(bs_code)
        industries.append(ind)
        # time.sleep(0.01) # Avoid rate limit if any

    df["industry"] = industries
    
    print("Logging out...")
    logout_baostock()

    print(f"Saving to {CSV_PATH}...")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print("Done.")

if __name__ == "__main__":
    main()
