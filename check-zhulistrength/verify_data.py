"""
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
[POS]: check-zhulistrength/verify_data.py, 数据字段及精度验证
[INPUT]: 真实数据/0306Table_3820行业.csv
[OUTPUT]: 控制台打印核对结果
"""
import pandas as pd

def verify_formula():
    try:
        # 读取 0306 的行业数据
        df = pd.read_csv('真实数据/0306Table_3820行业.csv')
        
        # 我们挑选几个在之前 0306-板块预期.csv 中出现过的板块来对照
        # 例如：证券、固态电池、电网设备
        targets = ['证券', '固态电池', '电网设备', '算力租赁', '农化制品']
        
        print(f"{'板块名称':<10} | {'主力净占比%':<10} | {'主力强度(原)':<10} | {'结果对比'}")
        print("-" * 60)
        
        # 这里我手动列出 0306-板块预期.csv (截图提取) 的对应强度值用于校对
        original_strength = {
            '证券': 4.99,
            '固态电池': -0.45,
            '电网设备': 0.52,
            '算力租赁': 1.73,
            '农化制品': 5.66
        }
        
        for name in targets:
            row = df[df['名称'] == name]
            if not row.empty:
                # 假设通达信的“主力净占比%”字段存放在“超大单净占比%”和“大单净占比%”之和，或者它本身有一列相关字段
                # 根据之前的 header_comparison.txt，列名是“超大单净占比%”和“大单净占比%”
                main_ratio = row['超大单净占比%'].values[0] + row['大单净占比%'].values[0]
                orig = original_strength.get(name, "N/A")
                diff = abs(main_ratio - orig) if isinstance(orig, float) else 0
                match = "✅ 吻合" if diff < 0.5 else "❌ 偏差较大"
                
                print(f"{name:<10} | {main_ratio:<12.2f} | {orig:<12} | {match}")
                
                # 顺便打印中单和小单情况，看看是否符合背离逻辑
                print(f"   [细节] 小单占比%: {row['小单净占比%'].values[0]:.2f}, 中单占比%: {row['中单净占比%'].values[0]:.2f}")
    
    except Exception as e:
        print(f"验算出错: {e}")

if __name__ == '__main__':
    verify_formula()
