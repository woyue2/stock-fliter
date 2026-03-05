# -*- coding: utf-8 -*-
"""
[L3] check_industry.py
[ROLE]: 统计已获取行业数据的比例与分布情况
[INPUT]: data/selected_stocks_all.csv
[OUTPUT]: stdout 统计信息
[PROTOCOL]: 变更时更新此头部，然后检查 L2/CLAUDE.md
"""
import pandas as pd
from pathlib import Path

# 获取正确的相对路径
BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / 'data' / 'selected_stocks_all.csv'

if not CSV_PATH.exists():
    print(f"❌ 找不到文件: {CSV_PATH}")
else:
    df = pd.read_csv(CSV_PATH, dtype=str)
    print(f'总数: {len(df)}')
    print(f'有行业: {len(df[df["industry"].notna() & (df["industry"] != "")])}')
    print(f'空行业: {len(df[df["industry"].isna() | (df["industry"] == "")])}')
    print('\n行业分布Top 10:')
    # 转换为 numeric 统计前过滤空值
    valid_industry = df[df['industry'].notna() & (df['industry'] != '')]
    print(valid_industry['industry'].value_counts().head(10))

