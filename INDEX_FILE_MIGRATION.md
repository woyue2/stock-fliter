# 索引文件位置变更总结

## 📋 变更说明

将股票索引文件从项目根目录移至 `get-data/data/` 目录，实现三个分析模块的数据共享。

## 🔄 变更内容

### 文件位置
- **旧位置**：`stocks_index.csv`（项目根目录）
- **新位置**：`get-data/data/stocks_index.csv`
- **原因**：三个分析模块（check-new-indicators、check-steady-uptrend、check-trend-bottom）共享同一个索引文件

### 修改的文件

#### 1. 三个分析模块的 HTML 报告生成器
- `check-new-indicators/reporters/html_reporter.py`
- `check-steady-uptrend/reporters/html_reporter.py`
- `check-trend-bottom/reporters/html_reporter.py`

**修改内容**：
```python
# 旧代码
index_file = Path(__file__).parent.parent.parent / "stocks_index.csv"

# 新代码
index_file = Path(__file__).parent.parent.parent / "get-data" / "data" / "stocks_index.csv"
```

#### 2. API 服务器
- `api_server.py`

**修改内容**：
```python
# 旧代码
INDEX_FILE = Path(__file__).parent / "stocks_index.csv"

# 新代码
INDEX_FILE = Path(__file__).parent / "get-data" / "data" / "stocks_index.csv"
```

#### 3. 新增文档
- `get-data/data/README.md` - 数据目录说明文档

#### 4. 更新文档
- `README_API.md` - 更新索引文件路径说明
- `CHANGELOG.md` - 记录此次变更

## ✅ 验证结果

所有配置已正确更新：
- ✓ 索引文件已移至 `get-data/data/stocks_index.csv`
- ✓ 三个分析模块配置已更新
- ✓ API 服务器配置已更新
- ✓ 文档已更新

## 🎯 优势

1. **统一管理**：所有数据文件集中在 `get-data/data/` 目录
2. **模块共享**：三个分析模块共享同一个索引文件
3. **清晰结构**：项目根目录更整洁
4. **符合规范**：数据文件放在专门的数据目录中

## 📝 使用说明

### 生成索引数据
运行任意分析模块，会自动追加数据到索引文件：
```bash
python check-new-indicators/main.py
python check-steady-uptrend/main.py
python check-trend-bottom/main.py
```

### 使用搜索功能
1. 启动 API 服务：`python api_server.py` 或双击 `start_api.bat`
2. 打开 `reports_index.html`
3. 使用搜索功能查找股票

### 清空索引
如需重新生成索引，删除文件即可：
```bash
del get-data\data\stocks_index.csv
```

## 🔍 测试

运行测试脚本验证功能：
```bash
test_search.bat
```

## ⚠️ 注意事项

1. 索引文件被 `.gitignore` 忽略，不会提交到 Git
2. 每次运行分析模块都会追加新数据，不会覆盖
3. 如果索引文件不存在，首次运行会自动创建

## 📅 变更日期

2026-01-31

## 👤 变更原因

用户反馈：索引文件应该保存在 `get-data/data/` 目录中，因为不只有一个分析模块，还有 bottom 和 uptrend 模块需要共享数据。

