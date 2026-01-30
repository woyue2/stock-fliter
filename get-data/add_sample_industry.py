# -*- coding: utf-8 -*-
"""
手动添加示例行业信息
用于测试HTML显示功能
"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "selected_stocks_all.csv"

# 常见股票的行业映射（示例数据）
SAMPLE_INDUSTRIES = {
    '600000': '银行', '600036': '银行', '600015': '银行', '600016': '银行',
    '600028': '石油石化', '600019': '钢铁', '600050': '通信',
    '600030': '证券', '600048': '房地产', '600031': '机械设备',
    '600230': '化工', '600500': '化工', '600722': '化工',
    '601077': '银行', '601298': '港口', '603379': '化工',
    '603898': '家居用品', '688172': '半导体', '688448': '电子',
    '300251': '传媒', '300784': '化工', '300808': '家用电器',
}

def add_sample_industry():
    """添加示例行业信息"""
    if not CSV_PATH.exists():
        print(f"[ERROR] 找不到文件: {CSV_PATH}")
        return False
    
    print(f"[INFO] 读取文件: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, dtype=str)
    
    # 如果没有industry列，创建它
    if 'industry' not in df.columns:
        df['industry'] = ''
    
    print(f"[INFO] 添加示例行业信息...")
    count = 0
    for idx, row in df.iterrows():
        code = str(row['code']).zfill(6)
        if code in SAMPLE_INDUSTRIES:
            df.at[idx, 'industry'] = SAMPLE_INDUSTRIES[code]
            count += 1
    
    print(f"[OK] 成功添加 {count} 只股票的行业信息")
    
    # 保存
    print(f"[INFO] 保存到: {CSV_PATH}")
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    
    print("\n[OK] 完成！这只是示例数据，请提供git仓库位置以恢复完整数据")
    return True

if __name__ == "__main__":
    add_sample_industry()

