"""Skills Registry Client"""
import httpx
from typing import Dict, Any, List, Optional
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

logger = LogManager("orchestrator").get_logger()
config = ConfigLoader().load_defaults()

class SkillsRegistryClient:
    """Client for Skills Registry Service"""
    
    def __init__(self):
        self.base_url = f"http://localhost:{config.get('ports', {}).get('skills_registry', 9303)}"
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def get_skill(self, skill_id: str) -> Dict[str, Any]:
        """Get skill definition"""
        try:
            response = await self.client.get(f"/api/v1/skills/{skill_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting skill {skill_id}: {e}")
            raise

    async def execute_skill(self, skill_id: str, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a skill"""
        try:
            payload = {
                "params": params,
                "context": context or {}
            }
            response = await self.client.post(f"/api/v1/skills/{skill_id}/execute", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error executing skill {skill_id}: {e}")
            raise

    async def close(self):
        await self.client.aclose()
