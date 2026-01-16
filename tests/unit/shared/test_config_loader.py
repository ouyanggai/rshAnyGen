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

    @pytest.mark.unit
    def test_load_config(self, temp_config_dir):
        """测试：加载指定配置文件"""
        test_config = {
            "test_key": "test_value",
            "nested": {"key": "value"}
        }
        config_file = Path(temp_config_dir) / "test.yaml"
        with open(config_file, "w") as f:
            yaml.dump(test_config, f)

        loader = ConfigLoader(config_dir=temp_config_dir)
        config = loader.load_config("test")

        assert isinstance(config, dict)
        assert config["test_key"] == "test_value"
        assert config["nested"]["key"] == "value"

    @pytest.mark.unit
    def test_load_config_nonexistent(self, temp_config_dir):
        """测试：加载不存在的配置文件应返回空字典"""
        loader = ConfigLoader(config_dir=temp_config_dir)
        config = loader.load_config("nonexistent")

        assert isinstance(config, dict)
        assert len(config) == 0

    @pytest.mark.unit
    def test_load_config_caching(self, temp_config_dir):
        """测试：配置加载应被缓存"""
        test_config = {"key": "value"}
        config_file = Path(temp_config_dir) / "cache_test.yaml"
        with open(config_file, "w") as f:
            yaml.dump(test_config, f)

        loader = ConfigLoader(config_dir=temp_config_dir)

        # 第一次加载
        config1 = loader.load_config("cache_test")
        # 第二次加载（应从缓存获取）
        config2 = loader.load_config("cache_test")

        assert config1 is config2  # 应该是同一个对象（缓存）

    @pytest.mark.unit
    def test_env_var_empty_with_default(self, temp_config_dir):
        """测试：环境变量为空字符串且有默认值时应使用默认值"""
        loader = ConfigLoader(config_dir=temp_config_dir)

        # 设置环境变量为空字符串
        os.environ["TEST_EMPTY"] = ""

        loader.load_defaults()
        loader._defaults["test"] = {"key": "${TEST_EMPTY:-default_value}"}

        value = loader.get("test.key")
        # 应该返回默认值，因为环境变量为空
        assert value == "default_value"

        # 清理
        del os.environ["TEST_EMPTY"]

    @pytest.mark.unit
    def test_env_var_empty_without_default(self, temp_config_dir):
        """测试：环境变量为空字符串且无默认值时应返回空字符串"""
        loader = ConfigLoader(config_dir=temp_config_dir)

        os.environ["TEST_EMPTY"] = ""
        loader.load_defaults()
        loader._defaults["test"] = {"key": "${TEST_EMPTY}"}

        value = loader.get("test.key")
        assert value == ""

        del os.environ["TEST_EMPTY"]
