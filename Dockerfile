# ============================================
# Network Automation System - Backend
# Multi-stage production build
# ============================================

# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies for building Python packages
# 使用阿里云 Debian 镜像加速 apt
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# 使用阿里云 PyPI 镜像加速 pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com

# Install LLM 依赖（litellm，供「通用 LLM 服务配置」直连各提供商 / LM Studio / Ollama 等）
# 说明：requirements-ai.txt 里 google-adk 与 langchain 对 tenacity 的版本要求互斥
# （>=9 与 <9），整文件无法一起安装；此处只安装 LLM 配置所必需的 litellm。
RUN pip install --no-cache-dir litellm==1.60.0 \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com

# Copy application source
COPY . .

# Create required directories
RUN mkdir -p backups logs data assets

# --- Stage 2: Production ---
FROM python:3.12-slim AS production

WORKDIR /app

# Install runtime dependencies only
# iputils-ping：设备可达性监控依赖的 ping 命令
# 使用阿里云 Debian 镜像加速 apt
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

# Copy Python packages and application from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Set ownership
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
