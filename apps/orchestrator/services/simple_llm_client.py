"""Simple LLM Client - Direct API calls bypassing langchain"""
from typing import Optional, List
import httpx
import os
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

logger = LogManager("orchestrator").get_logger()
config = ConfigLoader().load_defaults()
llm_config = ConfigLoader().load_config("llm")

class SimpleLLMClient:
    """Simple LLM client with direct API calls"""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or llm_config.get("active", "qwen")
        self.provider_config = llm_config.get("providers", {}).get(self.provider, {})

        if not self.provider_config:
            logger.warning(f"Provider {self.provider} not found, falling back to qwen")
            self.provider = "qwen"
            self.provider_config = llm_config.get("providers", {}).get("qwen", {})

        # Get API key from config or environment
        api_key = self.provider_config.get("api_key", "")
        # Expand environment variable if needed
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.environ.get(env_var, "")

        self.api_key = api_key
        self.base_url = self.provider_config.get("base_url", "")
        self.model = self.provider_config.get("models", ["glm-4-flash"])[0]
        self.timeout = self.provider_config.get("timeout", 60)

    async def achat(self, messages: List[str], temperature: float = 0.7) -> str:
        """Async chat completion"""
        # Format messages for API
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, str):
                formatted_messages.append({"role": "user", "content": msg})
            else:
                formatted_messages.append(msg)

        # Create HTTP client without proxy
        async with httpx.AsyncClient(
            proxies=None,
            trust_env=False,
            timeout=self.timeout
        ) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": formatted_messages,
                    "temperature": temperature
                }
            )

            if response.status_code != 200:
                logger.error(f"LLM API error: {response.status_code} - {response.text}")
                raise Exception(f"LLM API error: {response.status_code}")

            result = response.json()
            return result["choices"][0]["message"]["content"]

    def chat(self, message: str, temperature: float = 0.7) -> str:
        """Sync chat completion"""
        import asyncio

        # Create new event loop if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.achat([message], temperature))
