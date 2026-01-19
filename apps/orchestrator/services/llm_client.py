"""LLM Client Wrapper"""
from typing import Optional
from langchain_openai import ChatOpenAI
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

logger = LogManager("orchestrator").get_logger()
config = ConfigLoader().load_defaults()
llm_config = ConfigLoader().load_config("llm")

class LLMClient:
    """LLM Client supporting multiple providers"""
    
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or llm_config.get("active", "qwen")
        self.provider_config = llm_config.get("providers", {}).get(self.provider, {})
        
        if not self.provider_config:
            logger.warning(f"Provider {self.provider} not found in config, falling back to qwen")
            self.provider = "qwen"
            self.provider_config = llm_config.get("providers", {}).get("qwen", {})

    def get_chat_model(self, model: Optional[str] = None, temperature: float = 0.7):
        """Get ChatOpenAI instance"""
        model_name = model or self.provider_config.get("models", ["qwen-max"])[0]
        
        return ChatOpenAI(
            base_url=self.provider_config.get("base_url"),
            api_key=self.provider_config.get("api_key"),
            model=model_name,
            temperature=temperature,
        )
