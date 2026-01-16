"""pytest 配置和共享 fixtures"""
import sys
from pathlib import Path

import pytest
import tempfile
import shutil

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def test_config_dir():
    """测试配置目录"""
    config_dir = Path(__file__).parent / "fixtures"
    config_dir.mkdir(exist_ok=True)
    yield str(config_dir)


@pytest.fixture
def temp_log_dir(tmp_path):
    """临时日志目录"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    yield str(log_dir)
    shutil.rmtree(str(log_dir))


@pytest.fixture
def mock_llm_response():
    """模拟 LLM 响应"""
    return {
        "choices": [{
            "message": {"content": "测试响应内容"}
        }],
        "usage": {"total_tokens": 100}
    }
