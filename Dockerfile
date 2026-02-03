FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# 安装系统依赖（如有需要可在此扩展）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 暴露 API 端口
EXPOSE 5000

# 允许通过环境变量覆盖监听地址/端口
ENV HOST=0.0.0.0 \
    PORT=5000

# 默认启动搜索 API 服务
CMD ["sh", "-c", "gunicorn -b ${HOST}:${PORT} api_server:app"]

