#!/bin/bash
# rshAnyGen 测试运行脚本

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo -e "${GREEN}=== rshAnyGen 测试 ===${NC}"

# 解析参数
TEST_PATH=""
COVERAGE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--path)
            TEST_PATH="$2"
            shift 2
            ;;
        -c|--coverage)
            COVERAGE="--cov=apps --cov=services --cov-report=html --cov-report=term"
            shift
            ;;
        -h|--help)
            echo "用法: ./scripts/test.sh [选项]"
            echo ""
            echo "选项:"
            echo "  -p, --path PATH    测试路径 (默认: tests/)"
            echo "  -c, --coverage     生成覆盖率报告"
            echo "  -h, --help         显示帮助"
            echo ""
            echo "示例:"
            echo "  ./scripts/test.sh                    # 运行所有测试"
            echo "  ./scripts/test.sh -p tests/unit/     # 运行单元测试"
            echo "  ./scripts/test.sh -p tests/unit/gateway/ -c  # 运行 gateway 测试并生成覆盖率"
            exit 0
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            echo "使用 -h 查看帮助"
            exit 1
            ;;
    esac
done

# 默认测试路径
if [ -z "$TEST_PATH" ]; then
    TEST_PATH="tests/"
fi

echo -e "${YELLOW}运行测试: $TEST_PATH${NC}"

# 运行测试
if [ -z "$COVERAGE" ]; then
    pytest "$TEST_PATH" -v --tb=short
else
    pytest "$TEST_PATH" -v --tb=short $COVERAGE
    echo -e "${GREEN}覆盖率报告已生成: htmlcov/index.html${NC}"
fi

echo -e "${GREEN}=== 测试完成 ===${NC}"
