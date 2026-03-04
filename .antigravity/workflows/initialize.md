---
description: 环境初始化 — Next.js 前端 + Python 后端 + TailwindCSS v4
---

## 0. 检查运行时环境

// turbo
1. 检查 Node.js 版本（需 v18+）
   CommandLine: node -v

// turbo
2. 检查 Python 版本（需 3.11+）
   CommandLine: python --version

---

## 1. 初始化 Git 仓库

// turbo
3. git init
   CommandLine: git init

// turbo
4. 创建 .gitignore
   CommandLine: |
     echo "node_modules/\n.next/\n__pycache__/\n.venv/\n*.pyc\n.env\n.env.local" > .gitignore

---

## 2. 创建项目目录结构

// turbo
5. 创建 frontend / backend 目录
   CommandLine: mkdir frontend && mkdir backend

---

## 3. 前端：Next.js + TailwindCSS v4

// turbo
6. 创建 Next.js 项目（非交互模式，App Router，TypeScript，ESLint，src/）
   CommandLine: npx -y create-next-app@latest frontend --ts --eslint --app --src-dir --import-alias "@/*" --no-tailwind

// turbo
7. 安装 TailwindCSS v4（Vite 插件版已废弃，Next.js 使用 PostCSS 插件）
   CommandLine: cd frontend && npm install tailwindcss @tailwindcss/postcss postcss

// turbo
8. 写入 postcss.config.mjs（启用 TailwindCSS v4 PostCSS 插件）
   CommandLine: |
     echo "export default { plugins: { '@tailwindcss/postcss': {} } };" > frontend/postcss.config.mjs

// turbo
9. 替换 frontend/src/app/globals.css 仅保留 v4 导入
   CommandLine: |
     echo "@import 'tailwindcss';" > frontend/src/app/globals.css

// turbo
10. 安装 UI 增强库
    CommandLine: cd frontend && npm install framer-motion lucide-react clsx tailwind-variants react-icons

// turbo
11. 添加路径别名到 tsconfig（已由 create-next-app 生成，此步确认）
    CommandLine: cd frontend && cat tsconfig.json

---

## 4. 后端：Python (FastAPI)

// turbo
12. 创建 Python 虚拟环境
    CommandLine: cd backend && python -m venv .venv

// turbo
13. 激活虚拟环境（Windows）
    CommandLine: backend\.venv\Scripts\activate

// turbo
14. 安装 FastAPI + Uvicorn + 常用依赖
    CommandLine: cd backend && .venv\Scripts\pip install fastapi uvicorn[standard] pydantic python-dotenv httpx

// turbo
15. 生成 requirements.txt
    CommandLine: cd backend && .venv\Scripts\pip freeze > requirements.txt

// turbo
16. 创建后端入口文件 backend/main.py
    CommandLine: |
      echo "from fastapi import FastAPI
      from fastapi.middleware.cors import CORSMiddleware

      app = FastAPI()

      app.add_middleware(
          CORSMiddleware,
          allow_origins=['http://localhost:3000'],
          allow_credentials=True,
          allow_methods=['*'],
          allow_headers=['*'],
      )

      @app.get('/api/health')
      def health():
          return {'status': 'ok'}" > backend/main.py

---

## 5. 运行 Bootstrap 文档工作流

17. 执行 bootstrap.md，生成 L1/L2/L3 文档结构
    → 手动调用 bootstrap 工作流（见 .antigravity/workflows/bootstrap.md）

---

## 6. 首次 Git 提交

// turbo
18. 提交初始代码
    CommandLine: git add . && git commit -m "🚀 Init: Next.js + FastAPI + TailwindCSS v4"

---

## 完成后目录结构

```
project-root/
├── .antigravity/
│   ├── config.yaml
│   └── workflows/
│       ├── initialize.md   ← 本文件
│       ├── bootstrap.md    ← 文档播种工作流
│       └── sync_doc.md     ← 代码 ↔ 文档回环同步
├── frontend/               ← Next.js App Router + TailwindCSS v4
│   ├── src/app/
│   ├── postcss.config.mjs
│   └── package.json
├── backend/                ← FastAPI + Uvicorn
│   ├── main.py
│   ├── requirements.txt
│   └── .venv/
├── CLAUDE.md               ← L1 根文档（bootstrap 生成）
└── .gitignore
```
