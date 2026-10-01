# Stage 1: Build Frontend
FROM node:22-slim AS frontend-builder
WORKDIR /frontend

# NPM 源 — 默认走内网缓存（192.168.50.12）；在其他网络构建时才需要传参覆盖：
#   --build-arg NPM_REGISTRY=https://registry.npmmirror.com
ARG NPM_REGISTRY=http://192.168.50.12:4873
RUN npm config set registry ${NPM_REGISTRY} && npm config set fetch-retries 5 --location=global

# 锁文件一起复制，npm ci 严格按 lockfile 安装（多架构构建下各平台原生绑定
# 必须完整记录在 lockfile 中；依赖变更后需在宿主机重新生成 lockfile）
COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set fetch-retries 5 --location=global && npm ci --no-audit --no-fund
COPY frontend/ .
RUN npm run build

# Stage 2: Build Backend and Final Image
FROM python:3.10-slim
WORKDIR /app

# 设置 APT 国内镜像源 (针对 Debian) — 清华源（阿里云源部分地区不稳定）
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

# 单包超时 30s + 重试 5 次，弱网环境下不会卡死
RUN apt-get update \
    -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 \
    && apt-get install -y --no-install-recommends \
    -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 \
    gcc \
    python3-dev \
    tzdata \
    docker.io \
    docker-compose \
    postgresql-client \
    p7zip-full \
    rsync \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# PIP 源 — 默认走内网缓存（192.168.50.12）；在其他网络构建时才需要传参覆盖：
#   --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
#   --build-arg PIP_TRUSTED_HOST=
ARG PIP_INDEX_URL=http://192.168.50.12:3141/root/pypi/+simple
ARG PIP_TRUSTED_HOST=192.168.50.12
# 设置 PIP 源，增加超时和重试以提高构建稳定性
RUN pip install --no-cache-dir \
    --default-timeout=120 \
    --retries 5 \
    -i ${PIP_INDEX_URL} \
    --trusted-host ${PIP_TRUSTED_HOST} \
    -r requirements.txt

# 复制后端代码
COPY backend/ /app/

# 复制前端编译结果到后端静态目录
COPY --from=frontend-builder /frontend/dist /app/static

EXPOSE 6565

# 确保数据目录存在
RUN mkdir -p /app/data

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "6565"]