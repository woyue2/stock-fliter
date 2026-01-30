# 架构设计

## 总体架构
```mermaid
flowchart TD
    A[run_scan.py/run_td_scan.py] --> B[data_fetcher.py]
    A --> C[technical_indicators.py]
    A --> D[stock_scanner.py]
    B --> E[akshare API]
    C --> F[Pandas计算]
    D --> G[筛选逻辑]
    A --> H[Excel输出]
```

## 技术栈
- **后端:** Python 3.x
- **数据获取:** akshare（开源金融数据接口库）
- **数据处理:** pandas（数据分析库）
- **Excel输出:** openpyxl（Excel文件处理库）
- **命令行解析:** argparse（Python标准库）

## 核心流程
```mermaid
sequenceDiagram
    Participant User as 用户
    Participant Runner as 运行脚本
    Participant Fetcher as 数据获取模块
    Participant Indicator as 指标计算模块
    Participant Scanner as 扫描器模块
    Participant Output as 结果输出
    
    User->>Runner: 执行扫描命令
    Runner->>Fetcher: 获取股票列表和历史数据
    Fetcher->>Indicator: 传递K线数据
    Indicator->>Scanner: 计算技术指标
    Scanner->>Output: 筛选并输出结果
    Output->>User: 生成Excel报告
```

## 重大架构决策
完整的ADR存储在各变更的how.md中，本章节提供索引。

| adr_id | title | date | status | affected_modules | details |
|--------|-------|------|--------|------------------|---------|