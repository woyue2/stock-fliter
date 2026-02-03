# 云端轻量 Runner 方案（1核1G 环境）

> 目标：在低配置服务器（1核CPU + 1G 内存）上，尽量不依赖长期保留 `raw/*.csv`，通过“边获取、边分析、用完即丢”的方式完成每日九底 / 稳步上升 / 新指标分析，并保持现有 `selected_stocks_all.csv` 逻辑不变。
## 零、所有代码文件，均在./PlanToDeploy中执行，可以参考但不要引用该文件夹以外的文件
---

## 一、设计原则

- **不改动** `get-data/data/selected_stocks_all.csv` 的生成和更新逻辑，只把它当作“固定股票池 + 行业信息”。
- 保留现有模块（`check-trend-bottom`、`check-steady-uptrend`、`check-new-indicators`）的文件结构和报告生成方式，优先复用现有分析函数。
- 在“流式模式”下：
  - 尽量不写入 `get-data/data/raw/*.csv`，或只保留有限窗口（例如最近 N 天）。
  - 只在模块自己的 `output/` 下写结果（CSV + HTML）和全局 `stocks_index` 索引。
- 适配 1G 内存：任何时刻只在内存中保留“少数几只股票的数据 + 汇总 DataFrame”，不加载全市场历史。

---

## 二、整体流程概览（伪代码）

### 1. 顶层入口 `stream_run_daily.py`

```python
def main(end_date: str | None = None):
    # 1) 读取股票池（固定住 selected_stocks_all.csv）
    stocks = load_stock_pool_from_selected_all()

    # 2) 逐只股票拉取日线数据（只保留最近 N 天）
    #    对每个模块分别维护一个“命中结果列表”
    td_results = []
    steady_results = []
    new_ind_results = []

    for stock in stocks:
        df_daily = fetch_daily_data_streaming(stock.code, end_date=end_date, days=DEFAULT_DAYS)
        if df_daily is None or df_daily.empty:
            continue

        # 2.1 九底分析（返回命中的一行 dict 或 None，不写中间文件）
        td_row = analyze_td_bottom_single_stock(df_daily, stock)
        if td_row is not None:
            td_results.append(td_row)

        # 2.2 稳步上升分析
        steady_row = analyze_steady_single_stock(df_daily, stock)
        if steady_row is not None:
            steady_results.append(steady_row)

        # 2.3 新指标分析
        new_row = analyze_new_indicator_single_stock(df_daily, stock)
        if new_row is not None:
            new_ind_results.append(new_row)

        # 重要：此处不要把 df_daily 写入 raw/*.csv，也不要长期持有，只在循环内短暂使用

    # 3) 各模块汇总结果 → DataFrame → 生成 CSV + HTML + stocks_index 索引
    build_td_reports_and_index(td_results, end_date)
    build_steady_reports_and_index(steady_results, end_date)
    build_new_indicator_reports_and_index(new_ind_results, end_date)

    # 4) 生成 report_index / reports_index_YYYY-MM-DD / ...（复用 scripts/build_reports_index.py）
    build_global_reports_index()
```

---

## 三、关键组件设计

### 1. 股票池与行业信息（只读）

```python
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

@dataclass
class StockInfo:
    code: str      # 6位代码，如 '600000'
    name: str
    bs_code: str   # 如 'sh.600000'
    industry: str  # 行业中文，允许为空字符串


def load_stock_pool_from_selected_all() -> list[StockInfo]:
    csv_path = Path("get-data/data/selected_stocks_all.csv")
    df = pd.read_csv(csv_path, dtype=str)

    stocks: list[StockInfo] = []
    for _, row in df.iterrows():
        code = str(row.get("code", "")).zfill(6)
        name = str(row.get("name", ""))
        bs_code = str(row.get("bs_code", "")) or ("sh." + code if code.startswith("6") else "sz." + code)
        industry = str(row.get("industry", ""))  # 这里尊重文件内容，不做任何改写

        if code:
            stocks.append(StockInfo(code=code, name=name, bs_code=bs_code, industry=industry))

    return stocks
```

> 说明：这里完全“读-only”，不写回 `selected_stocks_all.csv`，确保该文件可以被视为固定配置。

### 2. 流式获取单只股票的日线数据

可复用 `get-data/main.py` 中已有的 Baostock / Tencent 拉取逻辑，但改成“单只股票函数”，只返回 DataFrame，不写 `raw/*.csv`：

```python
def fetch_daily_data_streaming(code: str, end_date: str | None, days: int) -> pd.DataFrame:
    """
    流式获取单只股票最近 N 天日线数据。
    - 优先 Baostock，失败再回退 Tencent。
    - 不落盘，只返回 DataFrame。
    """
    # 计算时间窗口 [start, end]
    # 这里可以复用 get-data.main.compute_fetch_range 的逻辑，但不需要 existing_df

    # 1) 尝试 Baostock
    df_bs, err = fetch_baostock_daily_streaming(code, start_date, end_date)
    if df_bs is not None and not df_bs.empty:
        return df_bs

    # 2) 失败时回退腾讯接口
    df_tx = fetch_tencent_daily(code, count=days)
    return df_tx
```

> 实现时建议从 `get-data/main.py` 中抽出可复用的“单股获取”逻辑，放到一个 util 函数里，但**不要改写已有的 main 行为**，而是新增一个专门给 runner 用的“纯内存模式”函数。

### 3. 单股分析接口（九底 / 稳步上升 / 新指标）

目前模块的分析都是批量型（一次跑完所有股票），在“流式模式”中，可以复用内部的“指标计算 + 打分”逻辑，包装成“单股版本”：

#### 3.1 九底（TD）单股分析

```python
from check-trend-bottom.analyzers.td_analyzer import TDAnalyzer, TDAnalyzerConfig

def analyze_td_bottom_single_stock(df_daily: pd.DataFrame, stock: StockInfo) -> dict | None:
    """
    使用 TDAnalyzer 的内部逻辑，对单只股票执行九底分析。
    返回命中结果的一行 dict（包含代码/名称/行业/共振级别等），不命中则返回 None。
    """
    # 这里有两种实现策略：
    # A. 复用现有 _analyze_stock / _build_resonance 逻辑，抽出一个静态方法；
    # B. 在 runner 中复制一份轻量版本，只计算日/周/月 TD 计数和共振级别。

    analysis = td_analyze_core(df_daily)  # 自己封装的核心逻辑
    if analysis["共振级别"] == "无底部信号":
        return None

    return {
        "代码": stock.code,
        "名称": stock.name,
        "行业": stock.industry or "未知",
        "板块": get_board_type(stock.code),  # 可复用 check-trend-bottom/data_loader.get_board_type
        **analysis,
    }
```

#### 3.2 稳步上升 / 新指标单股分析

做法类似：复用各自模块的分析函数，把“批量 DataFrame”改成“单股 DataFrame”，只在命中时返回一行 dict。

---

## 四、结果汇总与报告生成

在流式 runner 中，我们只维护“命中结果列表”，全部跑完后再进入“批量生成报告”的阶段，这一部分可以尽量复用现有 reporter：

```python
def build_td_reports_and_index(results: list[dict], end_date: str | None):
    if not results:
        print("[TD] 当日无九底信号，跳过报告生成")
        return

    df = pd.DataFrame(results)

    # 使用现有 Pipeline/HTMLReporter 的思路构建 output 目录
    output_root = Path("check-trend-bottom/output")
    date_str = end_date or df["日最新日期"].max()  # 或直接用传入的 end_date
    time_str = datetime.now().strftime("%H-%M-%S")
    output_dir = output_root / date_str / time_str
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1) 保存 CSV
    csv_path = output_dir / f"td_analysis_{date_str.replace('-', '')}_{time_str.replace('-', '')}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # 2) 调用 MarkdownReporter / HTMLReporter 生成 MD + HTML
    md_reporter = MarkdownReporter(output_dir, end_date=date_str)
    md_reporter.generate(df, title="TD九底分析报告")

    html_reporter = HTMLReporter(output_dir, end_date=date_str, display_date=date_str)
    summary_path = html_reporter.generate(df, title="TD九底分析报告")

    # 3) HTMLReporter 内部已经调用 _export_to_index_csv()，会把索引写入
    #    get-data/data/stocks_index/<date>/stocks_index.csv，无需额外构建。
```

稳步上升 / 新指标模块可以做对应的 `build_steady_reports_and_index()` / `build_new_indicator_reports_and_index()`，保持与原有 reporter 的输出结构一致。

---

## 五、与现有批处理脚本的关系

- `run_all_strategies.py` 保持原状，仍然走“先写 raw，再批量分析”的模式，更适合本地大硬盘环境。
- 新的 `stream_run_daily.py` 专门用于“云端轻量模式”：  
  - 只读 `selected_stocks_all.csv`；  
  - 流式拉取数据，不保存 raw；  
  - 只保留汇总结果和 HTML 报告 + stocks_index 索引。
- 在 PlanToDeploy 层面，可以约定：  
  - 本地：继续用 `run_all_strategies.py`；  
  - 1核1G 云端：使用 `stream_run_daily.py` + `api_server.py`，必要时搭配更轻量的保留窗口（只保留最近 N 天的报告目录）。

---

## 六、后续实现建议

1. **优先实现单股拉取函数**：从 `get-data/main.py` 抽取“拉取单股最近 N 天数据”的逻辑，放入一个 util 模块（例如 `get-data/stream_fetch.py`），保持原 main 不变。  
2. **封装九底/稳步上升/新指标的“单股分析核心”**，尽量调用现有的指标计算函数，而不是重新发明规则。  
3. 在根目录新增 `stream_run_daily.py`，按本文件的伪代码串联三个模块。  
4. 在 `PlanToDeploy/流程流畅.txt` 或其他部署文档中，标注：  
   - 本地使用 `run_all_strategies.py`  
   - 云端使用 `stream_run_daily.py`  
   - 两者都依赖同一个 `selected_stocks_all.csv` 作为股票池和行业来源。

---

## 七、风险点与实现细节补充

### 1. 设计落地的关键点

- 明确“只读 `selected_stocks_all.csv` + 不改原有 main 行为”，把云端模式全部收敛到**新增入口（`stream_run_daily.py`）和新增 util**，上线风险可控。  
- 单股拉取后，在一次循环里**同时喂给“九底 / 稳步上升 / 新指标”三个分析**，避免为三个模块各自重复打接口，整体复杂度和耗时都在可接受范围内。  
- 输出阶段继续复用各模块现有的 Reporter / HTML 结构与 `stocks_index` 目录，不重新设计结果结构，便于和现有前端/索引对接。

### 2. 主要风险 / 易踩坑点

- **外部接口压力**：如果股票池很大，在 1 核 1G 上串行拉完所有股票，整体耗时会偏长；同时如果 Baostock / 腾讯接口有频控，需要增加简单的节流（`sleep`）或失败重试 / 跳过策略。  
- **结果内存聚合**：命中结果通常不多，但在“极端行情 + 多策略”的情况下，三个 `results` 列表都有几千行时，最后 DataFrame 合并要注意只保留必要字段，避免把原始 K 线整段塞进去。  
- **代码复用边界**：方案中提到“抽出单股核心逻辑”，实现时如果只是复制粘贴现有内部函数，很容易出现“本地批量模式修了逻辑但流式模式忘记更新”的双轨问题，建议强制让两种入口共用同一分析核心。

### 3. 实现细节建议

- `fetch_daily_data_streaming` 尽量做成真正的公共 util：本地批量模式也可以在内部基于它封装一个“多股版本”，这样未来改接口 / 加字段时只要改一处。  
- 单股分析函数（例如 `analyze_td_bottom_single_stock`）优先从现有 TDAnalyzer / 稳步上升分析器中抽方法，而不是从报告层倒推规则，避免埋逻辑偏差；同时增加一组“同一天用旧 main 和 `stream_run_daily` 对比结果”的回归测试。  
- 报告生成函数里，可以把“构建 `output_dir` + 命名规则 + 写 CSV / HTML + 写 index”的公共部分抽到一个小 helper，确保和现有 main 的目录结构完全一致，避免前端查找路径时出现“云端跑出来的报告看不见”的问题。  
- 建议在云端 runner 里加入简单的“进度 / 故障日志”（例如每处理完 N 只股票打印一次进度、记录失败股票列表），方便在资源紧张环境下排查“为什么今天报告条数明显变少 / 变多”的问题。
