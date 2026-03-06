"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/check_columns.py, 检查数据源的字段分布
[INPUT]: 真实数据/0306Table_3820行业.xls, 1184概念.xls
[OUTPUT]: export_fields.txt
"""
import pandas as pd

def check_xls_columns():
    try:
        # 读取行业数据
        df_industry = pd.read_csv('真实数据/0306Table_3820行业.xls', sep='\t', encoding='gbk')
        
        # 读取概念数据
        df_concept = pd.read_csv('真实数据/0306Table_1184概念.xls', sep='\t', encoding='gbk')
        
        with open('export_fields.txt', 'w', encoding='utf-8') as f:
            f.write("======== 3820行业.xls 字段分布 ========\n")
            f.write(str(df_industry.columns.tolist()) + "\n")
            f.write("前两行数据预览:\n")
            f.write(str(df_industry.head(2).to_dict('records')) + "\n")
            
            f.write("\n======== 1184概念.xls 字段分布 ========\n")
            f.write(str(df_concept.columns.tolist()) + "\n")
            f.write("前两行数据预览:\n")
            f.write(str(df_concept.head(2).to_dict('records')) + "\n")
            
        print("执行成功，结果已写入 export_fields.txt")
        
    except Exception as e:
        print("读取出错, 请检查文件路径或格式:", e)

if __name__ == '__main__':
    check_xls_columns()
