import pandas as pd

# 读取稳步上升文件
steady = pd.read_csv('output/2026-01-28/23-57-41/steady_uptrend_only_20260128_235741.csv')
print('稳步上升数据:')
print(f'  总数: {len(steady)} 只')
print(f'  满足条件: {steady["steady_uptrend"].sum()} 只')
print(f'  样例: {steady["code"].head(3).tolist()}')

# 读取34_6文件
df34 = pd.read_csv('output/2026-01-29/01-19-55/xuanxue_34_6_23只_baseon_01282026_20260129_011955.csv')
print(f'\nxuanxue_34_6 (趋势+网格+6连阳): {len(df34)} 只')
print(f'  样例: {df34["代码"].head(3).tolist()}')

# 去除代码前缀 (SH./SZ.)
def clean_code(code_str):
    s = str(code_str)
    if '.' in s:
        return s.split('.')[1]
    return s

df34['纯代码'] = df34['代码'].apply(clean_code)

# 检查交集
codes34 = set(df34['纯代码'].astype(str))
scodes = set(steady['code'].astype(str))
common = codes34 & scodes
print(f'\n在稳步上升文件中找到: {len(common)} 只')

if common:
    signals = dict(zip(steady['code'].astype(str), steady['steady_uptrend']))
    print('\n这些股票的稳步上升信号:')
    for c in sorted(common)[:10]:
        name = df34[df34['纯代码']==c]['名称'].values[0]
        signal = signals[c]
        print(f'  {c} {name}: steady_uptrend={signal}')
    
    # 统计有多少满足稳步上升
    satisfied = sum(1 for c in common if signals[c])
    print(f'\n满足稳步上升条件的: {satisfied} 只')
    print(f'不满足稳步上升条件的: {len(common) - satisfied} 只')
else:
    print('\n没有交集！')
