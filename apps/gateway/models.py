"""Gateway 数据模型"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    """聊天请求"""
    session_id: Optional[str] = None
    message: str
    stream: bool = True
    enable_search: bool = False
    kb_ids: Optional[List[str]] = None
    model: Optional[str] = None  # LLM 模型名称

class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str
    content: str
    finish_reason: Optional[str] = None

class SkillInfo(BaseModel):
    """技能信息"""
    id: str
    name: str
    description: str
    enabled: bool
    requires_consent: bool
    category: Optional[str] = None

class SkillListResponse(BaseModel):
    """技能列表响应"""
    skills: List[SkillInfo]
