# ============================================
# Network Automation System - Frontend
# ============================================

FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including dev for build)
RUN npm install

# Copy source
COPY . .

# Build for production
RUN npm run build

# ============================================
# Stage 2: Production runner
# ============================================
FROM node:20-alpine AS production

WORKDIR /app

# Install serve to serve the static build
RUN npm install -g serve

# Copy built assets from builder
COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
