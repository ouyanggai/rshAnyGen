#!/bin/bash
# rshAnyGen 停止开发环境

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}=== 停止 rshAnyGen 开发环境 ===${NC}"

# 停止所有服务
docker compose -f deploy/docker/docker-compose.yml down

echo -e "${GREEN}=== 所有服务已停止 ===${NC}"
echo -e "${YELLOW}如需删除数据卷，运行: docker compose -f deploy/docker/docker-compose.yml down -v${NC}"
