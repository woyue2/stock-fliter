# -*- coding: utf-8 -*-
"""
HTML 报告生成器 - 极简风格，复用 check-trend-bottom 的格式

功能：
- 生成单页应用（summary.html）
- 左侧导航 + 右侧 iframe 展示详情
- localStorage 记住已选股票
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


class HTMLReporter:
    """HTML 报告生成器"""
    
    # 策略类别定义
    STRATEGY_CATEGORIES = {
        "强力买入": "稳步上升 AND 放量突破",
        "潜力反转": "NOT 稳步上升 AND MACD零轴下金叉", 
        "一般持有": "稳步上升 AND NOT 放量突破",
        "左侧关注": "TD9 OR MACD零轴下金叉"
    }
    
    def __init__(self, output_dir: Path, end_date: Optional[str] = None):
        self.output_dir = output_dir
        self.end_date = end_date
    
    def generate(self, df: pd.DataFrame, title: str = "新策略分析") -> Path:
        """生成 HTML 报告"""
        now = datetime.now()
        ts = now.strftime("%H%M%S")
        
        # 如果没有 end_date，从数据中读取日期
        if not self.end_date and not df.empty:
            # 尝试从多个可能的日期列中读取
            date_columns = ["最新日期", "日期", "交易日期", "date"]
            data_date = None
            for col in date_columns:
                if col in df.columns:
                    first_date = df[col].iloc[0]
                    if pd.notna(first_date):
                        data_date = str(first_date)
                        print(f"  [INFO] 从数据中读取到日期: {data_date}")
                        break
            
            if data_date:
                # 提取日期部分（可能是 "2024-01-30" 或 "2024-01-30 00:00:00" 格式）
                date_str = data_date.split()[0].replace("-", "")
            else:
                date_str = now.strftime("%Y%m%d")
                print(f"  [WARN] 数据中未找到日期信息，使用当前日期: {date_str}")
        else:
            date_str = self.end_date if self.end_date else now.strftime("%Y%m%d")
            date_str = date_str.replace("-", "")
        
        # 创建策略类别数据
        strategy_data = {}
        # 定义所有策略名称
        all_strategy_names = [
            # 强买入信号（11个）
            "TD9+MACD金叉+放量突破",
            "TD9+MACD金叉",
            "稳步上升+放量突破",
            "TD9+放量突破",
            "TD9+MACD金叉+阴线",
            "TD9+MACD金叉+阴线+放量突破",
            "TD7+MACD金叉",
            "TD8+MACD金叉",
            "TD7+放量突破",
            "TD8+放量突破",
            "TD8+MACD金叉+阴线+放量突破",
            # 中买入信号（6个）
            "MACD金叉+放量突破",
            "非稳步上升+MACD金叉",
            "TD9+稳步上升",
            "TD7+MACD金叉+阴线",
            "TD8+MACD金叉+阴线",
            "TD9+MACD金叉+阴线",
            # 观察信号（4个）
            "稳步上升+MACD金叉",
            "稳步上升+非放量突破",
            "TD9或MACD金叉",
            "TD7+MACD金叉+阴线+放量突破"
        ]
        
        for strategy_name in all_strategy_names:
            # 根据布尔列筛选数据
            if strategy_name in df.columns:
                strategy_df = df[df[strategy_name] == True]
            else:
                strategy_df = pd.DataFrame()
            strategy_data[strategy_name] = strategy_df
                
        # 生成各策略详情页
        for strategy_name, strategy_df in strategy_data.items():
            if not strategy_df.empty:
                self._generate_detail_page(strategy_df, self.output_dir, strategy_name)
        
        # 生成主页（带 iframe）
        summary_filename = f"summary_{date_str}_{ts}.html"
        summary_path = self._generate_summary(strategy_data, self.output_dir, title, summary_filename, date_str)
        
        # 导出到索引CSV
        self._export_to_index_csv(df, "新指标", date_str, summary_path)
        
        return summary_path
    
    def _generate_summary(self, strategy_data: dict, report_dir: Path, title: str, filename: str = "summary.html", date_str: str = None) -> Path:
        """生成主页"""
        
        # 收集所有策略（包括空策略）和统计信息
        available_strategies = []
        strategy_count_data = {}
        strategy_empty_flags = {}
        for strategy_name, strategy_df in strategy_data.items():
            strategy_count_data[strategy_name] = len(strategy_df)
            strategy_empty_flags[strategy_name] = strategy_df.empty
            if not strategy_df.empty:
                available_strategies.append(strategy_name)
        
        # 定义策略分组关系
        strategy_group_map = {
            # 强买入信号（13个）
            "TD9+MACD金叉+放量突破": "强买入信号",
            "TD9+MACD金叉": "强买入信号",
            "稳步上升+放量突破": "强买入信号",
            "TD9+放量突破": "强买入信号",
            "TD9+MACD金叉+阴线": "强买入信号",
            "TD9+MACD金叉+阴线+放量突破": "强买入信号",
            "TD7+MACD金叉": "强买入信号",
            "TD8+MACD金叉": "强买入信号",
            "TD7+放量突破": "强买入信号",
            "TD8+放量突破": "强买入信号",
            "TD9+放量突破": "强买入信号",
            "TD8+MACD金叉+阴线+放量突破": "强买入信号",
            # 中买入信号（6个）
            "MACD金叉+放量突破": "中买入信号",
            "非稳步上升+MACD金叉": "中买入信号",
            "TD9+稳步上升": "中买入信号",
            "TD7+MACD金叉+阴线": "中买入信号",
            "TD8+MACD金叉+阴线": "中买入信号",
            "TD9+MACD金叉+阴线": "中买入信号",
            # 观察信号（4个）
            "稳步上升+MACD金叉": "观察信号",
            "稳步上升+非放量突破": "观察信号",
            "TD9或MACD金叉": "观察信号",
            "TD7+MACD金叉+阴线+放量突破": "观察信号"
        }
        
        # 策略描述映射
        strategy_desc_map = {
            # 强买入信号
            "TD9+MACD金叉+放量突破": "TD9 + MACD金叉 + 放量突破",
            "TD9+MACD金叉": "TD9 + MACD金叉",
            "稳步上升+放量突破": "稳步上升 + 放量突破",
            "TD9+放量突破": "TD9 + 放量突破",
            "TD9+MACD金叉+阴线": "TD9 + MACD金叉 + 阴线",
            "TD9+MACD金叉+阴线+放量突破": "TD9 + MACD金叉 + 阴线 + 放量突破",
            "TD7+MACD金叉": "TD7 + MACD金叉",
            "TD8+MACD金叉": "TD8 + MACD金叉",
            "TD7+放量突破": "TD7 + 放量突破",
            "TD8+放量突破": "TD8 + 放量突破",
            "TD9+放量突破": "TD9 + 放量突破",
            "TD8+MACD金叉+阴线+放量突破": "TD8 + MACD金叉 + 阴线 + 放量突破",
            # 中买入信号
            "MACD金叉+放量突破": "MACD金叉 + 放量突破",
            "非稳步上升+MACD金叉": "非稳步上升 + MACD金叉",
            "TD9+稳步上升": "TD9 + 稳步上升",
            "TD7+MACD金叉+阴线": "TD7 + MACD金叉 + 阴线",
            "TD8+MACD金叉+阴线": "TD8 + MACD金叉 + 阴线",
            "TD9+MACD金叉+阴线": "TD9 + MACD金叉 + 阴线",
            # 观察信号
            "稳步上升+MACD金叉": "稳步上升 + MACD金叉",
            "稳步上升+非放量突破": "稳步上升 + 非放量突破",
            "TD9或MACD金叉": "TD9 或 MACD金叉",
            "TD7+MACD金叉+阴线+放量突破": "TD7 + MACD金叉 + 阴线 + 放量突破"
        }
        
        # 按策略分组（保持固定顺序）
        groups = {
            "强买入信号": [],
            "中买入信号": [], 
            "观察信号": []
        }
        
        # 将所有策略分配到对应的分组（包括空策略）
        all_strategy_names = list(strategy_count_data.keys())
        for strategy in all_strategy_names:
            if strategy in strategy_group_map:
                group = strategy_group_map[strategy]
                groups[group].append((strategy, strategy_count_data[strategy]))
        
        # 策略描述映射
        strategy_desc_map = {
            "完美底部": "TD9 + MACD零轴下金叉 + 放量突破",
            "黄金组合": "TD9 + MACD零轴下金叉",
            "强力买入": "稳步上升 + 放量突破",
            "TD突破": "TD9 + 放量突破",
            "MACD突破": "MACD零轴下金叉 + 放量突破",
            "潜力反转": "非稳步上升 + MACD零轴下金叉",
            "TD上升": "TD9 + 稳步上升", 
            "稳步上升加MACD": "稳步上升 + MACD零轴下金叉",
            "一般持有": "稳步上升 + 非放量突破", 
            "左侧关注": "TD9 或 MACD零轴下金叉"
        }
        
        # 生成导航项
        nav_items = ""
        first_strategy = available_strategies[0] if available_strategies else ""
        
        for group_name, items in groups.items():
            if items:
                nav_items += f'<div class="nav-group">{group_name}</div>'
                for strategy, count in items:
                    strategy_desc = strategy_desc_map.get(strategy, strategy)
                    active = "active" if strategy == first_strategy else ""
                    is_empty = strategy_empty_flags.get(strategy, False)
                    disabled = "disabled" if is_empty else ""
                    onclick = f"onclick=\"showStrategy('{strategy}')\"" if not is_empty else ""
                    nav_items += f'''
                    <div class="nav-item {active} {disabled}" data-strategy="{strategy}" {onclick}>
                        <span class="strategy-name">{strategy_desc}</span>
                        <span class="strategy-count">{count}</span>
                    </div>
                    '''
        
        available_strategies_js = str(available_strategies).replace("'", '"')
        
        # 使用 date_str 来显示标题日期（已经从数据中读取或使用 end_date）
        if date_str and len(date_str) == 8:
            display_date = date_str[:4] + "-" + date_str[4:6] + "-" + date_str[6:8]
            display_title = f"{title} - {display_date}"
        else:
            display_title = title
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{display_title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, "Microsoft YaHei", sans-serif;
            background: #f5f5f5;
            height: 100vh;
            overflow: hidden;
        }}
        .layout {{
            display: flex;
            height: 100vh;
        }}
        .sidebar {{
            width: 200px;
            background: #fff;
            border-right: 1px solid #e0e0e0;
            display: flex;
            flex-direction: column;
        }}
        .logo {{
            padding: 20px;
            font-size: 16px;
            font-weight: 600;
            color: #333;
            border-bottom: 1px solid #e0e0e0;
        }}
        .nav {{
            flex: 1;
            overflow-y: auto;
            padding: 10px 0;
        }}
        .nav-group {{
            padding: 12px 20px 6px;
            font-size: 12px;
            color: #ff6b00;
            font-weight: 700;
            font-size: 13px;
        }}
        .nav-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 20px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .nav-item:hover {{
            background: #f5f5f5;
        }}
        .nav-item.active {{
            background: #e3f2fd;
            color: #1976d2;
        }}
        .strategy-name {{
            font-size: 14px;
        }}
        .strategy-count {{
            font-size: 12px;
            background: #e0e0e0;
            padding: 2px 8px;
            border-radius: 10px;
        }}
        .nav-item.active .strategy-count {{
            background: #1976d2;
            color: #fff;
        }}
        .nav-item.disabled {{
            color: #ccc;
            cursor: not-allowed;
        }}
        .nav-item.disabled:hover {{
            background: #fff;
        }}
        .nav-item.disabled .strategy-count {{
            background: #eee;
            color: #ccc;
        }}
        .selected-stocks {{
            padding: 15px 20px;
            border-top: 1px solid #e0e0e0;
            background: #fafafa;
            max-height: 150px;
            overflow-y: auto;
        }}
        .selected-title {{
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .selected-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }}
        .selected-item {{
            display: inline-flex;
            align-items: center;
            padding: 2px 6px;
            background: #e3f2fd;
            border-radius: 3px;
            font-size: 11px;
            color: #1976d2;
        }}
        .selected-item .remove {{
            margin-left: 4px;
            cursor: pointer;
            color: #999;
        }}
        .selected-item .remove:hover {{
            color: #d32f2f;
        }}
        .notes-section {{
            padding: 15px 20px;
            border-top: 1px solid #e0e0e0;
            background: #fff;
        }}
        .notes-label {{
            font-size: 12px;
            color: #666;
            margin-bottom: 6px;
        }}
        .notes-input {{
            width: 100%;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 8px;
            font-size: 12px;
            resize: none;
            font-family: inherit;
        }}
        .notes-input:focus {{
            outline: none;
            border-color: #1976d2;
        }}
        .main {{
            flex: 1;
            display: flex;
            flex-direction: column;
        }}
        .content {{
            flex: 1;
            background: #fff;
        }}
        .content iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}
        .empty {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="layout">
        <div class="sidebar">
            <div class="logo">📊 {title}</div>
            <div class="nav">
                {nav_items}
            </div>
            <!-- 已选股票 -->
            <div class="selected-stocks">
                <div class="selected-title">
                    <span>⭐ 已选股票</span>
                    <span id="selectedCount">0只</span>
                </div>
                <div class="selected-list" id="selectedList"></div>
            </div>
            <!-- 备注 -->
            <div class="notes-section">
                <div class="notes-label">📝 备注</div>
                <textarea class="notes-input" id="notesInput" placeholder="添加备注..." rows="3"></textarea>
            </div>
        </div>
        <div class="main">
            <div class="content" id="content">
                {f'<iframe src="{first_strategy}.html"></iframe>' if first_strategy else '<div class="empty">暂无数据</div>'}
            </div>
        </div>
    </div>
    
    <script>
        const availableStrategies = {available_strategies_js};
        const emptyStrategies = {str(strategy_empty_flags).replace("'", '"').replace("True", "true").replace("False", "false")};
        const STORAGE_KEY = 'selected_stocks';
        const NOTES_KEY = 'report_notes';
        
        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', () => {{
            loadSelectedStocks();
            loadNotes();
            
            // 监听 iframe 消息
            window.addEventListener('message', handleIframeMessage);
        }});
        
        // 处理 iframe 消息
        function handleIframeMessage(event) {{
            if (event.data && event.data.type === 'selectionUpdate') {{
                renderSelectedStocks(event.data.stocks);
            }}
        }}
        
        // 供子页面调用：更新已选股票列表
        window.addSelectedStockFromChild = function(selectedCodes) {{
            localStorage.setItem(STORAGE_KEY, JSON.stringify(selectedCodes));
            renderSelectedStocks(selectedCodes);
            
            // 同步到所有 iframe
            document.querySelectorAll('iframe').forEach(iframe => {{
                try {{
                    iframe.contentWindow.updateSelectionFromParent(selectedCodes);
                }} catch (e) {{}}
            }});
        }};
        
        // 加载已选股票
        function loadSelectedStocks() {{
            const stocks = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            renderSelectedStocks(stocks);
        }}
        
        // 渲染已选股票列表
        function renderSelectedStocks(stocks) {{
            const container = document.getElementById('selectedList');
            const countEl = document.getElementById('selectedCount');
            countEl.textContent = stocks.length + '只';
            
            if (stocks.length === 0) {{
                container.innerHTML = '<span style="color:#999;font-size:11px;">暂无</span>';
                return;
            }}
            
            container.innerHTML = stocks.map(code => `
                <span class="selected-item" data-code="${{code}}">
                    ${{code}}
                    <span class="remove" onclick="removeStock('${{code}}')">×</span>
                </span>
            `).join('');
        }}
        
        // 添加已选股票（供 iframe 调用）
        function addSelectedStock(code) {{
            const stocks = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            if (!stocks.includes(code)) {{
                stocks.push(code);
                localStorage.setItem(STORAGE_KEY, JSON.stringify(stocks));
                renderSelectedStocks(stocks);
                
                // 同步到所有 iframe
                document.querySelectorAll('iframe').forEach(iframe => {{
                    try {{
                        iframe.contentWindow.updateSelectionFromParent(stocks);
                    }} catch (e) {{}}
                }});
            }}
        }}
        
        // 移除已选股票
        function removeStock(code) {{
            let stocks = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            stocks = stocks.filter(c => c !== code);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(stocks));
            renderSelectedStocks(stocks);
            
            // 通知所有 iframe 更新勾选状态
            document.querySelectorAll('iframe').forEach(iframe => {{
                try {{
                    iframe.contentWindow.removeStockSelection(code);
                }} catch (e) {{}}
            }});
        }}
        
        // 加载备注
        function loadNotes() {{
            const notes = localStorage.getItem(NOTES_KEY) || '';
            document.getElementById('notesInput').value = notes;
        }}
        
        // 保存备注
        document.getElementById('notesInput').addEventListener('input', function() {{
            localStorage.setItem(NOTES_KEY, this.value);
        }});
        
        // 显示策略
        function showStrategy(strategy) {{
            // 更新导航状态
            document.querySelectorAll('.nav-item').forEach(item => {{
                item.classList.remove('active');
                if (item.dataset.strategy === strategy) {{
                    item.classList.add('active');
                }}
            }});
            
            // 更新 iframe
            if (availableStrategies.includes(strategy)) {{
                document.getElementById('content').innerHTML = 
                    `<iframe src="${{strategy}}.html"></iframe>`;
            }} else {{
                // 显示空状态页面
                const emptyHtml = `
                <div style="display:flex;align-items:center;justify-content:center;height:100%;color:#999;">
                    <div style="text-align:center;">
                        <div style="font-size:48px;margin-bottom:16px;">📭</div>
                        <div style="font-size:16px;">暂无符合该策略的股票</div>
                        <div style="font-size:14px;color:#ccc;margin-top:8px;">策略: ${{strategy}}</div>
                    </div>
                </div>`;
                document.getElementById('content').innerHTML = emptyHtml;
            }}
        }}
    </script>
</body>
</html>
'''
        
        path = report_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path
    
    def _generate_detail_page(self, df: pd.DataFrame, report_dir: Path, strategy: str) -> Path:
        """生成详情页（极简风格）"""
        
        # 生成表格行
        rows_html = ""
        for idx, row in df.iterrows():
            code = row.get("代码", "")
            name = row.get("名称", "")
            board = row.get("板块", "")
            industry = row.get("行业", "")
            latest_close = row.get("最新收盘", "")
            latest_date = row.get("最新日期", "")
            steady_uptrend = "✅" if row.get("稳步上升", False) else ""
            volume_breakout = "✅" if row.get("放量突破", False) else ""
            macd_gold = "✅" if row.get("MACD金叉(零下)", False) else ""
            macd_strength = row.get("MACD值", 0)
            td_count = row.get("TD计数", 0)
            strategies = row.get("所属策略", "")
            
            # 构建东方财富链接
            if str(code).startswith("6"):
                em_code = f"sh{code}"
            else:
                em_code = f"sz{code}"
            em_url = f"https://quote.eastmoney.com/{em_code}.html"
            
            # MACD值显示（颜色编码）
            macd_strength_html = f"{macd_strength}"
            if macd_strength < -1:
                macd_strength_html = f'<span style="color: #d32f2f; font-weight: bold;">{macd_strength}</span>'
            elif macd_strength < -0.5:
                macd_strength_html = f'<span style="color: #f57c00;">{macd_strength}</span>'
            elif macd_strength < 0:
                macd_strength_html = f'<span style="color: #999;">{macd_strength}</span>'
            else:
                macd_strength_html = f'<span style="color: #4caf50;">{macd_strength}</span>'
            
            rows_html += f'''
            <tr data-code="{code}">
                <td><input type="checkbox" class="check" data-code="{code}" onchange="saveChecked()"></td>
                <td><a href="javascript:void(0)" onclick="showStock('{em_url}')" class="code">{code}</a></td>
                <td>{name}</td>
                <td>{board}</td>
                <td>{industry}</td>
                <td>{latest_close}</td>
                <td>{latest_date}</td>
                <td>{steady_uptrend}</td>
                <td>{volume_breakout}</td>
                <td>{macd_gold}</td>
                <td class="macd-strength">{macd_strength_html}</td>
                <td class="td td-{self._get_td_class(td_count)}">{td_count}</td>
                <td class="detail">{strategies}</td>
            </tr>
            '''
        
        # 板块统计
        board_stats = ""
        if "板块" in df.columns and df["板块"] is not None:
            stats = df["板块"].value_counts()
            for board, count in stats.items():
                board_stats += f'<span class="tag">{board} {count}</span>'

        # 行业统计
        industry_stats = ""
        if "行业" in df.columns and df["行业"] is not None:
            stats = df["行业"].value_counts().head(10)
            for ind, count in stats.items():
                industry_stats += f'<span class="tag">{ind} {count}</span>'
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{strategy}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, "Microsoft YaHei", sans-serif;
            font-size: 13px;
            color: #333;
            background: #fff;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }}
        .left-panel {{
            width: 35%;
            min-width: 400px;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #e0e0e0;
        }}
        .right-panel {{
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #fafafa;
        }}
        .right-header {{
            padding: 10px 16px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .stock-frame {{
            flex: 1;
            border: none;
            width: 100%;
        }}
        .placeholder {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
        }}
        .header {{
            padding: 16px 20px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .title {{
            font-size: 16px;
            font-weight: 600;
        }}
        .count {{
            color: #666;
        }}
        .toolbar {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .btn {{
            padding: 6px 12px;
            border: 1px solid #ddd;
            background: #fff;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }}
        .btn:hover {{
            background: #f5f5f5;
        }}
        .search {{
            padding: 6px 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 150px;
        }}
        .stats {{
            padding: 12px 20px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .stats-group {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .stats-label {{
            font-size: 12px;
            color: #999;
            margin-right: 4px;
        }}
        .tag {{
            font-size: 11px;
            padding: 2px 6px;
            background: #f0f0f0;
            border-radius: 3px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #fafafa;
            font-weight: 500;
            position: sticky;
            top: 0;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        tr.checked {{
            background: #e8f5e9;
        }}
        .code {{
            color: #1976d2;
            text-decoration: none;
        }}
        .code:hover {{
            text-decoration: underline;
        }}
        .td {{
            font-weight: 600;
            text-align: center;
        }}
        .td-high {{ color: #d32f2f; }}
        .td-mid {{ color: #f57c00; }}
        .td-low {{ color: #999; }}
        .macd-strength {{
            text-align: center;
            font-weight: 600;
        }}
        .detail {{
            font-size: 11px;
            color: #1976d2;
        }}
        .table-wrap {{
            overflow: auto;
            flex: 1;
        }}
        .checked-info {{
            font-size: 12px;
            color: #4caf50;
        }}
        .open-new {{
            font-size: 11px;
            color: #1976d2;
            text-decoration: none;
            cursor: pointer;
        }}
        .open-new:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="left-panel">
        <div class="header">
        <div>
            <span class="title">{strategy}</span>
            <span class="count">共 {len(df)} 只</span>
        </div>
        <div class="toolbar">
            <span class="checked-info" id="checkedInfo">已选 0</span>
            <button class="btn" onclick="selectAll()">全选</button>
            <button class="btn" onclick="clearAll()">清除</button>
            <button class="btn" onclick="exportCSV()">导出</button>
            <input type="text" class="search" placeholder="搜索..." oninput="filterTable(this.value)">
        </div>
    </div>
    
    <div class="stats">
        <div class="stats-group">
            <span class="stats-label">板块:</span>
            {board_stats}
        </div>
        <div class="stats-group">
            <span class="stats-label">行业:</span>
            {industry_stats}
        </div>
    </div>
    
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th width="30"></th>
                    <th>代码</th>
                    <th>名称</th>
                    <th>板块</th>
                    <th>行业</th>
                    <th>最新收盘</th>
                    <th>最新日期</th>
                    <th>稳步上升</th>
                    <th>放量突破</th>
                    <th>MACD金叉</th>
                    <th>MACD强度</th>
                    <th>TD计数</th>
                    <th>所属策略</th>
                </tr>
            </thead>
            <tbody id="tbody">
                {rows_html}
            </tbody>
        </table>
    </div>
    </div>
    
    <div class="right-panel">
        <div class="right-header">
            <span id="stockTitle">点击左侧股票代码查看详情</span>
            <a id="openNew" class="open-new" style="display:none" onclick="window.open(currentUrl)" title="新窗口打开">↗ 新窗口</a>
        </div>
        <div class="placeholder" id="placeholder">← 选择股票查看行情</div>
        <iframe id="stockFrame" class="stock-frame" style="display:none"></iframe>
    </div>
    
    <script>
        const STORAGE_KEY = 'new_strategy_{strategy.replace(" ", "_")}';
        let currentUrl = '';
        
        // 初始化
        document.addEventListener('DOMContentLoaded', loadChecked);
        
        function loadChecked() {{
            const checked = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            checked.forEach(code => {{
                const cb = document.querySelector(`input[data-code="${{code}}"]`);
                if (cb) {{
                    cb.checked = true;
                    cb.closest('tr').classList.add('checked');
                }}
            }});
            updateInfo();
        }}
        
        function saveChecked() {{
            const checked = [];
            document.querySelectorAll('.check:checked').forEach(cb => {{
                checked.push(cb.dataset.code);
                cb.closest('tr').classList.add('checked');
            }});
            document.querySelectorAll('.check:not(:checked)').forEach(cb => {{
                cb.closest('tr').classList.remove('checked');
            }});
            localStorage.setItem(STORAGE_KEY, JSON.stringify(checked));
            updateInfo();
            
            // 通知父窗口更新已选股票列表
            try {{
                window.parent.addSelectedStockFromChild(checked);
            }} catch (e) {{}}
        }}
        
        // 供父窗口调用：更新当前页面的勾选状态
        function updateSelectionFromParent(selectedCodes) {{
            document.querySelectorAll('.check').forEach(cb => {{
                const isChecked = selectedCodes.includes(cb.dataset.code);
                cb.checked = isChecked;
                if (isChecked) {{
                    cb.closest('tr').classList.add('checked');
                }} else {{
                    cb.closest('tr').classList.remove('checked');
                }}
            }});
            updateInfo();
        }}
        
        // 供父窗口调用：移除勾选
        function removeStockSelection(code) {{
            const cb = document.querySelector(`input[data-code="${{code}}"]`);
            if (cb) {{
                cb.checked = false;
                cb.closest('tr').classList.remove('checked');
            }}
            saveChecked();
        }}
        
        function updateInfo() {{
            const count = document.querySelectorAll('.check:checked').length;
            document.getElementById('checkedInfo').textContent = '已选 ' + count;
        }}
        
        function selectAll() {{
            document.querySelectorAll('.check').forEach(cb => cb.checked = true);
            saveChecked();
        }}
        
        function clearAll() {{
            document.querySelectorAll('.check').forEach(cb => cb.checked = false);
            saveChecked();
        }}
        
        function exportCSV() {{
            const rows = [['代码', '名称']];
            document.querySelectorAll('.check:checked').forEach(cb => {{
                const tr = cb.closest('tr');
                rows.push([cb.dataset.code, tr.cells[2].textContent]);
            }});
            if (rows.length === 1) {{ alert('请先选择股票'); return; }}
            const csv = rows.map(r => r.join(',')).join('\\n');
            const blob = new Blob(['\\ufeff' + csv], {{type: 'text/csv'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = '{strategy}.csv';
            a.click();
        }}
        
        function filterTable(keyword) {{
            keyword = keyword.toLowerCase();
            document.querySelectorAll('#tbody tr').forEach(tr => {{
                tr.style.display = tr.textContent.toLowerCase().includes(keyword) ? '' : 'none';
            }});
        }}
        
        function showStock(url) {{
            currentUrl = url;
            const code = url.match(/([a-z]+\\d+)\\.html/)[1];
            document.getElementById('stockTitle').textContent = code.toUpperCase();
            document.getElementById('openNew').style.display = 'inline';
            document.getElementById('placeholder').style.display = 'none';
            const frame = document.getElementById('stockFrame');
            frame.style.display = 'block';
            frame.src = url;
        }}
    </script>
</body>
</html>
'''
        
        path = report_dir / f"{strategy}.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path
    
    def _get_td_class(self, value: int) -> str:
        """根据TD值返回CSS类"""
        if value >= 9:
            return "high"
        elif value >= 7:
            return "mid"
        return "low"
    
    def _export_to_index_csv(self, df: pd.DataFrame, module_name: str, 
                             report_date: str, report_path: Path):
        """将股票数据追加到索引CSV"""
        index_file = Path(__file__).parent.parent.parent / "get-data" / "data" / "stocks_index.csv"
        
        # 准备索引数据
        index_data = []
        for _, row in df.iterrows():
            # 获取该股票所属的策略
            strategies = []
            for col in df.columns:
                if col in ["代码", "名称", "板块", "行业", "最新收盘", "最新日期", 
                          "稳步上升", "放量突破", "MACD金叉(零下)", "MACD值", "TD计数", "所属策略"]:
                    continue
                if row.get(col, False) == True:
                    strategies.append(col)
            
            strategy_str = ", ".join(strategies) if strategies else row.get("所属策略", "")
            
            # 计算相对于项目根目录的路径
            project_root = Path(__file__).parent.parent.parent
            relative_path = report_path.relative_to(project_root)
            # 转换为正斜杠格式（适用于Web）
            web_path = str(relative_path).replace("\\", "/")
            
            index_data.append({
                "代码": str(row.get("代码", "")).strip(),
                "名称": str(row.get("名称", "")).strip(),
                "日期": report_date[:4] + "-" + report_date[4:6] + "-" + report_date[6:8] if len(report_date) == 8 else report_date,
                "模块": module_name,
                "策略级别": strategy_str,
                "报告路径": web_path,
                "板块": str(row.get("板块", "")).strip(),
                "行业": str(row.get("行业", "")).strip(),
                "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        if not index_data:
            return
        
        # 追加到CSV
        index_df = pd.DataFrame(index_data)
        if index_file.exists():
            index_df.to_csv(index_file, mode='a', header=False, 
                           index=False, encoding='utf-8-sig')
        else:
            index_df.to_csv(index_file, index=False, encoding='utf-8-sig')
        
        print(f"  [OK] 已导出 {len(index_data)} 条记录到索引文件")
