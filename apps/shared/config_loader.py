"""统一配置加载器"""
import yaml
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigLoader:
    """统一配置加载器，支持默认值 + 环境变量覆盖"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._defaults: Optional[Dict[str, Any]] = None
        self._configs: Dict[str, Dict[str, Any]] = {}

    def load_defaults(self) -> Dict[str, Any]:
        """加载默认配置"""
        if self._defaults is None:
            default_path = self.config_dir / "default.yaml"
            if not default_path.exists():
                raise FileNotFoundError(f"Default config not found: {default_path}")

            with open(default_path, 'r', encoding='utf-8') as f:
                self._defaults = yaml.safe_load(f) or {}
        return self._defaults

    def load_config(self, name: str) -> Dict[str, Any]:
        """加载指定配置文件"""
        if name not in self._configs:
            config_path = self.config_dir / f"{name}.yaml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._configs[name] = yaml.safe_load(f) or {}
            else:
                self._configs[name] = {}
        return self._configs[name]

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值，支持点分隔路径

        支持环境变量替换：
        - ${VAR_NAME} - 必须的环境变量
        - ${VAR_NAME:-default} - 带默认值
        """
        keys = key_path.split('.')
        value = self.load_defaults()

        # 遍历路径获取值
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default

        # 环境变量替换
        if isinstance(value, str) and value.startswith("${"):
            return self._resolve_env_var(value)

        return value if value is not None else default

    def _resolve_env_var(self, value: str) -> str:
        """解析环境变量，支持默认值 ${VAR:-default}"""
        match = re.match(r'\$\{([^}:]+)(?::-([^}]*))?\}', value)
        if match:
            var_name, default_val = match.groups()
            return os.getenv(var_name, default_val or '')
        return os.getenv(value[2:-1], '')
