"""配置加载器单元测试"""
import pytest
import os
import tempfile
import yaml
from pathlib import Path
from apps.shared.config_loader import ConfigLoader


class TestConfigLoader:
    """配置加载器测试"""

    @pytest.fixture
    def temp_config_dir(self):
        """临时配置目录"""
        temp_dir = tempfile.mkdtemp()
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()

        # 创建默认配置
        default_config = {
            "app": {"name": "test_app"},
            "ports": {"web_ui": 9300}
        }
        with open(config_dir / "default.yaml", "w") as f:
            yaml.dump(default_config, f)

        yield str(config_dir)

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

    @pytest.mark.unit
    def test_load_defaults(self, temp_config_dir):
        """测试：加载默认配置"""
        loader = ConfigLoader(config_dir=temp_config_dir)
        defaults = loader.load_defaults()

        assert defaults["app"]["name"] == "test_app"
        assert defaults["ports"]["web_ui"] == 9300

    @pytest.mark.unit
    def test_get_simple_value(self, temp_config_dir):
        """测试：获取简单配置值"""
        loader = ConfigLoader(config_dir=temp_config_dir)

        app_name = loader.get("app.name")
        assert app_name == "test_app"

    @pytest.mark.unit
    def test_get_nested_value(self, temp_config_dir):
        """测试：获取嵌套配置值"""
        loader = ConfigLoader(config_dir=temp_config_dir)

        port = loader.get("ports.web_ui")
        assert port == 9300

    @pytest.mark.unit
    def test_get_with_default(self, temp_config_dir):
        """测试：获取不存在的值时返回默认值"""
        loader = ConfigLoader(config_dir=temp_config_dir)

        value = loader.get("nonexistent.key", "default_value")
        assert value == "default_value"

    @pytest.mark.unit
    def test_env_var_replacement(self, temp_config_dir):
        """测试：环境变量替换"""
        loader = ConfigLoader(config_dir=temp_config_dir)

        # 设置环境变量
        os.environ["TEST_VAR"] = "test_value"

        # 先加载默认配置，然后在测试配置中使用环境变量
        loader.load_defaults()
        loader._defaults["test"] = {"key": "${TEST_VAR}"}

        value = loader.get("test.key")
        assert value == "test_value"

        # 清理
        del os.environ["TEST_VAR"]

    @pytest.mark.unit
    def test_env_var_with_default(self, temp_config_dir):
        """测试：环境变量替换带默认值"""
        loader = ConfigLoader(config_dir=temp_config_dir)

        # 环境变量不存在
        if "TEST_VAR_DEFAULT" in os.environ:
            del os.environ["TEST_VAR_DEFAULT"]

        # 先加载默认配置，然后设置测试配置
        loader.load_defaults()
        loader._defaults["test"] = {"key": "${TEST_VAR_DEFAULT:-default_value}"}

        value = loader.get("test.key")
        assert value == "default_value"
