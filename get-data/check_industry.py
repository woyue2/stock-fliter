import pandas as pd

df = pd.read_csv('C:/Users/Administrator/Desktop/Park/stocks-fliter/get-data/data/selected_stocks_all.csv')
print(f'总数: {len(df)}')
print(f'有行业: {len(df[df["industry"].notna() & (df["industry"] != "")])}')
print(f'空行业: {len(df[df["industry"].isna() | (df["industry"] == "")])}')
print('\n行业分布Top 10:')
print(df[df['industry'].notna() & (df['industry'] != '')]['industry'].value_counts().head(10))

