"""
[INPUT]:    data_provider.py, streamlit, lightweight-charts
[OUTPUT]:   Interactive Replay App
[POS]:      valueCellMAx/main.py - Main application entry
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""
import streamlit as st
import pandas as pd
from lightweight_charts.widgets import StreamlitChart
import os
from data_provider import (
    get_stock_list, get_clean_df, get_available_dates, 
    get_stock_note, save_stock_note, check_db_health,
    get_stock_annotations, add_stock_annotation, remove_stock_annotation,
    get_stock_list_by_strategy, get_signal_types_for_strategy, run_strategy_scan,
    get_market_calendar, get_strategy_full_results
)

# 页面配置
st.set_page_config(layout="wide", page_title="ValueCellMAx - 专业复盘系统")

# 常量 (已废弃 JSON，全量使用 SQLite)

def load_note_from_db(code: str):
    """从数据库加载笔记"""
    return get_stock_note(code)

def save_note_to_db(code: str, note: str):
    """保存笔记到数据库"""
    save_stock_note(code, note)

def main():
    st.sidebar.title("🚀 ValueCellMAx")

    # --- 核心图表区域 (定义在前面以避免 UnboundLocalError) ---
    @st.fragment
    def render_chart_area(stock_code, selected_stock, df, current_idx, show_ma):
        # 指标预计算
        df = df.copy()
        if 'ma5' not in df.columns:
            df['ma5'] = df['close'].rolling(5).mean()
        if 'ma20' not in df.columns:
            df['ma20'] = df['close'].rolling(20).mean()

        st.subheader(f"📊 {selected_stock}")
        
        # 截断数据到当前回放索引
        visible_df = df.iloc[:current_idx + 1]

        chart = StreamlitChart(width=1200, height=700, toolbox=True)
        
        # A股颜色标准: 红涨绿跌
        chart.candle_style(
            up_color='#ef5350', down_color='#26a69a',
            wick_up_color='#ef5350', wick_down_color='#26a69a',
            border_up_color='#ef5350', border_down_color='#26a69a'
        )
        chart.volume_config(up_color='#ef5350', down_color='#26a69a')
        chart.legend(visible=True)

        if show_ma:
            line5 = chart.create_line(name='MA5', color='#ffca3a')
            line5.set(visible_df[['time', 'ma5']].rename(columns={'ma5': 'MA5'}).dropna())
            line20 = chart.create_line(name='MA20', color='#1982c4')
            line20.set(visible_df[['time', 'ma20']].rename(columns={'ma20': 'MA20'}).dropna())
        
        chart.set(visible_df)
        
        # 加载注解标记
        annos = get_stock_annotations(stock_code)
        for a in annos:
            chart.marker(time=a['date'], text=a['text'], shape='arrow_up', color='#ffffff', position='below')
        
        # 快捷键及缩放
        chart.hotkey(None, 'ArrowUp', lambda c: c.run_script(f'{c.id}.chart.timeScale().zoomIn()'))
        chart.hotkey(None, 'ArrowDown', lambda c: c.run_script(f'{c.id}.chart.timeScale().zoomOut()'))
        chart.load()
    
    # 0. 数据库健康检查 (Strict SQLite)
    is_healthy, msg = check_db_health()
    if not is_healthy:
        st.error(f"⚠️ 核心数据引擎故障: {msg}")
        st.info("💡 请确保 get-data/data/stocks.db 已生成且含数据。")
        return

    # 0.1 获取全局交易日历 (用于日期控制)
    market_dates = get_market_calendar()
    if not market_dates:
        st.error("数据库中无有效行情日期。")
        return
        
    if 'current_date_str' not in st.session_state:
        st.session_state.current_date_str = market_dates[-1]
    
    if 'view_mode' not in st.session_state:
        st.session_state.view_mode = "图表复盘"

    current_date = st.session_state.current_date_str

    # --- 侧边栏全局日期控制 ---
    st.sidebar.divider()
    st.sidebar.subheader("🕒 全局日期控制")
    
    all_dates = market_dates
    min_date = pd.to_datetime(all_dates[0]).date()
    max_date = pd.to_datetime(all_dates[-1]).date()
    
    import bisect
    
    def nav_to_date(new_date_str):
        if new_date_str in all_dates:
            st.session_state.current_date_str = new_date_str
            st.rerun()

    def on_date_change():
        raw_date = st.session_state.date_picker.strftime('%Y-%m-%d')
        idx = bisect.bisect_right(all_dates, raw_date) - 1
        idx = max(0, min(idx, len(all_dates)-1))
        nav_to_date(all_dates[idx])

    def on_slider_change():
        nav_to_date(all_dates[st.session_state.date_slider])

    current_idx = bisect.bisect_right(all_dates, st.session_state.current_date_str) - 1
    current_idx = max(0, min(current_idx, len(all_dates)-1))
    current_dt = pd.to_datetime(all_dates[current_idx]).date()

    st.sidebar.date_input("选择日期 (自动吸附)", value=current_dt, min_value=min_date, max_value=max_date, key="date_picker", on_change=on_date_change)
    st.sidebar.slider("回放进度", min_value=0, max_value=len(all_dates)-1, value=current_idx, key="date_slider", on_change=on_slider_change)
    
    col1, col2 = st.sidebar.columns(2)
    if col1.button("⏪ 前一天", use_container_width=True): nav_to_date(all_dates[current_idx - 1]) if current_idx > 0 else None
    if col2.button("⏩ 后一天", use_container_width=True): nav_to_date(all_dates[current_idx + 1]) if current_idx < len(all_dates) - 1 else None

    st.sidebar.info(f"📍 当前日期: {all_dates[current_idx]}")

    # --- 侧边栏主导航 ---
    st.sidebar.divider()
    st.sidebar.subheader("📌 功能模块")
    view_mode = st.sidebar.radio(
        "选择视图", 
        ["图表复盘", "TD 策略分析"], 
        index=0 if st.session_state.view_mode == "图表复盘" else 1,
        key="view_mode_radio"
    )
    st.session_state.view_mode = view_mode

    # 1. 策略分析视图 (TD 扫描与结果表格)
    if st.session_state.view_mode == "TD 策略分析":
        st.sidebar.divider()
        st.sidebar.subheader("🔍 TD 扫描设置")
        scan_limit = st.sidebar.number_input("扫描数量限制 (0为全量)", min_value=0, value=0, help="限制分析的股票数量，用于快速测试")
        
        if st.sidebar.button(f"🚀 开始 {current_date} 全量扫描"):
            progress_bar = st.sidebar.progress(0, text="准备扫描...")
            def report_progress(current, total):
                if total > 0:
                    progress_bar.progress(current / total, text=f"扫描中: {current}/{total}")
            
            # 使用新的 run_strategy_scan (支持 limit)
            limit_val = scan_limit if scan_limit > 0 else None
            num = run_strategy_scan("TD", current_date, limit=limit_val, progress_callback=report_progress)
            progress_bar.empty()
            st.session_state.last_scan_msg = f"✅ 完成！在 {current_date} 发现 {num} 个信号"
            st.rerun()

        if 'last_scan_msg' in st.session_state:
            st.sidebar.success(st.session_state.last_scan_msg)
            # 点击任何其他东西后清除
            del st.session_state.last_scan_msg

        # 主界面展示 TD 结果表格
        st.header(f"🔍 TD 策略扫描结果 ({current_date})")
        
        # 优化：直接加载结果，不再需要深度分析进度条
        with st.spinner("正在从数据库加载分析结果..."):
            df_results = get_strategy_full_results("TD", current_date)

        if 'selected_td_stock' not in st.session_state:
            st.session_state.selected_td_stock = None
            
        left_col, right_col = st.columns([2, 3]) # 左侧 40%，右侧 60%
        
        with left_col:
            if not df_results.empty:
                st.info(f"💡 发现 {len(df_results)} 个信号。点击代码可预览K线。")
                
                # 简化表格列
                display_cols = ["代码", "名称", "共振级别", "日/周/月 TD计数", "波动率", "日最新价"]
                df_display = df_results[display_cols]
                
                # 格式化展示
                def color_resonance(val):
                    if '20+极限' in val or '15-20极地' in val or '10-15深底' in val:
                        return 'color: #c92a2a; font-weight: bold;'
                    elif '9底' in val:
                        return 'color: #e67700; font-weight: 500;'
                    elif '6底' in val or '共振' in val:
                        return 'color: #2f9e44;'
                    return ''

                styled_df = df_display.style.applymap(color_resonance, subset=['共振级别'])
                
                # 使用 st.dataframe 交互式展示
                event = st.dataframe(
                    styled_df, 
                    use_container_width=True, 
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row"
                )
                
                # 处理行选中
                if event and event.get("selection") and event["selection"]["rows"]:
                    selected_row_idx = event["selection"]["rows"][0]
                    selected_code = df_results.iloc[selected_row_idx]['代码']
                    selected_name = df_results.iloc[selected_row_idx]['名称']
                    st.session_state.selected_td_stock = {"code": selected_code, "name": selected_name}
            else:
                st.warning(f"目前 {current_date} 无 TD 信号。请在左侧点击“开始扫描”。")

        with right_col:
            if st.session_state.selected_td_stock:
                code = st.session_state.selected_td_stock["code"]
                name = st.session_state.selected_td_stock["name"]
                st.subheader(f"📊 K线预览: {name} ({code})")
                
                df_chart = get_clean_df(code)
                if not df_chart.empty:
                    # 找到当前日期在 DataFrame 中的索引
                    date_series = pd.to_datetime(df_chart['date']).dt.strftime('%Y-%m-%d')
                    chart_idx_list = date_series[date_series <= current_date].index
                    if not chart_idx_list.empty:
                        chart_idx = chart_idx_list[-1]
                        render_chart_area(code, name, df_chart, chart_idx, show_ma=True)
                    else:
                        st.warning("无法定位到当前日期的K线数据。")
                else:
                    st.error("无法加载该股票的K线数据。")
            else:
                st.info("👈 请点击左侧列表中的股票以预览K线图。")

    # 2. 图表复盘视图 (原有逻辑)
    else:
        # 1. 选股策略
        st.sidebar.divider()
        st.sidebar.subheader("🎯 策略筛选")
        strategy_opt = st.sidebar.selectbox("选择策略", ["无", "TD"], index=1 if "TD" in st.session_state.get('selected_stock_str', '') else 0)
        
        signal_type = "全部"
        if strategy_opt != "无":
            available_signals = get_signal_types_for_strategy(current_date, strategy_opt)
            if available_signals:
                signal_type = st.sidebar.selectbox("信号类型", ["全部"] + available_signals)

        # 2. 股票选择
        stock_list = get_stock_list_by_strategy(strategy_opt, signal_type, current_date)
        
        # 确定初始选中的股票
        default_index = 0
        if 'selected_stock_str' in st.session_state and st.session_state.selected_stock_str in stock_list:
            default_index = stock_list.index(st.session_state.selected_stock_str)

        if not stock_list:
            st.sidebar.error(f"所选策略/日期下无匹配股票。")
            if strategy_opt == "无": return
            selected_stock = ""
        else:
            selected_stock = st.sidebar.selectbox("选择标的", stock_list, index=default_index)
            st.session_state.selected_stock_str = selected_stock

        if not selected_stock:
            st.info("💡 请在左侧选择策略并扫描，或在“TD 策略分析”中运行全量扫描。")
            return

        stock_code = selected_stock.split(']')[0].replace('[', '').strip()
        
        # 加载全量数据
        df = get_clean_df(selected_stock)
        if df.empty:
            st.warning(f"标的 {selected_stock} 暂无日线数据。")
            return

        # 3. 复盘日记
        st.sidebar.divider()
        st.sidebar.subheader("📝 复盘日记")
        current_note = load_note_from_db(stock_code)
        new_note = st.sidebar.text_area("逻辑存证", value=current_note, height=200, key=f"note_{stock_code}")
        if st.sidebar.button("💾 存档", use_container_width=True):
            save_note_to_db(stock_code, new_note)
            st.sidebar.success("已存档")

        # 指标开关
        st.sidebar.divider()
        st.sidebar.subheader("📈 指标显示")
        show_ma = st.sidebar.checkbox("显示均线 (MA5/MA20)", value=False)

        # 渲染图表
        render_chart_area(stock_code, selected_stock, df, current_idx, show_ma)

    # --- 统一 CSS 优化 ---
    st.markdown("""
        <style>
            /* 强制稳定侧边栏宽度，减少重载时的位移感 */
            [data-testid="stSidebar"] {
                min-width: 350px !important;
                max-width: 350px !important;
            }
            /* 隐藏 Streamlit 自载的过度动画，减少闪动 */
            [data-testid="stAppViewBlockContainer"] {
                padding-top: 2rem !important;
                transition: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # 执行渲染
    # render_chart_area(stock_code, selected_stock, df, current_idx, show_ma) 已经在上面分模式执行了

    # 快捷键突破 (注入并映射到侧边栏按钮)
    st.components.v1.html(f"""
    <script>
        const doc = window.parent.document;
        const keyboardHandler = (e) => {{
            if (e.key === 'ArrowLeft') {{
                const btn = Array.from(doc.querySelectorAll('button')).find(b => b.innerText.includes('前一天'));
                if (btn) btn.click();
            }} else if (e.key === 'ArrowRight') {{
                const btn = Array.from(doc.querySelectorAll('button')).find(b => b.innerText.includes('后一天'));
                if (btn) btn.click();
            }}
        }};
        doc.removeEventListener('keydown', keyboardHandler);
        doc.addEventListener('keydown', keyboardHandler);
    </script>
    """, height=0)

if __name__ == "__main__":
    main()
