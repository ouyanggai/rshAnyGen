# rshAnyGen 开源 Agent 系统 - 实施计划（第一阶段）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 构建模块化的、支持 MCP/Skills/联网搜索的中文 Agent 系统的基础设施和共享模块

**架构：** 基于 FastAPI + LangGraph + Vue3，使用在线 LLM API，支持多提供商配置

**技术栈：** Python 3.10+, FastAPI, LangGraph, Vue3, Tailwind, Redis, Milvus

---

## 第一阶段：基础设施和共享模块

本阶段建立项目基础结构、配置系统、日志管理和测试框架。

---

### Task 1: 创建项目基础目录结构

**目标：** 创建完整的项目目录结构

**Step 1: 创建目录结构**

```bash
# 创建主目录
mkdir -p apps/shared apps/gateway apps/orchestrator apps/web-ui
mkdir -p services/mcp-baidu-search services/mcp-knowledge services/mcp-manager
mkdir -p services/skills-registry services/rag-pipeline
mkdir -p config scripts logs tests/{unit,integration,e2e,fixtures}
mkdir -p deploy/{docker,k8s} docs/plans

# 创建日志子目录
mkdir -p logs/{gateway,orchestrator,mcp,skills,rag}

# 创建测试子目录
mkdir -p tests/unit/{shared,gateway,orchestrator,mcp,skills,rag}
mkdir -p tests/integration/{agent,rag}
mkdir -p tests/e2e/{chat,search}

# 验证结构
tree -L 2 -I '__pycache__|node_modules'
```

**预期输出：** 完整的目录树结构

**Step 2: 创建 .gitignore 文件**

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Logs
logs/
*.log

# Environment
.env
.env.local

# Node
node_modules/
apps/web-ui/dist/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Database
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db
EOF
```

**Step 3: 初始化 Git 仓库**

```bash
git init
git add .gitignore
git commit -m "chore: initialize git repository with .gitignore"
```

---

### Task 2: 创建共享配置文件

**目标：** 创建所有默认配置文件

**Files:**
- Create: `config/default.yaml`
- Create: `config/llm.yaml`
- Create: `config/vector_db.yaml`
- Create: `config/embedding.yaml`
- Create: `config/mcp.yaml`
- Create: `config/rag.yaml`

**Step 1: 创建默认配置文件**

```bash
cat > config/default.yaml << 'EOF'
# rshAnyGen 默认配置
app:
  name: "rshAnyGen"
  version: "0.1.0"
  environment: "development"
  log_level: "INFO"

# 服务端口（9300+ 专属段）
ports:
  web_ui: 9300
  gateway: 9301
  orchestrator: 9302
  skills_registry: 9303
  mcp_manager: 9304
  rag_pipeline: 9305

# 外部依赖端口
dependencies:
  redis:
    host: "localhost"
    port: 6379
    db: 0
    ttl: 3600
  milvus:
    host: "localhost"
    port: 19530
  qdrant:
    host: "localhost"
    port: 6333

# LLM 默认配置
llm:
  provider: "qwen"
  model: "qwen-max"
  temperature: 0.7
  max_tokens: 2000
  timeout: 30

# 向量数据库默认配置
vector_db:
  provider: "milvus"
  host: "localhost"
  port: 19530
  collection: "knowledge_base"
  dimension: 1024
  index_type: "HNSW"
  metric_type: "COSINE"

# 嵌入服务默认配置
embedding:
  provider: "qwen"
  model: "text-embedding-v3"
  batch_size: 32
  dimension: 1024

# 重排服务默认配置
reranker:
  provider: "qwen"
  model: "rerank-v2"
  top_n: 5
EOF
```

**Step 2: 创建 LLM 配置文件**

```bash
cat > config/llm.yaml << 'EOF'
# LLM 提供商配置
providers:
  qwen:
    api_key: "${QWEN_API_KEY}"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    models:
      - "qwen-max"
      - "qwen-plus"
      - "qwen-turbo"

  zhipu:
    api_key: "${ZHIPU_API_KEY}"
    base_url: "https://open.bigmodel.cn/api/paas/v4"
    models:
      - "glm-4-plus"
      - "glm-4"

  kimi:
    api_key: "${KIMI_API_KEY}"
    base_url: "https://api.moonshot.cn/v1"
    models:
      - "moonshot-v1-128k"

  openai:
    api_key: "${OPENAI_API_KEY}"
    base_url: "https://api.openai.com/v1"
    models:
      - "gpt-4o"
      - "gpt-4o-mini"

# 当前使用的提供商
active: "qwen"
EOF
```

**Step 3: 提交配置文件**

```bash
git add config/
git commit -m "chore: add default configuration files"
```

---

### Task 3: 实现配置加载器（带测试）

**目标：** 实现统一的配置加载器，支持环境变量替换

**Files:**
- Create: `apps/shared/config_loader.py`
- Create: `tests/unit/shared/test_config_loader.py`

**Step 1: 编写配置加载器的测试**

```bash
cat > tests/unit/shared/test_config_loader.py << 'EOF'
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

        # 在测试配置中使用环境变量
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

        loader._defaults["test"] = {"key": "${TEST_VAR_DEFAULT:-default_value}"}

        value = loader.get("test.key")
        assert value == "default_value"
EOF
```

**Step 2: 运行测试（预期失败）**

```bash
cd /Volumes/oygsky/AIstudy/rshAnyGen
pytest tests/unit/shared/test_config_loader.py -v
```

**预期输出：** FAIL - ModuleNotFoundError: No module named 'apps.shared.config_loader'

**Step 3: 实现配置加载器**

```bash
cat > apps/shared/config_loader.py << 'EOF'
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
EOF
```

**Step 4: 创建 apps/shared/__init__.py**

```bash
cat > apps/shared/__init__.py << 'EOF'
"""共享模块"""
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

__all__ = ["ConfigLoader", "LogManager"]
EOF
```

**Step 5: 创建 apps/__init__.py**

```bash
cat > apps/__init__.py << 'EOF'
"""应用模块"""
EOF
```

**Step 6: 运行测试（预期通过）**

```bash
pytest tests/unit/shared/test_config_loader.py -v
```

**预期输出：** PASS (6 passed)

**Step 7: 提交**

```bash
git add apps/shared/ tests/unit/shared/test_config_loader.py
git commit -m "feat: implement config loader with tests"
```

---

### Task 4: 实现日志管理器（带测试）

**目标：** 实现统一的日志管理器，按服务分类输出

**Files:**
- Create: `apps/shared/logger.py`
- Create: `tests/unit/shared/test_logger.py`

**Step 1: 编写日志管理器的测试**

```bash
cat > tests/unit/shared/test_logger.py << 'EOF'
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
EOF
```

**Step 2: 运行测试（预期失败）**

```bash
pytest tests/unit/shared/test_logger.py -v
```

**预期输出：** FAIL - ModuleNotFoundError: No module named 'apps.shared.logger'

**Step 3: 实现日志管理器**

```bash
cat > apps/shared/logger.py << 'EOF'
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
EOF
```

**Step 4: 运行测试（预期通过）**

```bash
pytest tests/unit/shared/test_logger.py -v
```

**预期输出：** PASS (5 passed)

**Step 5: 提交**

```bash
git add apps/shared/logger.py tests/unit/shared/test_logger.py
git commit -m "feat: implement log manager with tests"
```

---

### Task 5: 设置 pytest 配置

**目标：** 配置 pytest 测试框架

**Files:**
- Create: `tests/pytest.ini`
- Create: `tests/conftest.py`

**Step 1: 创建 pytest.ini**

```bash
cat > tests/pytest.ini << 'EOF'
[pytest]
# 测试发现
testpaths = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 输出
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=apps
    --cov=services
    --cov-report=term-missing
    --cov-report=html:htmlcov

# 标记
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: E2E 测试
    slow: 慢速测试
    external: 需要外部依赖
EOF
```

**Step 2: 创建 conftest.py**

```bash
cat > tests/conftest.py << 'EOF'
"""pytest 配置和共享 fixtures"""
import pytest
import tempfile
import shutil
from pathlib import Path


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
EOF
```

**Step 3: 创建测试 fixtures**

```bash
mkdir -p tests/fixtures/configs
cat > tests/fixtures/configs/test_config.yaml << 'EOF'
# 测试配置
app:
  name: "test_app"
  version: "1.0.0"

ports:
  test_service: 9999
EOF
```

**Step 4: 运行所有测试**

```bash
pytest tests/unit/shared/ -v
```

**预期输出：** PASS (11 passed)

**Step 5: 提交**

```bash
git add tests/
git commit -m "chore: setup pytest configuration"
```

---

### Task 6: 创建依赖文件

**目标：** 创建所有 Python 依赖文件

**Files:**
- Create: `requirements-shared.txt`
- Create: `apps/gateway/requirements.txt`
- Create: `apps/orchestrator/requirements.txt`

**Step 1: 创建共享依赖**

```bash
cat > requirements-shared.txt << 'EOF'
# 核心框架
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# 配置管理
pyyaml>=6.0.1
python-dotenv>=1.0.0

# 日志
loguru>=0.7.2

# 数据库
redis>=5.0.1
pymilvus>=2.3.0
qdrant-client>=1.7.0

# HTTP 客户端
httpx>=0.26.0
aiohttp>=3.9.0

# 测试
pytest>=7.4.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0

# 工具
python-multipart>=0.0.6
websockets>=12.0
EOF
```

**Step 2: 创建 Gateway 依赖**

```bash
cat > apps/gateway/requirements.txt << 'EOF'
-r ../../requirements-shared.txt

# Gateway 特定
fastapi-limiter>=0.1.6
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
EOF
```

**Step 3: 创建 Orchestrator 依赖**

```bash
cat > apps/orchestrator/requirements.txt << 'EOF'
-r ../../requirements-shared.txt

# LangGraph / LangChain
langgraph>=0.0.20
langchain>=0.1.0
langchain-openai>=0.0.2

# LLM 客户端
dashscope>=1.14.0
zhipuai>=1.0.0
openai>=1.10.0
EOF
```

**Step 4: 提交**

```bash
git add requirements*.txt apps/*/requirements.txt
git commit -m "chore: add dependency files"
```

---

### Task 7: 创建开发脚本

**目标：** 创建开发启动脚本

**Files:**
- Create: `scripts/dev.sh`
- Create: `scripts/stop.sh`
- Create: `scripts/install.sh`
- Create: `scripts/test.sh`

**Step 1: 创建 dev.sh**

```bash
cat > scripts/dev.sh << 'EOF'
#!/bin/bash
# 一键启动开发环境

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  rshAnyGen 开发环境启动${NC}"
echo -e "${GREEN}=========================================${NC}"

# 检查依赖
check_dependencies() {
    echo -e "${YELLOW}检查依赖...${NC}"

    command -v python3 >/dev/null 2>&1 || { echo -e "${RED}错误: 未安装 Python3${NC}"; exit 1; }
    command -v node >/dev/null 2>&1 || { echo -e "${RED}错误: 未安装 Node.js${NC}"; exit 1; }

    echo -e "${GREEN}✓ 依赖检查通过${NC}"
}

# 创建日志目录
setup_logs() {
    mkdir -p logs/{gateway,orchestrator,mcp,skills,rag}
    echo -e "${GREEN}✓ 日志目录已创建${NC}"
}

# 启动 Redis
start_redis() {
    if ! pgrep -x "redis-server" > /dev/null; then
        redis-server --daemonize yes --port 6379
        echo -e "${GREEN}✓ Redis 已启动${NC}"
    else
        echo -e "${GREEN}✓ Redis 已在运行${NC}"
    fi
}

# 主流程
main() {
    check_dependencies
    setup_logs
    start_redis

    echo ""
    echo -e "${GREEN}开发环境准备完成！${NC}"
    echo -e "请手动启动各服务："
    echo -e "  - Gateway:     cd apps/gateway && python main.py"
    echo -e "  - Orchestrator: cd apps/orchestrator && python main.py"
}

main
EOF

chmod +x scripts/dev.sh
```

**Step 2: 创建 stop.sh**

```bash
cat > scripts/stop.sh << 'EOF'
#!/bin/bash
# 停止所有服务

echo "停止服务..."

# 停止后端
for pid_file in logs/*/.*.pid; do
    if [ -f "$pid_file" ]; then
        kill $(cat "$pid_file") 2>/dev/null
        rm "$pid_file"
    fi
done

# 停止 Redis
if pgrep -x "redis-server" > /dev/null; then
    redis-cli shutdown
fi

echo "所有服务已停止"
EOF

chmod +x scripts/stop.sh
```

**Step 3: 创建 install.sh**

```bash
cat > scripts/install.sh << 'EOF'
#!/bin/bash
# 一键安装依赖

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}安装项目依赖...${NC}"

# Python 依赖
echo -e "${YELLOW}安装 Python 依赖...${NC}"
pip install -r requirements-shared.txt

echo -e "${GREEN}✓ 依赖安装完成${NC}"
EOF

chmod +x scripts/install.sh
```

**Step 4: 创建 test.sh**

```bash
cat > scripts/test.sh << 'EOF'
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
EOF

chmod +x scripts/test.sh
```

**Step 5: 提交**

```bash
git add scripts/
git commit -m "chore: add development scripts"
```

---

## 第一阶段完成检查清单

- [x] 项目目录结构创建
- [x] 配置文件创建（default.yaml, llm.yaml 等）
- [x] 配置加载器实现（带测试）
- [x] 日志管理器实现（带测试）
- [x] pytest 配置完成
- [x] 依赖文件创建
- [x] 开发脚本创建

---

## 下一步

第一阶段完成后，继续实施：

**第二阶段：API 网关**
- FastAPI 服务设置
- 聊天接口实现
- 会话管理中间件
- Skills 管理 API

**第三阶段：Agent 编排层**
- LangGraph 状态定义
- 意图识别节点
- 技能选择节点
- LLM 生成节点

---

*实施计划完成日期：2025-01-16*
