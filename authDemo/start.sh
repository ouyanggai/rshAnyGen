#!/bin/bash

# 获取脚本所在目录
BASE_DIR=$(cd "$(dirname "$0")" && pwd)
BACKEND_DIR="$BASE_DIR/java-backend"
FRONTEND_DIR="$BASE_DIR/vue-frontend"
MAVEN_BIN="$BASE_DIR/maven/apache-maven-3.9.6/bin/mvn"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Auth Demo...${NC}"

# 1. 检查环境
if ! command -v java &> /dev/null; then
    echo -e "${RED}Error: Java is not installed or not in PATH.${NC}"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed or not in PATH.${NC}"
    exit 1
fi

# 2. 启动后端
echo -e "${GREEN}Starting Java Backend...${NC}"
cd "$BACKEND_DIR"

# 确定 Maven 命令
if [ -f "$MAVEN_BIN" ]; then
    chmod +x "$MAVEN_BIN"
    MVN_CMD="$MAVEN_BIN"
else
    if command -v mvn &> /dev/null; then
        MVN_CMD="mvn"
    else
        echo -e "${RED}Error: Maven not found.${NC}"
        exit 1
    fi
fi

# 后台运行后端
"$MVN_CMD" spring-boot:run > "$BASE_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"
echo "Logs: $BASE_DIR/backend.log"

# 3. 启动前端
echo -e "${GREEN}Starting Vue Frontend...${NC}"
cd "$FRONTEND_DIR"

echo "Installing dependencies..."
npm install > /dev/null 2>&1

echo "Starting dev server..."
npm run dev > "$BASE_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"
echo "Logs: $BASE_DIR/frontend.log"

# 4. 等待服务就绪并打开浏览器 (简单延时)
echo -e "${GREEN}Waiting for services to initialize...${NC}"
sleep 5
echo -e "${GREEN}Opening browser...${NC}"
open "http://192.168.1.212:5174" 2>/dev/null || xdg-open "http://192.168.1.212:5174" 2>/dev/null || echo "Please open http://192.168.1.212:5174 manually"

# 5. 优雅退出
cleanup() {
    echo -e "${GREEN}Stopping services...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}Services are running. Press Ctrl+C to stop.${NC}"
wait
