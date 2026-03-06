"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/convert_ths.py, 处理同花顺数据格式转换
[INPUT]: 真实数据/*-ths.xls
[OUTPUT]: 同名 .csv, ths_headers.txt
"""
import pandas as pd
import os

def convert_ths_xls_to_csv(file_path):
    print(f"正在处理: {file_path}")
    try:
        # 同花顺的 xls 导出可能是 gb2312/gbk 编码的 tab 分隔或逗号分隔文本，或者含有其他特殊字符
        # 尝试使用 gbk 和 tab 分隔读取
        try:
            df = pd.read_csv(file_path, sep='\t', encoding='gbk')
            if len(df.columns) <= 1: # 如果按 tab 分隔失败（只有一列），可能是逗号分隔
                df = pd.read_csv(file_path, sep=',', encoding='gbk')
        except UnicodeDecodeError:
            # 如果 gbk 失败，尝试 utf-8
            df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
            if len(df.columns) <= 1:
                df = pd.read_csv(file_path, sep=',', encoding='utf-8')
                
        # 生成 csv 文件名
        csv_path = file_path.replace('.xls', '.csv')
        
        # 保存为 UTF-8 编码的 CSV
        df.to_csv(csv_path, index=False, encoding='utf-8-sig') 
        print(f"✅ 转换成功: {os.path.basename(file_path)} -> {os.path.basename(csv_path)}")
        return df.columns.tolist(), df.head(3)
    except Exception as e:
        print(f"❌ 转换 {file_path} 失败: {e}")
        return None, None

def main():
    base_dir = '/mnt/f/QIANQIAN/stock-fliter/check-zhulistrength/真实数据'
    files = [
        'Table-index-redian-0306-ths.xls',
        'Table-money-0306-ths.xls'
    ]
    
    with open('ths_headers.txt', 'w', encoding='utf-8') as f:
        f.write("======== 同花顺(THS) 表头与数据预览 ========\n")
        
        for file in files:
            full_path = os.path.join(base_dir, file)
            if os.path.exists(full_path):
                headers, preview = convert_ths_xls_to_csv(full_path)
                if headers is not None:
                    f.write(f"\n[{file}] 表头:\n")
                    f.write(", ".join(headers) + "\n\n")
                    f.write(f"数据预览 (前3行):\n")
                    f.write(preview.to_string() + "\n")
                    print(f"提取表头成功: {file}")
            else:
                print(f"⚠️ 文件不存在: {full_path}")

    print("\n所有同花顺表头及前3行数据已提取至 check-zhulistrength/ths_headers.txt，请查看。")

if __name__ == '__main__':
    main()
