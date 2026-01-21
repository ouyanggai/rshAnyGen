#!/bin/bash
# rshAnyGen 停止开发环境

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}=== 停止 rshAnyGen 开发环境 ===${NC}"

# 停止 PID 文件记录的进程
if [ -d "logs/pids" ]; then
    echo -e "${YELLOW}停止 Python/Node 进程...${NC}"
    for pid_file in logs/pids/*.pid; do
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            service_name=$(basename "$pid_file" .pid)
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 "$pid"
                echo -e "已停止 $service_name (PID: $pid)"
            else
                echo -e "$service_name (PID: $pid) 已不在运行"
            fi
            rm "$pid_file"
        fi
    done
fi

# 备用：按端口停止
echo -e "${YELLOW}检查残留端口占用...${NC}"
for port in 6333 9300 9301 9302 9303 9305; do
    pids=$(lsof -ti tcp:"$port" || true)
    if [[ -n "$pids" ]]; then
        echo -e "释放端口 $port (PIDs: $pids)"
        echo "$pids" | xargs kill -9 || true
    fi
done

echo -e "${GREEN}=== 所有服务已停止 ===${NC}"
echo -e "${YELLOW}如需删除数据卷，运行: docker compose -f deploy/docker/docker-compose.yml down -v${NC}"
