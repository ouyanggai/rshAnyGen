#!/usr/bin/env python3
"""
独立启动后台任务处理器
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apps.orchestrator.services.background_tasks import BackgroundTaskProcessor
from apps.shared.logger import LogManager

async def main():
    # 初始化日志
    logger = LogManager("background_tasks").get_logger()
    logger.info("启动后台任务处理器...")

    processor = BackgroundTaskProcessor()

    try:
        # 启动后台任务
        await processor.start()
    except KeyboardInterrupt:
        logger.info("收到停止信号")
    except Exception as e:
        logger.error(f"后台任务处理器异常: {e}")
        raise
    finally:
        logger.info("后台任务处理器已停止")

if __name__ == "__main__":
    asyncio.run(main())