# 索引文件路径更新说明

## 更新日期
2026-01-31

## 更新内容

### 1. 修改目标
将所有模块的 `stocks_index.csv` 从固定路径改为按日期分类的路径结构：

**旧路径：**
```
get-data/data/stocks_index.csv
```

**新路径：**
```
get-data/data/stocks_index/{YYYY-MM-DD}/stocks_index.csv
```

### 2. 修改的文件

#### 2.1 check-new-indicators/reporters/html_reporter.py
- **修改方法：** `_export_to_index_csv()`
- **修改内容：** 
  - 根据报告日期创建对应的日期文件夹
  - 将 stocks_index.csv 写入到日期文件夹中
  - 自动创建目录（如果不存在）

#### 2.2 check-steady-uptrend/reporters/html_reporter.py
- **修改方法：** `_export_to_index_csv()`
- **修改内容：** 同上

#### 2.3 check-trend-bottom/reporters/html_reporter.py
- **修改方法：** `_export_to_index_csv()`
- **修改内容：** 同上

#### 2.4 scripts/build_reports_index.py
- **新增函数：** `get_latest_stocks_index_date()`
  - 自动查找最新日期的 stocks_index.csv
  - 返回最新日期字符串（格式：YYYY-MM-DD）

- **修改函数：** `main()`
  - 使用最新日期的 stocks_index.csv 生成报告索引
  - 将生成的 reports_index.html 和 reports_list.html 放入带日期的文件夹
  - 新路径：`report_index/reports_index_{YYYY-MM-DD}/`

#### 2.5 api_server.py
- **新增函数：** `get_latest_index_file()`
  - 自动查找最新日期的 stocks_index.csv
  - 支持向后兼容（如果没有日期目录，使用旧路径）

- **修改函数：** `load_index()`
  - 使用 `get_latest_index_file()` 获取最新索引文件
  - 在控制台输出当前使用的索引文件路径

### 3. 目录结构变化

#### 3.1 stocks_index 目录结构
```
get-data/data/
├── stocks_index/
│   ├── 2026-01-30/
│   │   └── stocks_index.csv
│   ├── 2026-01-31/
│   │   └── stocks_index.csv
│   └── ...
└── stocks_index.csv (旧文件，保留用于兼容)
```

#### 3.2 report_index 目录结构
```
report_index/
├── reports_index_2026-01-30/
│   ├── reports_index.html
│   └── reports_list.html
├── reports_index_2026-01-31/
│   ├── reports_index.html
│   └── reports_list.html
└── ...
```

### 4. 使用说明

#### 4.1 生成报告（各模块）
运行各模块的 main.py 时，会自动：
1. 从数据中提取日期信息
2. 创建对应日期的目录
3. 将索引数据写入 `get-data/data/stocks_index/{日期}/stocks_index.csv`

示例：
```bash
# check-new-indicators
cd check-new-indicators
python main.py

# check-steady-uptrend
cd check-steady-uptrend
python main.py

# check-trend-bottom
cd check-trend-bottom
python main.py
```

#### 4.2 生成报告索引
```bash
python scripts/build_reports_index.py
```

该脚本会：
1. 自动查找最新日期的 stocks_index.csv
2. 生成报告索引页面
3. 将生成的 HTML 文件放入 `report_index/reports_index_{日期}/` 目录

#### 4.3 启动 API 服务
```bash
python api_server.py
```

API 服务会：
1. 自动查找最新日期的 stocks_index.csv
2. 在控制台显示当前使用的索引文件路径
3. 提供搜索、统计等 API 接口

### 5. 测试验证

运行测试脚本验证修改：
```bash
python test_index_path.py
```

测试内容包括：
1. 验证索引文件路径是否正确
2. 验证 API 服务器能否找到最新索引文件
3. 验证 build_reports_index.py 的输出路径

### 6. 向后兼容性

- **api_server.py** 支持向后兼容：如果没有找到日期目录，会尝试使用旧的 `stocks_index.csv` 路径
- 旧的 `stocks_index.csv` 文件可以保留，不会影响新功能

### 7. 优势

1. **数据隔离：** 每个日期的数据独立存储，不会相互覆盖
2. **历史追溯：** 可以查看任意日期的索引数据
3. **自动管理：** 自动使用最新日期的数据，无需手动指定
4. **清晰组织：** 报告索引按日期分类，便于管理和查找

### 8. 注意事项

1. 确保各模块能正确从数据中提取日期信息
2. 日期格式统一为 `YYYY-MM-DD`
3. 如果数据中没有日期信息，会使用当前系统日期
4. 旧的 `stocks_index.csv` 文件可以保留作为备份

### 9. 相关文件

- `test_index_path.py` - 测试脚本
- `INDEX_PATH_UPDATE.md` - 本文档

## 更新完成

所有修改已完成并测试通过。各模块现在会将索引数据写入带日期的目录，报告索引也会按日期分类存储。

