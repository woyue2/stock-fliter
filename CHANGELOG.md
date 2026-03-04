# 更新日志

## 2026-01-31

### 🎉 新功能：跨报告股票搜索

#### 功能说明
实现了跨模块、跨日期的股票搜索功能，可以快速查找某个股票在所有分析报告中的出现情况。

#### 主要特性
- ✅ **自动索引生成**：三个分析模块运行时自动导出数据到统一索引
- ✅ **Flask API服务**：提供 REST API 接口
- ✅ **Web搜索界面**：在 `reports_index.html` 中集成搜索功能
- ✅ **热门股票统计**：显示出现次数最多的股票
- ✅ **统计信息**：总记录数、独立股票数、日期范围等

#### 文件修改

**新增文件：**
- `api_server.py` - Flask API 服务器
- `start_api.bat` - API 启动脚本
- `README_API.md` - 使用指南
- `get-data/data/stocks_index.csv` - 股票索引文件（自动生成）
- `get-data/data/README.md` - 数据目录说明

**修改文件：**
- `check-new-indicators/reporters/html_reporter.py` - 添加 `_export_to_index_csv()` 方法
- `check-steady-uptrend/reporters/html_reporter.py` - 添加 `_export_to_index_csv()` 方法
- `check-trend-bottom/reporters/html_reporter.py` - 添加 `_export_to_index_csv()` 方法
- `reports_index.html` - 添加搜索功能界面

#### 技术细节

**索引文件位置变更：**
- 原位置：项目根目录 `stocks_index.csv`
- 新位置：`get-data/data/stocks_index.csv`
- 原因：三个分析模块共享同一个索引文件

**路径格式修复：**
- 问题：CSV 中保存的报告路径使用反斜杠，导致浏览器无法打开
- 解决：转换为正斜杠格式（Web 标准）
- 示例：`check-new-indicators/output/2026-01-31/01-15-07/summary_20260130_011507.html`

**自动化流程：**
1. 运行任意分析模块（`main.py`）
2. 生成 HTML 报告
3. 自动提取股票数据
4. 追加到 `get-data/data/stocks_index.csv`
5. 通过 API 服务提供搜索功能

#### 使用方法

```bash
# 1. 生成报告（自动生成索引）
python check-new-indicators/main.py

# 2. 启动 API 服务
python api_server.py
# 或双击 start_api.bat

# 3. 打开 reports_index.html 使用搜索功能
```

#### 依赖安装

```bash
pip install flask flask-cors pandas
```

---

## 2026-01-30

### Git 仓库整理

#### 问题
- `check-steady-uptrend` 和 `check-trend-bottom` 子目录有自己的 `.git` 目录
- 导致被识别为 Git 子模块，无法正常提交

#### 解决方案
- 备份子目录的 Git 历史到 `git-history-backup/`
- 删除子目录的 `.git` 目录
- 合并到主仓库（Monorepo 架构）
- 更新 `.gitignore` 防止再次出现

#### 文件变更
- 新增：`git-history-backup/check-steady-uptrend-history.txt`
- 新增：`git-history-backup/check-trend-bottom-history.txt`
- 修改：`.gitignore` - 添加子目录 `.git` 忽略规则

---

## 2026-01-29

### Bug 修复

#### 修复 HTML 标题日期显示问题
- **问题**：当不提供 `end_date` 参数时，HTML 标题不显示日期
- **修复**：从数据中读取日期并显示
- **影响文件**：
  - `check-new-indicators/reporters/html_reporter.py`
  - `check-steady-uptrend/reporters/html_reporter.py`
  - `check-trend-bottom/reporters/html_reporter.py`

---

## 版本说明

当前版本：v1.1.0
- 主要功能：股票技术分析 + 跨报告搜索
- 支持模块：新指标、稳步上升、趋势底部
- 数据源：AKShare
- 报告格式：HTML + CSV 索引
