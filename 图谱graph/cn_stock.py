import json
import os
import requests
import time
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
import concurrent.futures
from tqdm import tqdm
import threading

file_lock = threading.Lock()

table_keys = ['公司名称', '所属地域', '英文名称', '所属行业', '曾用名', '公司网址']
hds = [{'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'},
       {'User-Agent': 'Mozilla/5.0 (Windows NT 6.2) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.12 Safari/535.11'},
       {'User-Agent': 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)'}]


def stock_spider(id):
    url = 'http://basic.10jqka.com.cn/'+id+'/company.html#stockpage'
    time.sleep(np.random.rand()*5)

    org = {'股票代码': id}
    req = requests.get(url, headers=hds[int(id) % 3])
    req.encoding = 'gbk'
    text = req.text
    soup = BeautifulSoup(text, 'html.parser')
    table = soup.find('table', {'class': 'm_table'})
    try:
        org['img'] = table.find('img')['src']
    except Exception:
        pass 
    try:   
        spans = table.findAll('span')
        for index, span in enumerate(spans):
            org[table_keys[index]] = span.text.strip()
    except Exception:
        pass
    try:
        org['主营业务'] = re.search(
            r"(主营业务：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        for p in ['控股股东', '实际控制人', '最终控制人']:
            pattern = re.compile(
                "("+p+"：</strong>\s*<span>)(.*)(<span class=)")
            match = pattern.search(text)
            if match != None:
                org[p] = match.group(2).strip()
            else:
                org[p] = ""
    except Exception as e:
        pass
    try:
        org['董事长'] = re.search(
            r"(董事长：</strong>\s*<span>\s*<a.*>)(.*)(</a>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['董事长秘书'] = re.search(
            r"(董\s*秘：</strong>\s*<span>\s*<a.*>)(.*)(</a>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['法人代表'] = re.search(
            r"(法人代表：</strong>\s*<span>\s*<a.*>)(.*)(</a>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['总经理'] = re.search(
            r"(总\s*经\s*理：</strong>\s*<span>\s*<a.*>)(.*)(</a>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['总裁'] = re.search(
            r"(总\s*裁：</strong>\s*<span>\s*<a.*>)(.*)(</a>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['注册资金'] = re.search(
            r"(注册资金：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['员工人数'] = re.search(
            r"(员工人数：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['电话'] = re.search(
            r"(电\s*话：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['传真'] = re.search(
            r"(传\s*真：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['邮编'] = re.search(
            r"(邮\s*编：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['办公地址'] = re.search(
            r"(办公地址：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['成立日期'] = re.search(
            r"(成立日期：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['发行数量'] = re.search(
            r"(发行数量：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['发行价格'] = re.search(
            r"(发行价格：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['上市日期'] = re.search(
            r"(上市日期：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass

    try:
        org['发行市盈率'] = re.search(
            r"(发行市盈率：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception as e:
        pass
    try:
        org['预计募资'] = re.search(
            r"(预计募资：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['首日开盘价'] = re.search(
            r"(首日开盘价：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['实际募资'] = re.search(
            r"(实际募资：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['主承销商'] = re.search(
            r"(主承销商：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass
    try:
        org['上市保荐人'] = re.search(
            r"(上市保荐人：</strong>\s*<span>)(.*)(</span>)", text).group(2).strip()
    except Exception:
        pass

    return org



def process_and_save(code):
    try:
        org = stock_spider(code)
        if org:
            # 加锁确保多线程写入文件不出现冲突
            with file_lock:
                with open('a_result.json', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(org, ensure_ascii=False) + '\n')
    except Exception as e:
        pass

if __name__ == '__main__':
    with open('a_stock.txt', 'r', encoding='utf-8') as code_list:
        a_stock_codes = json.load(code_list)
        
    n_workers = 3  # 设置默认线程数参数
    print(f"开始增量抓取，共发现 {len(a_stock_codes)} 个股票，当前使用 {n_workers} 个线程...")
    print(f"抓取结果将边抓边写追加至：a_result.json")
    
    # 线程池并发执行与进度条
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = [executor.submit(process_and_save, code) for code in a_stock_codes]
        # tqdm 读取进度
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="抓取进度"):
            pass
            
    print("全部抓取完毕！")