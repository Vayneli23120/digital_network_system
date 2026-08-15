# ============================================
# Network Automation System - Frontend
# 构建 Vue 产物并用 nginx 托管 + 反代 /api /ws /photos
# ============================================

FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including dev for build)
# 使用 npmmirror 镜像加速 npm
RUN npm install --no-audit --no-fund --registry=https://registry.npmmirror.com

# Copy source
COPY . .

# Build for production（VITE_API_BASE_URL 默认 /api，由 nginx 反代）
RUN npm run build

# ============================================
# Stage 2: nginx
# ============================================
FROM nginx:1.27-alpine AS production

# 覆盖默认站点配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
