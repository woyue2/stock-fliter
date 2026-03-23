import json
import concurrent.futures
from tqdm import tqdm
from cn_stock import process_and_save

if __name__ == '__main__':
    # 只需要读取刚刚保存的 missing_stocks.txt
    with open('missing_stocks.txt', 'r', encoding='utf-8') as f:
        missing_codes = json.load(f)
        
    n_workers = 3
    print(f"开始单独补录... 共有 {len(missing_codes)} 只未抓取的股票，使用 {n_workers} 个线程...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = [executor.submit(process_and_save, code) for code in missing_codes]
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="补录进度"):
            pass
            
    print("补录完成！请使用检查脚本再次确认是否均已成功。")
