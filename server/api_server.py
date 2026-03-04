# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# INPUT:  stocks_index.csv
# OUTPUT: Flask JSON API
# POS:    server/api_server.py
# -*- coding: utf-8 -*-
"""
股票搜索API服务
启动: python server/api_server.py
访问: http://localhost:5000
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
from pathlib import Path

app = Flask(__name__)
CORS(app)  # 允许跨域

def get_latest_index_file():
    """获取最新日期的 stocks_index.csv"""
    # 由于脚本移动到了 server/ 目录下，路径需要向上跳一级
    base_dir = Path(__file__).parent.parent
    stocks_index_dir = base_dir / "get-data" / "data" / "stocks_index"
    
    if not stocks_index_dir.exists():
        # 如果没有日期目录，尝试使用旧的路径
        old_path = base_dir / "get-data" / "data" / "stocks_index.csv"
        return old_path if old_path.exists() else None
    
    # 查找最新日期的目录
    date_dirs = [d for d in stocks_index_dir.iterdir() if d.is_dir()]
    if not date_dirs:
        return None
    
    latest_date_dir = sorted(date_dirs, key=lambda d: d.name, reverse=True)[0]
    index_file = latest_date_dir / "stocks_index.csv"
    
    return index_file if index_file.exists() else None

def load_index():
    """加载索引CSV"""
    index_file = get_latest_index_file()
    if not index_file or not index_file.exists():
        return pd.DataFrame()
    print(f"[INFO] 使用索引文件: {index_file}")
    return pd.read_csv(index_file, encoding='utf-8-sig')

@app.route('/api/search', methods=['GET'])
def search_stock():
    """搜索股票
    参数:
        code: 股票代码 (如: 600519)
        name: 股票名称 (如: 茅台)
        date: 日期 (如: 2026-01-30)
        module: 模块 (如: MAxRSIx6U1D)
    """
    df = load_index()
    if df.empty:
        return jsonify({"error": "索引文件不存在"}), 404
    
    # 获取查询参数
    code = request.args.get('code', '').strip()
    name = request.args.get('name', '').strip()
    date = request.args.get('date', '').strip()
    module = request.args.get('module', '').strip()
    
    # 筛选
    if code:
        df = df[df['代码'].astype(str).str.contains(code, na=False)]
    if name:
        df = df[df['名称'].str.contains(name, na=False)]
    if date:
        df = df[df['日期'] == date]
    if module:
        df = df[df['模块'] == module]
    
    # 转换为JSON前，将所有 NaN/NaT 转为 None，避免前端 JSON.parse 失败
    df = df.where(pd.notna(df), None)
    results = df.to_dict('records')
    return jsonify({
        "total": len(results),
        "results": results
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    df = load_index()
    if df.empty:
        return jsonify({"error": "索引文件不存在"}), 404
    
    stats = {
        "total_records": len(df),
        "unique_stocks": df['代码'].nunique(),
        "date_range": {
            "start": df['日期'].min(),
            "end": df['日期'].max()
        },
        "modules": df['模块'].value_counts().to_dict(),
        "latest_update": df['生成时间'].max() if '生成时间' in df.columns else None
    }
    return jsonify(stats)

@app.route('/api/hot-stocks', methods=['GET'])
def get_hot_stocks():
    """获取热门股票（出现次数最多）"""
    df = load_index()
    if df.empty:
        return jsonify([])
    
    top_n = int(request.args.get('limit', 20))
    hot = df.groupby(['代码', '名称']).size().reset_index(name='出现次数')
    hot = hot.sort_values('出现次数', ascending=False).head(top_n)
    return jsonify(hot.to_dict('records'))

@app.route('/')
def index():
    """首页"""
    return """
    <h1>股票搜索API</h1>
    <ul>
        <li><a href="/api/search?code=600519">/api/search?code=600519</a></li>
        <li><a href="/api/search?name=茅台">/api/search?name=茅台</a></li>
        <li><a href="/api/stats">/api/stats</a></li>
        <li><a href="/api/hot-stocks">/api/hot-stocks</a></li>
    </ul>
    """

if __name__ == '__main__':
    index_file = get_latest_index_file()
    if index_file:
        print(f"索引文件: {index_file}")
    else:
        print("警告: 未找到索引文件")
    print(f"API服务启动: http://localhost:5000")
    app.run(debug=True, port=5000)
