---
description: 项目冷启动播种机 — Next.js + FastAPI + TailwindCSS v4 GEB 文档结构
---

## 目标

为 Next.js 前端 + Python 后端 双仓库结构生成三层分型文档（L1 / L2 / L3）

---

## 步骤

1. **L1 根文档**：检查项目根目录是否已有 `CLAUDE.md`，若没有则创建，内容包含：
   - 项目名称与总体目标
   - 技术栈：Next.js 14 (App Router) + TailwindCSS v4 + FastAPI (Python 3.11+)
   - 顶层目录说明（`frontend/`, `backend/`, `.antigravity/`）
   - 全局开发约定（命名规范、分支策略、文档同步协议）
   - 参考模板：
     ```markdown
     # <ProjectName> · L1 Root

     ## 技术栈
     - Frontend: Next.js 14 · App Router · TypeScript · TailwindCSS v4
     - Backend:  FastAPI · Python 3.11+ · Uvicorn · Pydantic v2
     - UI Lib:   framer-motion · lucide-react · clsx · react-icons

     ## 目录结构
     <directory>
       frontend/   — Next.js 前端
       backend/    — FastAPI 后端
       .antigravity/ — 配置与工作流
     </directory>

     ## 开发约定
     - 前端路由：App Router（`src/app/` 目录）
     - API 前缀：`/api/`（后端）、`/api/` Next.js 反向代理指向 `localhost:8000`
     - 环境变量：`.env.local`（前端）、`.env`（后端），均不提交 git
     - 文档同步：每次代码变更后运行 `sync_doc` 工作流
     ```

2. **L2 模块文档**（为每个主要目录生成 `CLAUDE.md`）：

   - `frontend/CLAUDE.md`：
     - 描述前端模块职责
     - 记录页面路由列表（`src/app/page.tsx` 等）
     - 记录组件成员列表（`src/components/`）
     - 记录 API 调用约定（fetch / axios / SWR）

   - `backend/CLAUDE.md`：
     - 描述后端模块职责
     - 记录路由文件列表（`routers/`）
     - 记录数据模型（`models/`, `schemas/`）
     - 记录依赖注入和中间件约定

3. **L3 文件级契约**（在业务文件顶部插入注释契约）：

   - **TypeScript / TSX 文件**（前端）：
     ```ts
     /**
      * [COMPONENT] <ComponentName>
      * [INPUT]     <props 类型名>
      * [OUTPUT]    <返回 JSX 描述>
      * [POS]       frontend/src/components/<ComponentName>.tsx
      * [DEPS]      lucide-react, framer-motion
      */
     ```

   - **Python 文件**（后端）：
     ```python
     """
     [MODULE]  <module_name>
     [INPUT]   <接受的请求体 Schema>
     [OUTPUT]  <返回的响应 Schema>
     [POS]     backend/<path>.py
     [DEPS]    fastapi, pydantic
     """
     ```

4. **完成后提交**：
   ```bash
   git add . && git commit -m "🚀 Bootstrap GEB 文档结构 (L1/L2/L3)"
   ```
