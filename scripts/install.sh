#!/bin/bash
# rshAnyGen 安装所有依赖

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== rshAnyGen 依赖安装 ===${NC}"

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo -e "${YELLOW}警告: Python 版本过低 ($PYTHON_VERSION)，建议使用 Python 3.10+${NC}"
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv venv
fi

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source venv/bin/activate

# 升级 pip
echo -e "${YELLOW}升级 pip...${NC}"
pip install --upgrade pip

# 安装共享依赖
echo -e "${YELLOW}安装共享依赖...${NC}"
pip install -r requirements-shared.txt

# 安装各服务依赖
echo -e "${YELLOW}安装 Gateway 依赖...${NC}"
pip install -r apps/gateway/requirements.txt

echo -e "${YELLOW}安装 Orchestrator 依赖...${NC}"
pip install -r apps/orchestrator/requirements.txt

echo -e "${YELLOW}安装 Skills Registry 依赖...${NC}"
if [ -f "services/skills_registry/requirements.txt" ]; then
    pip install -r services/skills_registry/requirements.txt
fi

echo -e "${YELLOW}安装 MCP Manager 依赖...${NC}"
if [ -f "services/mcp_manager/requirements.txt" ]; then
    pip install -r services/mcp_manager/requirements.txt
fi

echo -e "${YELLOW}安装 RAG Pipeline 依赖...${NC}"
if [ -f "services/rag_pipeline/requirements.txt" ]; then
    pip install -r services/rag_pipeline/requirements.txt
fi

echo -e "${GREEN}=== 依赖安装完成 ===${NC}"
echo -e "${YELLOW}激活虚拟环境: source venv/bin/activate${NC}"
