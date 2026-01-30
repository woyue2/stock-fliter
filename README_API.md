# 股票跨报告搜索功能使用指南

## 📋 功能说明

在 `reports_index.html` 中实现了股票搜索功能，可以：
- 🔍 搜索某个股票在不同日期、不同指标模块中的出现情况
- 📊 查看热门股票（出现次数最多）
- 📈 查看统计信息（总记录数、独立股票数、日期范围等）

## 🚀 使用步骤

### 1. 生成报告（自动生成索引）

运行任意一个分析模块，会自动将股票数据追加到 `stocks_index.csv`：

```bash
# 新指标分析
python check-new-indicators/main.py

# 稳步上升分析
python check-steady-uptrend/main.py

# TD底部分析
python check-trend-bottom/main.py
```

### 2. 启动API服务

**方式1：使用批处理文件（推荐）**
```bash
双击 start_api.bat
```

**方式2：命令行启动**
```bash
python api_server.py
```

服务启动后会显示：
```
索引文件: C:\Users\Administrator\Desktop\Park\stocks-fliter\get-data\data\stocks_index.csv
API服务启动: http://localhost:5000
```

### 3. 打开索引页面

双击打开 `reports_index.html`，即可使用搜索功能。

## 🔍 搜索功能

### 搜索股票
- 输入股票代码（如：`600519`）或名称（如：`茅台`）
- 点击"搜索"按钮
- 查看该股票在所有报告中的出现记录

### 热门股票
- 点击"热门股票"按钮
- 查看出现次数最多的前20只股票
- 点击"查看详情"可以查看该股票的所有记录

### 统计信息
- 点击"统计信息"按钮
- 查看总记录数、独立股票数、日期范围、各模块统计等

## 📊 API接口

### 搜索股票
```
GET /api/search?code=600519
GET /api/search?name=茅台
GET /api/search?date=2026-01-30
GET /api/search?module=稳步上升
```

### 热门股票
```
GET /api/hot-stocks?limit=20
```

### 统计信息
```
GET /api/stats
```

## 📁 文件说明

- `get-data/data/stocks_index.csv` - 股票索引数据（自动生成，三个模块共享）
- `api_server.py` - Flask API服务
- `start_api.bat` - API服务启动脚本
- `reports_index.html` - 报告索引页面（包含搜索功能）

## 🔧 依赖安装

如果首次使用，需要安装依赖：

```bash
pip install flask flask-cors pandas
```

## ⚠️ 注意事项

1. **必须先启动API服务**，否则搜索功能无法使用
2. **索引文件会自动追加**，每次生成报告都会添加新记录
3. **如需清空索引**，删除 `get-data/data/stocks_index.csv` 文件即可
4. **API服务默认端口5000**，如果端口被占用，可以修改 `api_server.py` 中的端口号
5. **索引文件位置**：`get-data/data/stocks_index.csv`（三个分析模块共享）

## 📈 性能说明

- 搜索速度：< 100ms
- 支持记录数：< 10万条
- 并发支持：适合个人使用

## 🎯 示例

### 搜索贵州茅台
1. 启动API服务
2. 打开 `reports_index.html`
3. 输入 `600519` 或 `茅台`
4. 点击搜索
5. 查看结果，点击"查看报告"可以直接跳转到对应报告

### 查看热门股票
1. 打开 `reports_index.html`
2. 点击"热门股票"按钮
3. 查看出现次数最多的股票
4. 点击"查看详情"查看该股票的所有记录

## 🐛 故障排除

### 搜索失败
- 检查API服务是否启动
- 检查浏览器控制台是否有错误信息
- 确认 `get-data/data/stocks_index.csv` 文件存在

### 端口被占用
- 修改 `api_server.py` 中的端口号（默认5000）
- 同时修改 `reports_index.html` 中的 `API_BASE` 地址

### 中文乱码
- 确保文件编码为 UTF-8
- CSV文件使用 UTF-8-BOM 编码

## 📝 更新日志

### 2026-01-31
- ✅ 实现CSV索引自动生成
- ✅ 创建Flask API服务
- ✅ 添加搜索、热门股票、统计功能
- ✅ 修改三个HTML报告生成器，自动导出索引
- ✅ 修复报告路径问题（使用正斜杠格式）
- ✅ 将索引文件移至 `get-data/data/` 目录（三个模块共享）

