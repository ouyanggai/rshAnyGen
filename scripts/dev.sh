#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== rshAnyGen 本地开发环境启动（Python + Node）===${NC}"

mkdir -p logs/{gateway,orchestrator,skills,rag,webui} logs/pids

get_port() {
  local key="$1"
  awk -v k="$key:" '
    $1=="ports:" {in_ports=1; next}
    in_ports && $1==k {print $2; exit}
    in_ports && NF==0 {in_ports=0}
  ' config/default.yaml
}
PORT_WEBUI=$(get_port web_ui)
PORT_GATEWAY=$(get_port gateway)
PORT_ORCH=$(get_port orchestrator)
PORT_SKILLS=$(get_port skills_registry)
PORT_RAG=$(get_port rag_pipeline)

if [[ -z "$PORT_WEBUI" || -z "$PORT_GATEWAY" || -z "$PORT_ORCH" || -z "$PORT_SKILLS" || -z "$PORT_RAG" ]]; then
  echo -e "${RED}错误: 无法从 config/default.yaml 读取端口${NC}"
  exit 1
fi

free_port() {
  local port="$1"
  local pids
  pids=$(lsof -ti tcp:"$port" || true)
  if [[ -n "$pids" ]]; then
    echo -e "${YELLOW}端口 $port 已被占用，正在释放...${NC}"
    echo "$pids" | xargs kill -9 || true
    sleep 0.5
  fi
}

if [[ ! -d "venv" ]]; then
  echo -e "${YELLOW}创建并安装 Python 依赖...${NC}"
  bash scripts/install.sh
else
  source venv/bin/activate
fi

start_python_module() {
  local name="$1"
  local module="$2"
  local port="$3"
  local log="logs/${name}/${name}.log"
  free_port "$port"
  echo -e "${YELLOW}启动 ${name} (${module})，端口 ${port}...${NC}"
  bash -c "source venv/bin/activate && PYTHONPATH=. python -m ${module}" &
  local pid=$!
  echo "$pid" > "logs/pids/${name}.pid"
  echo -e "${GREEN}${name} 启动完成 (PID: $pid)，日志: $log${NC}"
}

start_uvicorn_app() {
  local name="$1"
  local app_ref="$2"
  local port="$3"
  local log="logs/${name}/${name}.log"
  free_port "$port"
  echo -e "${YELLOW}启动 ${name} (uvicorn ${app_ref})，端口 ${port}...${NC}"
  bash -c "source venv/bin/activate && PYTHONPATH=. uvicorn ${app_ref} --host 0.0.0.0 --port ${port}" &
  local pid=$!
  echo "$pid" > "logs/pids/${name}.pid"
  echo -e "${GREEN}${name} 启动完成 (PID: $pid)，日志: $log${NC}"
}

start_web_ui() {
  local port="$1"
  local log="logs/webui/webui.log"
  free_port "$port"
  echo -e "${YELLOW}启动 Web UI (SvelteKit Vite)，端口 ${port}...${NC}"
  pushd apps/web-ui > /dev/null
  if [[ ! -d "node_modules" ]]; then
    npm install --legacy-peer-deps
  fi
  BACKEND_GATEWAY="http://localhost:${PORT_GATEWAY}" \
  BACKEND_ORCHESTRATOR="http://localhost:${PORT_ORCH}" \
  npm run dev -- --port "${port}" --host &
  local pid=$!
  echo "$pid" > "${PROJECT_ROOT}/logs/pids/webui.pid"
  popd > /dev/null
  echo -e "${GREEN}Web UI 启动完成 (PID: $pid)，日志: $log${NC}"
}

echo -e "${YELLOW}启动后端服务...${NC}"
start_python_module "gateway" "apps.gateway.main" "$PORT_GATEWAY"
start_python_module "orchestrator" "apps.orchestrator.main" "$PORT_ORCH"
start_uvicorn_app "skills" "services.skills_registry.api.main:app" "$PORT_SKILLS"
start_uvicorn_app "rag" "services.rag_pipeline.server:app" "$PORT_RAG"

echo -e "${YELLOW}启动前端 Web UI...${NC}"
start_web_ui "$PORT_WEBUI"

echo ""
echo -e "${GREEN}=== 服务已启动（本地开发）===${NC}"
echo -e "Web UI:        ${GREEN}http://localhost:${PORT_WEBUI}${NC}"
echo -e "Gateway:       ${GREEN}http://localhost:${PORT_GATEWAY}${NC}   [健康检查: /health]"
echo -e "Orchestrator:  ${GREEN}http://localhost:${PORT_ORCH}${NC}      [健康检查: /health]"
echo -e "Skills API:    ${GREEN}http://localhost:${PORT_SKILLS}${NC}    [健康检查: /api/v1/health]"
echo -e "RAG Pipeline:  ${GREEN}http://localhost:${PORT_RAG}${NC}       [健康检查: /api/v1/health]"
echo ""
echo -e "${YELLOW}日志路径: logs/<service>/*.log${NC}"
echo -e "${YELLOW}PID 文件: logs/pids/<service>.pid${NC}"
echo -e "${YELLOW}生产环境脚本: ./scripts/prod.sh${NC}"
wait
