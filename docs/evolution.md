# 项目演进日志 (Evolution Log)

> 格式：每条 TODO / 技术债 / 已完成重构 按时间倒序追加。
> 状态标记：🔴 待处理 | 🟡 进行中 | ✅ 已完成

---

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

# 2026-03-05

## 变动  实现全系统并行扫描优化与智能资源调度
### 原因  单线程扫描 5000+ 股票耗时过长（1-2分钟），且需适配 2G 低配服务器避免 OOM
### 影响  引入 `ProcessPoolExecutor` 并行化 4 大核心分析模块；新增 `system_utils` 自动检测内存并触发 `LOW_MEM_MODE`；升级 `run_all_strategies.py` 为交互式调度向导。
