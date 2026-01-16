#!/bin/bash
# 模块化测试运行脚本

MODULE=${1:-shared}
TYPE=${2:-unit}

case $MODULE in
    shared)
        pytest "tests/unit/shared/" -v -m $TYPE
        ;;
    all)
        pytest tests/ -v
        ;;
    *)
        echo "用法: ./scripts/test.sh [shared|all] [unit|integration|e2e]"
        exit 1
        ;;
esac
