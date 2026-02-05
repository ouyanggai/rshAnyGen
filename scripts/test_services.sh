#!/bin/bash
# 测试所有服务是否正常运行

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== 测试 rshAnyGen 服务状态 ===${NC}"

# 测试端口连通性
test_service() {
    local name="$1"
    local port="$2"
    local path="${3:-/health}"

    if curl -s "http://localhost:${port}${path}" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name (端口 $port): 正常"
        return 0
    else
        echo -e "${RED}✗${NC} $name (端口 $port): 异常"
        return 1
    fi
}

# 测试PID文件
test_process() {
    local name="$1"
    local pid_file="logs/pids/$2.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} $name: 运行中 (PID: $pid)"
            return 0
        else
            echo -e "${RED}✗${NC} $name: 未运行"
            return 1
        fi
    else
        echo -e "${YELLOW}?${NC} $name: PID文件不存在"
        return 1
    fi
}

echo ""
echo -e "${YELLOW}1. 测试 HTTP 服务...${NC}"
test_service "Gateway" 9301
test_service "Orchestrator" 9302
test_service "Skills API" 9303
test_service "RAG Pipeline" 9305
test_service "Web UI" 9300

echo ""
echo -e "${YELLOW}2. 测试后台进程...${NC}"
test_process "Background Tasks" "background_tasks"

echo ""
echo -e "${YELLOW}3. 测试 Redis 连接...${NC}"
if python3 -c "import redis; r=redis.Redis(host='192.168.1.248', port=6379); r.ping()" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Redis (192.168.1.248:6379): 正常"
else
    echo -e "${RED}✗${NC} Redis (192.168.1.248:6379): 异常"
fi

echo ""
echo -e "${YELLOW}4. 测试长期记忆功能...${NC}"
if [ -f "test_memory_final.py" ]; then
    if source venv/bin/activate && python test_memory_final.py > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} 长期记忆系统: 正常"
    else
        echo -e "${YELLOW}?${NC} 长期记忆系统: 需要进一步检查"
    fi
else
    echo -e "${YELLOW}?${NC} 长期记忆系统: 测试脚本不存在"
fi

echo ""
echo -e "${GREEN}=== 测试完成 ===${NC}"
echo ""
echo -e "${YELLOW}查看服务日志:"
echo -e "  Gateway:        tail -f logs/gateway/gateway.log"
echo -e "  Orchestrator:   tail -f logs/orchestrator/orchestrator.log"
echo -e "  Background:     tail -f logs/orchestrator/background_tasks.log"
echo -e "  Skills:        tail -f logs/skills/skills.log"
echo -e "  RAG:           tail -f logs/rag/rag.log"
echo ""