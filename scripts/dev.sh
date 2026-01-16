#!/bin/bash
# 一键启动开发环境

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  rshAnyGen 开发环境启动${NC}"
echo -e "${GREEN}=========================================${NC}"

# 检查依赖
check_dependencies() {
    echo -e "${YELLOW}检查依赖...${NC}"

    command -v python3 >/dev/null 2>&1 || { echo -e "${RED}错误: 未安装 Python3${NC}"; exit 1; }
    command -v node >/dev/null 2>&1 || { echo -e "${RED}错误: 未安装 Node.js${NC}"; exit 1; }

    echo -e "${GREEN}✓ 依赖检查通过${NC}"
}

# 创建日志目录
setup_logs() {
    mkdir -p logs/{gateway,orchestrator,mcp,skills,rag}
    echo -e "${GREEN}✓ 日志目录已创建${NC}"
}

# 启动 Redis
start_redis() {
    if ! pgrep -x "redis-server" > /dev/null; then
        redis-server --daemonize yes --port 6379
        echo -e "${GREEN}✓ Redis 已启动${NC}"
    else
        echo -e "${GREEN}✓ Redis 已在运行${NC}"
    fi
}

# 主流程
main() {
    check_dependencies
    setup_logs
    start_redis

    echo ""
    echo -e "${GREEN}开发环境准备完成！${NC}"
    echo -e "请手动启动各服务："
    echo -e "  - Gateway:     cd apps/gateway && python main.py"
    echo -e "  - Orchestrator: cd apps/orchestrator && python main.py"
}

main
