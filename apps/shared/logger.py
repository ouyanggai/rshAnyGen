"""统一日志管理器"""
import logging
import sys
from pathlib import Path
from datetime import datetime


class LogManager:
    """统一日志管理，按服务分类输出"""

    def __init__(self, service_name: str, log_dir: str = "logs"):
        self.service_name = service_name
        self.log_dir = Path(log_dir)
        self.service_log_dir = self.log_dir / service_name
        self.service_log_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.INFO)
        self._setup_handlers()

    def _setup_handlers(self):
        """配置日志处理器"""
        # 清除现有处理器
        self.logger.handlers.clear()

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # 文件输出（按日期）
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.service_log_dir / f"{self.service_name}-{today}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # 统一格式
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """获取 logger 实例"""
        return self.logger

    def close(self):
        """关闭所有日志处理器，释放资源"""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

    def __enter__(self):
        """支持上下文管理器协议"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时自动清理资源"""
        self.close()
        return False
