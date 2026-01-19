#!/bin/bash
# rshAnyGen 一键启动开发环境

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== rshAnyGen 开发环境启动 ===${NC}"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    exit 1
fi

# 检查 Docker Compose
if ! docker compose version &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    exit 1
fi

# 创建日志目录
mkdir -p logs/{gateway,orchestrator,mcp,skills,rag}

# 启动依赖服务 (Redis, Milvus)
echo -e "${YELLOW}启动依赖服务...${NC}"
docker compose -f deploy/docker/docker-compose.yml up -d redis etcd minio milvus

# 等待依赖服务就绪
echo -e "${YELLOW}等待依赖服务就绪...${NC}"
sleep 10

# 检查服务状态
echo -e "${YELLOW}检查服务状态...${NC}"
docker compose -f deploy/docker/docker-compose.yml ps redis etcd minio milvus

# 启动应用服务
echo -e "${YELLOW}启动应用服务...${NC}"
docker compose -f deploy/docker/docker-compose.yml up -d

# 等待应用服务启动
echo -e "${YELLOW}等待应用服务启动...${NC}"
sleep 5

# 显示所有服务状态
echo -e "${GREEN}=== 服务状态 ===${NC}"
docker compose -f deploy/docker/docker-compose.yml ps

echo ""
echo -e "${GREEN}=== 开发环境已启动 ===${NC}"
echo -e "Gateway:        ${GREEN}http://localhost:9301${NC}"
echo -e "Orchestrator:   ${GREEN}http://localhost:9302${NC}"
echo -e "Skills Registry: ${GREEN}http://localhost:9303${NC}"
echo -e "MCP Manager:    ${GREEN}http://localhost:9304${NC}"
echo -e "RAG Pipeline:   ${GREEN}http://localhost:9305${NC}"
echo ""
echo -e "${YELLOW}查看日志: docker compose -f deploy/docker/docker-compose.yml logs -f [service_name]${NC}"
echo -e "${YELLOW}停止环境: ./scripts/stop.sh${NC}"
