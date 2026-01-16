#!/bin/bash
# 一键安装依赖

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}安装项目依赖...${NC}"

# Python 依赖
echo -e "${YELLOW}安装 Python 依赖...${NC}"
pip install -r requirements-shared.txt

echo -e "${GREEN}✓ 依赖安装完成${NC}"
