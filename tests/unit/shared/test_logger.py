"""日志管理器单元测试"""
import pytest
import logging
from pathlib import Path
import shutil
from datetime import datetime
import tempfile


class TestLogManager:
    """日志管理器测试"""

    @pytest.fixture
    def temp_log_dir(self):
        """临时日志目录"""
        temp_dir = tempfile.mkdtemp()
        log_dir = Path(temp_dir) / "logs"
        log_dir.mkdir()
        yield log_dir
        shutil.rmtree(temp_dir)

    @pytest.mark.unit
    def test_init_creates_log_directory(self, temp_log_dir):
        """测试：初始化时应创建服务日志目录"""
        from apps.shared.logger import LogManager

        LogManager("gateway", log_dir=str(temp_log_dir))

        service_log_dir = temp_log_dir / "gateway"
        assert service_log_dir.exists()
        assert service_log_dir.is_dir()

    @pytest.mark.unit
    def test_logger_returns_valid_logger(self, temp_log_dir):
        """测试：get_logger 应返回有效的 Logger 实例"""
        from apps.shared.logger import LogManager

        manager = LogManager("orchestrator", log_dir=str(temp_log_dir))
        logger = manager.get_logger()

        assert isinstance(logger, logging.Logger)
        assert logger.name == "orchestrator"

    @pytest.mark.unit
    def test_log_file_created_on_message(self, temp_log_dir):
        """测试：写入日志时应创建日志文件"""
        from apps.shared.logger import LogManager

        manager = LogManager("gateway", log_dir=str(temp_log_dir))
        logger = manager.get_logger()

        logger.info("Test message")

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_log_dir / "gateway" / f"gateway-{today}.log"
        assert log_file.exists()

    @pytest.mark.unit
    def test_log_file_contains_message(self, temp_log_dir):
        """测试：日志文件应包含写入的消息"""
        from apps.shared.logger import LogManager

        manager = LogManager("skills", log_dir=str(temp_log_dir))
        logger = manager.get_logger()

        test_msg = "Test log message for verification"
        logger.info(test_msg)

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_log_dir / "skills" / f"skills-{today}.log"

        content = log_file.read_text(encoding='utf-8')
        assert test_msg in content
        assert "[INFO]" in content

    @pytest.mark.unit
    def test_multiple_services_separate_logs(self, temp_log_dir):
        """测试：不同服务应写入不同日志文件"""
        from apps.shared.logger import LogManager

        gateway_mgr = LogManager("gateway", log_dir=str(temp_log_dir))
        orchestrator_mgr = LogManager("orchestrator", log_dir=str(temp_log_dir))

        gateway_mgr.get_logger().info("Gateway message")
        orchestrator_mgr.get_logger().info("Orchestrator message")

        today = datetime.now().strftime("%Y-%m-%d")
        gateway_log = temp_log_dir / "gateway" / f"gateway-{today}.log"
        orchestrator_log = temp_log_dir / "orchestrator" / f"orchestrator-{today}.log"

        gateway_content = gateway_log.read_text(encoding='utf-8')
        orchestrator_content = orchestrator_log.read_text(encoding='utf-8')

        assert "Gateway message" in gateway_content
        assert "Orchestrator message" not in gateway_content

        assert "Orchestrator message" in orchestrator_content
        assert "Gateway message" not in orchestrator_content
