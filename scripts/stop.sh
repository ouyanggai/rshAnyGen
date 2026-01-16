#!/bin/bash
# 停止所有服务

echo "停止服务..."

# 停止后端
for pid_file in logs/*/.*.pid; do
    if [ -f "$pid_file" ]; then
        kill $(cat "$pid_file") 2>/dev/null
        rm "$pid_file"
    fi
done

# 停止 Redis
if pgrep -x "redis-server" > /dev/null; then
    redis-cli shutdown
fi

echo "所有服务已停止"
