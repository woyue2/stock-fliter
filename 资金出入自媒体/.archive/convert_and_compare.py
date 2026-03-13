"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/convert_and_compare.py, 批量转换通达信 xls 到 csv
[INPUT]: 真实数据/*.xls
[OUTPUT]: 同名 .csv 与 header_comparison.txt
"""
import pandas as pd
import os

def convert_xls_to_csv(file_path):
    try:
        # 通达信导出的 .xls 实际是 GBK 编码的制表符分隔文本
        df = pd.read_csv(file_path, sep='\t', encoding='gbk')
        
        # 生成 csv 文件名
        csv_path = file_path.replace('.xls', '.csv')
        
        # 保存为 UTF-8 编码的 CSV
        df.to_csv(csv_path, index=False, encoding='utf-8-sig') # 使用 utf-8-sig 方便 Excel 直接打开不乱码
        print(f"转换成功: {os.path.basename(file_path)} -> {os.path.basename(csv_path)}")
        return df.columns.tolist()
    except Exception as e:
        print(f"转换 {file_path} 失败: {e}")
        return None

def main():
    base_dir = './真实数据'
    files = [
        '0306Table_1184概念.xls',
        '0306Table_3820行业.xls'
    ]
    
    results = {}
    for f in files:
        full_path = os.path.join(base_dir, f)
        if os.path.exists(full_path):
            headers = convert_xls_to_csv(full_path)
            if headers:
                results[f] = headers
        else:
            print(f"文件不存在: {full_path}")

    # 对比表头并输出到文件
    with open('header_comparison.txt', 'w', encoding='utf-8') as f:
        f.write("======== 表头对比结果 ========\n")
        for filename, headers in results.items():
            f.write(f"\n[{filename}]\n")
            f.write(", ".join(headers) + "\n")

    print("\n所有表头已提取至 header_comparison.txt，请查看。")

if __name__ == '__main__':
    main()
