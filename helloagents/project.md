# 项目技术约定

---

## 技术栈
- **核心:** Python 3.x
- **数据获取:** akshare
- **数据处理:** pandas
- **Excel输出:** openpyxl
- **命令行解析:** argparse

---

## 开发约定
- **代码规范:** 遵循PEP8规范
- **命名约定:** 
  - 变量名: 下划线命名法（如: stock_code）
  - 函数名: 下划线命名法（如: get_stock_data）
  - 类名: 驼峰命名法（如: StockScanner）
- **文件命名:** 小写字母+下划线（如: data_fetcher.py）

---

## 错误与日志
- **策略:** 统一异常处理，网络请求失败自动重试3次
- **日志:** 使用print输出，包含进度信息和错误提示

---

## 测试与流程
- **测试:** 提供快速测试脚本（quick_test.py）
- **提交:** 未明确规范，建议使用清晰的提交信息

---

## 依赖管理
- 使用requirements.txt管理依赖
- 主要依赖: pandas, akshare, openpyxl