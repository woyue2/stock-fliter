# 项目演进日志 (Evolution Log)

> 格式：每条 TODO / 技术债 / 已完成重构 按时间倒序追加。
> 状态标记：🔴 待处理 | 🟡 进行中 | ✅ 已完成

---

# 2026-03-13
## 变动  优化数据同步性能 (方案 2) 与 Streamlit UI 交互稳定性
### 原因  1. 股票同步 (5400+ 文件) 耗时过长，单文件数据库连接开销巨大。
        2. Streamlit 页面切换日期时闪烁严重，影响复盘效率。
### 影响  1. **性能**：重构 `sync_missing_to_db.py` 为“内存聚合版”，通过全量指纹库实现秒级对账，入库改用单笔大事务。
        2. **UI**：`main.py` 引入 `@st.fragment` 隔离刷新，锁定 CSS 侧边栏宽度，新增左右方向键全局翻页。
        3. **规范**：补齐 `util/L2` 文档并更新头部契约。

## 变动  实现 Smile Number 战法全量回测工具并集成“黄金勾”与“缩量”因子
### 原因  需要科学量化 Smile Number 的战果，验证 RSI 拐点与成交量萎缩对胜率的提升效果。
### 影响  1. **回测引擎**：新建 `verify_db_probability.py`，采用多进程并发架构，支持 T+2 移动止损 (2%) 模拟。
        2. **黄金勾因子**：实现 RSI-6 过滤，通过 `RSI < 35 且向上勾头` 将日均收益从 0.8% 提升至 1.2%。
        3. **缩量因子**：引入 `vol_shrink` 过滤（当日成交量 < 前日），进一步提升选股精度。
        4. **UI 增强**：在 `valueCellMAx` 中集成手动搜码、个股复盘日记（入库存储）以及更稳定的表格行选中逻辑。

## 变动  修复数据同步脚本中的 typo 并修正快照行情日期获取逻辑
### 原因  1. `sync_missing_to_db.py` 中 `drop_columns` 方法调用错误导致同步中断。
        2. `fetch_daily_snap.py` 在凌晨运行时错误使用系统日期，导致数据标签跨天错误。
### 影响  1. 将 `drop_columns` 修正为 pandas 标准 of `drop(columns=...)`，恢复同步流程。
        2. 在 `fetch_daily_snap.py` 中引入 `get_actual_trade_date` 逻辑，通过新浪指数接口实时对齐行情日期，并提供 9 点前自动预测“昨天”的回退机制。
        3. 连板天梯脚本集成“区域热力分布”分析，支持按省份自动统计涨停分布（基于正则匹配与地图映射）。

# 2026-03-12
## 变动  实现 CSV 备份与 SQLite 数据库的双向自动同步与数据补全
### 原因  用户提出“CSV 补全 SQLite，SQLite 抓取补全 CSV”的需求，旨在消除两套存储系统之间的数据孤岛，提高数据冗余可靠性。
### 影响  1. 重构 `scripts/sync_missing_to_db.py`：实现 `sync_bidirectional` 逻辑，支持高并发对齐。
        2. 升级 `fetch_daily_snap.py`：快照入库后自动触发 CSV 增量补全，实现“秒级抓取，毫秒补全”。
        3. 优化 `fetch_daily_history.py`：将双向同步深度挂载至 K 线合并与断点检测环节。
        4. 升级 `scripts/verify_sync.py`：支持 DB vs CSV 行数精准校验。

# 2026-03-11
## 变动  新增 INT_MATH 规则至神奇数字选股公式
### 原因  13.94 (13=9+4) 这种“整数部分与两小数位数字之和/积的等式关系”未被原先独立位数的切割逻辑覆盖。
### 影响  修改 `神奇数字/规则.md`，追加全局变量 `INT_MATH` 并在 V1 与 V2 的汇总条件 `SQ_ALL` 中使用，提高了盘口语言的识别宽度。

## 技术债 / TODO 积压

### 🔴 TODO-001 — get-data 网络请求逻辑冗余

- **发现日期**: 2026-03-04
- **发现阶段**: `/review` 代码审查
- **坏味道类型**: 冗余（Duplication）
- **GEB 定位**: 不触发 FATAL/SEVERE，属于 WARN 级技术债

**现象**:

`get-data/main.py`（`fetch_tencent_daily`）与 `get-data/fetch_minute_data.py`（`fetch_minute_data`）内，网络请求模式高度相似：
- `requests.get(url, timeout=10, allow_redirects=True)` 模板重复
- 异常捕获、超时设置、`raise_for_status()` 分散两处，各自写一遍
- 将来若需要统一加 User-Agent、重试策略、代理配置，**必须两处同时改**（僵化）

**建议修复**:

提取至 `util/network_client.py`，暴露：
```python
def http_get(url: str, timeout: int = 10) -> requests.Response:
    """统一网络请求入口：超时 / 重试 / UA / 错误处理"""
```
两个文件均改为 `from util.network_client import http_get`。

**预估工作量**: S（≤2小时）

**修复优先级**: 低（仅在下次改动 get-data 时顺手做）

---

## 已完成重构记录

# 2026-03-07

## 变动  新增量化雷达四象限坐标轴终端（V5黑金版）并重构路径感知
### 原因  原有的放射图难以直观表达主力强度（绝对值）与正负属性（吸筹/出逃）的二维关系。用户分享报告需要高清移动端截图适配。
### 影响  引入 `radial_terminal_template.html` 四象限前端引擎并配备 `gen_radial_report.py` 数据生成脚本；新增带有重叠推算（Force Separation）的 HTML5 拖拽可视化功能；新增基于 `html2canvas` 的纯净版 iPhone 12 (578 x 865) 尺寸高清图片一键导出；大幅优化 `gen_pro_report.py` 以基于脚本相对绝对路径无缝支持全局调用。

## 变动  重构 check-zhulistrength 主力资金流策略，统一适配同花顺盘后双表数据
### 原因  截图软件与东方财富/通达信基础盘口口径定义不一致，为提高大资金分析准确性，放弃模糊识别并彻底转向同花顺资金结构计算
### 影响  引入 `run_daily_scan.py` 自动化读取每日 `input/` 文件的极简操作流。通过清洗与推演零和博弈算法（小单=-(大单+中单)）生成最终战报于 `output/`。所有早期实验验证脚本迁移至 `.archive/` 隐藏以降低维护噪音。

# 2026-03-10
## 变动  优化 .gitignore 规则并清理 Git 索引
### 原因  仓库中存在大量分析生成的 HTML、CSV、MD 等中间产物，导致索引臃肿且容易误提交。
### 影响  1. 更新根目录 `.gitignore`，全面覆盖各子模块的 `output/` 文件夹及临时数据。
        2. 执行 `git rm --cached` 重置索引，移除非必要的追踪文件。
        3. 按照结构化提交规范（feat/chore/docs）重组历史提交。
