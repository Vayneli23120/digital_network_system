# Makefile — 混合部署编排（物理机后端 + Docker 采集器）
#
# 背景：Prometheus + snmp_exporter 跑在 Docker；后端/数据库/发现服务跑在物理机。
# 用法：在 Ubuntu 部署机的仓库根目录执行 make <目标>，例如 `make deploy`。
#
# 这个文件把跨边界的“部署顺序 + 权限 + 健康检查”固化下来，避免每次靠记忆。

SHELL := /bin/bash
COMPOSE_DIR := docker
TARGETS_DIR := docker/prometheus/targets
BACKEND_PORT := 8000

.PHONY: help deploy up down restart-backend targets-perms health logs

help:
	@echo "可用命令："
	@echo "  make deploy          一键按序部署：修权限 → 起容器 → 重启后端 → 健康检查"
	@echo "  make up              启动 Prometheus + snmp_exporter 容器"
	@echo "  make down            停止采集容器"
	@echo "  make restart-backend 重启物理机后端（uvicorn，会加载 .env）"
	@echo "  make targets-perms   修复目标文件目录属主，确保后端可写"
	@echo "  make health          检查后端 /ready、采集诊断、Prometheus targets"
	@echo "  make logs            查看容器与后端日志"

# 正确顺序：先修权限（否则后端可能写不了目标文件）→ 起容器 → 重启后端 → 验证
deploy: targets-perms up restart-backend health

up:
	cd $(COMPOSE_DIR) && docker compose up -d

down:
	cd $(COMPOSE_DIR) && docker compose down

restart-backend:
	./scripts/restart-backend.sh

# 让物理机后端运行用户可写 Prometheus 目标文件目录。
# Docker 常以 root 建目录导致后端写失败；此目标重复执行安全（幂等）。
targets-perms:
	mkdir -p $(TARGETS_DIR)
	chown -R $$(id -u):$$(id -g) $(TARGETS_DIR)

health:
	@echo "== 后端 /ready =="
	@curl -sf http://localhost:$(BACKEND_PORT)/ready && echo "" || echo "后端未就绪（503/不可达）"
	@echo "== 采集诊断 /api/system/diagnostics =="
	@curl -sf http://localhost:$(BACKEND_PORT)/api/system/diagnostics && echo "" || echo "诊断接口不可用"
	@echo "== Prometheus targets =="
	@curl -sf http://localhost:9090/api/v1/targets | head -c 400 && echo "" || echo "Prometheus 不可达"

logs:
	@echo "== netprom (Prometheus) =="
	@cd $(COMPOSE_DIR) && docker compose logs --tail=30 prometheus || true
	@echo "== netsnmp (snmp_exporter) =="
	@cd $(COMPOSE_DIR) && docker compose logs --tail=30 snmp_exporter || true
	@echo "== backend (uvicorn) =="
	@tail -n 30 logs/uvicorn.log 2>/dev/null || echo "无 uvicorn 日志"
