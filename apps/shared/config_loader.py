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
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).resolve().parents[2] / ".env"
            load_dotenv(env_path)
        except Exception:
            pass

    def load_defaults(self) -> Dict[str, Any]:
        """加载默认配置"""
        if self._defaults is None:
            default_path = self.config_dir / "default.yaml"
            if not default_path.exists():
                raise FileNotFoundError(f"Default config not found: {default_path}")

            with open(default_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                self._defaults = self._resolve_recursive(data)
        return self._defaults

    def load_config(self, name: str) -> Dict[str, Any]:
        """加载指定配置文件"""
        if name not in self._configs:
            config_path = self.config_dir / f"{name}.yaml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    self._configs[name] = self._resolve_recursive(data)
            else:
                self._configs[name] = {}
        return self._configs[name]

    def _resolve_recursive(self, data: Any) -> Any:
        """递归解析配置中的环境变量"""
        if isinstance(data, dict):
            return {k: self._resolve_recursive(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_recursive(item) for item in data]
        elif isinstance(data, str) and data.startswith("${"):
            return self._resolve_env_var(data)
        return data

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
        """
        解析环境变量，支持默认值 ${VAR:-default}

        优先使用环境变量，如果环境变量不存在或为空，则使用默认值
        """
        match = re.match(r'\$\{([^}:]+)(?::-([^}]*))?\}', value)
        if match:
            var_name, default_val = match.groups()
            env_val = os.getenv(var_name)
            # 如果环境变量不存在，或提供了默认值且环境变量为空字符串
            if env_val is None:
                return default_val or ''
            if env_val == '' and default_val is not None:
                return default_val
            return env_val
        return os.getenv(value[2:-1], '')
