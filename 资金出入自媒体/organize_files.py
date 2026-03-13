import os
import shutil

def organize_files():
    base_dir = '/mnt/f/QIANQIAN/stock-fliter/check-zhulistrength'
    
    # 目录定义
    input_dir = os.path.join(base_dir, 'input')
    output_dir = os.path.join(base_dir, 'output')
    archive_dir = os.path.join(base_dir, '.archive')
    
    # 创建目录
    for d in [input_dir, output_dir, archive_dir]:
        os.makedirs(d, exist_ok=True)
        
    # 需要留下的白名单 (其余全扔进 archive)
    whitelist = [
        'input',
        'output',
        '.archive',
        'CLAUDE.md',
        '模板.md',
        '策略.md',
        'README.md',
        'run_daily_scan.py',
        'organize_files.py'
    ]
    
    moved_count = 0
    
    # 遍历当前目录
    for item in os.listdir(base_dir):
        if item in whitelist:
            continue
            
        item_path = os.path.join(base_dir, item)
        archive_path = os.path.join(archive_dir, item)
        
        try:
            shutil.move(item_path, archive_path)
            moved_count += 1
            print(f"已归档: {item}")
        except Exception as e:
            print(f"归档失败 {item}: {e}")
            
    # 特别处理：把最近提取的 THS 数据拷贝到 input 目录作为演示
    demo_money = os.path.join(archive_dir, '真实数据', 'Table-money-0306-ths.csv')
    demo_redian = os.path.join(archive_dir, '真实数据', 'Table-index-redian-0306-ths.csv')
    
    if os.path.exists(demo_money):
        shutil.copy(demo_money, os.path.join(input_dir, 'Table-money-0306-ths.csv'))
    if os.path.exists(demo_redian):
        shutil.copy(demo_redian, os.path.join(input_dir, 'Table-index-redian-0306-ths.csv'))

    print(f"\n整理完毕！共把 {moved_count} 个过渡期文件及目录封存到了 .archive/ 中。")

if __name__ == '__main__':
    organize_files()
