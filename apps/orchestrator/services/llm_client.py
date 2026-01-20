"""LLM Client Wrapper"""
from typing import Optional
import httpx
import os

# Disable proxy before importing langchain to prevent SOCKS errors
for key in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
    os.environ.pop(key, None)

from langchain_openai import ChatOpenAI
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

logger = LogManager("orchestrator").get_logger()
config = ConfigLoader().load_defaults()
llm_config = ConfigLoader().load_config("llm")

# Create HTTP client with proxy disabled and trust_env=False
_http_client = httpx.Client(
    trust_env=False,
    timeout=httpx.Timeout(60.0)
)
_http_async_client = httpx.AsyncClient(
    trust_env=False,
    timeout=httpx.Timeout(60.0)
)

class LLMClient:
    """LLM Client supporting multiple providers"""

    def __init__(
        self, 
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.provider = provider or llm_config.get("active", "qwen")
        self.provider_config = llm_config.get("providers", {}).get(self.provider, {}).copy()

        if not self.provider_config:
            logger.warning(f"Provider {self.provider} not found in config, falling back to qwen")
            self.provider = "qwen"
            self.provider_config = llm_config.get("providers", {}).get("qwen", {}).copy()
            
        # Override with dynamic values if provided
        if api_key:
            self.provider_config["api_key"] = api_key
        if base_url:
            self.provider_config["base_url"] = base_url

        # Debug logging for API Key and Base URL
        final_api_key = self.provider_config.get("api_key", "")
        masked_key = f"{final_api_key[:8]}...{final_api_key[-4:]}" if len(final_api_key) > 12 else "***"
        logger.info(f"Initializing LLMClient: provider={self.provider}, base_url={self.provider_config.get('base_url')}, api_key={masked_key}")

    def get_chat_model(self, model: Optional[str] = None, temperature: float = 0.7):
        """Get ChatOpenAI instance"""
        model_name = model or self.provider_config.get("models", ["qwen-max"])[0]

        # Use HTTP client with proxy disabled
        return ChatOpenAI(
            base_url=self.provider_config.get("base_url"),
            api_key=self.provider_config.get("api_key"),
            model=model_name,
            temperature=temperature,
            http_client=_http_client,
            http_async_client=_http_async_client,
        )
