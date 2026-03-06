# API Contract

[PROTOCOL]: 变更代码后，通过 sync_doc.md 自动更新此契约文档。

## 概览
本文件记录 `server/api_server.py` 暴露出的所有接口契约，并供前端保持同步一致。
当前后端框架：Flask

---

## 接口详情

### 1. 首页
- **路径（PATH）**: `/`
- **请求方式（METHOD）**: `GET`
- **功能描述**: 股票搜索API 服务首页，返回简单的 HTML 欢迎页面及接口示例。
- **请求参数（Request）**: 无
- **响应数据（Response）**: `text/html`

### 2. 搜索股票
- **路径（PATH）**: `/api/search`
- **请求方式（METHOD）**: `GET`
- **功能描述**: 根据条件筛选索引记录中股票的综合分析结果。
- **请求参数（Request Schema）**: (Query 参数)
  - `code` (string, optional): 股票代码，如 `600519`
  - `name` (string, optional): 股票名称，如 `茅台`
  - `date` (string, optional): 分析日期，如 `2026-01-30`
  - `module` (string, optional): 分析模块，如 `MAxRSIx6U1D`
- **响应数据（Response Schema）**:
  ```json
  {
      "total": 100,
      "results": [
          {
              "代码": "600519",
              "名称": "贵州茅台",
              "日期": "2026-01-30",
              "模块": "MAxRSIx6U1D",
              "...": "..."
          }
      ]
  }
  ```
  *如不满足条件或索引不存在，返回 `error` message (HTTP 404)*

### 3. 系统统计信息
- **路径（PATH）**: `/api/stats`
- **请求方式（METHOD）**: `GET`
- **功能描述**: 获取全局股票索引库的概览统计数据。
- **请求参数（Request Schema）**: 无
- **响应数据（Response Schema）**:
  ```json
  {
      "total_records": 5000,
      "unique_stocks": 1200,
      "date_range": {
          "start": "2026-01-01",
          "end": "2026-01-30"
      },
      "modules": {
          "check-tdxmacdxvolume": 2000,
          "MAxRSIx6U1D": 1500
      },
      "latest_update": "2026-01-30 15:30:00"
  }
  ```

### 4. 热门股票
- **路径（PATH）**: `/api/hot-stocks`
- **请求方式（METHOD）**: `GET`
- **功能描述**: 获取在各个策略模块中提及/出现次数最多的股票排名。
- **请求参数（Request Schema）**: (Query 参数)
  - `limit` (integer, optional, default=20): 返回的条数限制
- **响应数据（Response Schema）**: 数组
  ```json
  [
      {
          "代码": "600519",
          "名称": "贵州茅台",
          "出现次数": 10
      }
  ]
  ```
