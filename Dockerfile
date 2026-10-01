# 基础镜像可用 --build-arg 覆盖（docker-compose.yml 默认指向 AWS ECR 公共镜像，
# 避免国内 docker hub 镜像源失效；官方构建不传参数即用 docker.io 原名）。
# 注意：用在 FROM 上的 ARG 必须声明在第一个 FROM 之前（全局作用域）。
ARG NODE_IMAGE=node:20-alpine
ARG PYTHON_IMAGE=python:3.12-slim

# ============================================================
# Stage 1: 构建前端 (Vite + React + TypeScript)
# ============================================================
FROM ${NODE_IMAGE} AS frontend

WORKDIR /build

# 先复制依赖描述文件，利用 Docker 层缓存
COPY package.json package-lock.json ./
RUN npm ci

# 复制源码并构建
COPY . .
RUN npm run build

# ============================================================
# Stage 2: 运行时 (Python 后端 + 已构建的静态文件)
# ============================================================
FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME_CONSOLE_HOST=0.0.0.0 \
    HOME_CONSOLE_PORT=8765 \
    HOME_CONSOLE_DATA=/app/server/data \
    HOME_CONSOLE_STATIC=/app/dist

# 安装 uv（项目的依赖管理工具）
RUN pip install uv

# ffmpeg：摄像头 RTSP → MJPEG 实时转码、ONVIF 不支持事件时的帧差检测都依赖它。
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/server

# 安装 Python 依赖（锁定版本）
COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --frozen --no-dev

# 复制后端源码
COPY server/ ./

# 复制前端构建产物
COPY --from=frontend /build/dist /app/dist

# 确保数据目录存在（会被卷挂载覆盖）
RUN mkdir -p /app/server/data

EXPOSE 8765

# 健康检查：使用服务自带的 /api/health 接口
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/api/health',timeout=3).status==200 else 1)" || exit 1

CMD ["uv", "run", "python", "-m", "home_console_server"]
