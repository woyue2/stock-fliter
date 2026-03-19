import pandas as pd
from collections import Counter
import itertools

# =============================================================================
# 1. 数据加载与环境初始化
# =============================================================================

FILE_PATH = "所有股票行业分类；主营；概念 (1).csv"

def load_stock_data(path):
    """
    尝试多种编码加载原始 CSV 数据。
    """
    try:
        # 尝试 UTF-8
        return pd.read_csv(path, encoding='utf-8')
    except UnicodeDecodeError:
        try:
            # 尝试 GBK (同花顺、i问财导出常用编码)
            return pd.read_csv(path, encoding='gbk')
        except Exception as e:
            print(f"Error reading with GBK: {e}")
            # 尝试 UTF-8 with BOM
            return pd.read_csv(path, encoding='utf-8-sig')

df = load_stock_data(FILE_PATH)

# =============================================================================
# 2. 数据结构初探 (Data Inspection)
# =============================================================================

# 打印基本统计信息与前几行
# print(df.info())
# print(df.head())

"""
# [备注：代码输出概览]
# <class 'pandas.core.frame.DataFrame'>
# RangeIndex: 5706 entries, 0 to 5705
# Data columns (total 14 columns):
#  0   股票代码                  5706 non-null   object
#  1   股票简称                  5706 non-null   object
#  2   a股流通市值 (日期格式)         5706 non-null   object
#  ...
#  6   主营产品名称                5706 non-null   object
#  7   所属概念                  5706 non-null   object
#  13  所属同花顺行业               5706 non-null   object
"""

# =============================================================================
# 3. 基础板块/概念关联分析 (Concept Co-occurrence Analysis)
# =============================================================================

def analyze_concept_correlation(df, target_concept, top_n=10, ignore_generic=True):
    """
    查找与目标概念 (target_concept) 最常共同出现的伴生概念。
    """
    # 忽略融资融券、深股通等无选股参考价值的通用标签
    ignore_tags = ['融资融券', '深股通', '沪股通', '国企改革', '专精特新', '新股与次新股', '注册制次新股'] if ignore_generic else []
    
    # 清理并提取概念列表
    all_concepts_series = df['所属概念'].dropna().apply(lambda x: x.split(';'))
    
    related_list = []
    for concepts in all_concepts_series:
        if target_concept in concepts:
            # 提取除目标概念和通用标签以外的概念
            related_list.extend([c for c in concepts if c != target_concept and c not in ignore_tags])
    
    return Counter(related_list).most_common(top_n)

# 示例分析: 低空经济
print("--- 示例分析: 低空经济 ---")
top_related_low_altitude = analyze_concept_correlation(df, '低空经济')
for concept, count in top_related_low_altitude:
    print(f"- {concept}: {count} times")

# 示例分析: 新能源汽车
print("\n--- 示例分析: 新能源汽车 ---")
top_related_new_energy = analyze_concept_correlation(df, '新能源汽车', top_n=5)
for concept, count in top_related_new_energy:
    print(f"- {concept}: {count} times")

# =============================================================================
# 4. 自动化生成热点图谱数据 (Association Map Generation)
# =============================================================================

hot_topics = ['低空经济', '人工智能', '人形机器人', '储能', '固态电池']
results = []

for topic in hot_topics:
    related = analyze_concept_correlation(df, topic, top_n=5)
    # 格式化关联结果
    related_str = ", ".join([f"{c}({count})" for c, count in related])
    results.append({'热门风口': topic, '最强关联/上下游概念': related_str})

# 导出分析结果
output_df = pd.DataFrame(results)
output_name = '热点关联图谱_示例.csv'
output_df.to_csv(output_name, index=False, encoding='utf-8-sig')
print(f"\n[OK] 成功保存热点关联数据至: {output_name}")

# =============================================================================
# 5. 可视化预览 (Markdown Table Output)
# =============================================================================

# print("\n[关联图谱预览]")
# print(output_df.to_markdown(index=False))

"""
# [备注：最终图谱预览结果]
| 热门风口   | 最强关联/上下游概念                                                    |
|:-------|:--------------------------------------------------------------|
| 低空经济   | 机器人概念(226), 无人机(224), 新能源汽车(194), 华为概念(177), 军工(175)          |
| 人工智能   | DeepSeek概念(515), 华为概念(461), AI应用(415), 机器人概念(404), AI智能体(368) |
| 人形机器人  | 机器人概念(376), 新能源汽车(244), 比亚迪概念(169), 华为概念(141), 储能(127)        |
...
"""