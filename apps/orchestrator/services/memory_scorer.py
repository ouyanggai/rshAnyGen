from datetime import datetime
import math
from typing import Optional

class MemoryScorer:
    """记忆评分器(时间衰减)"""
    
    def __init__(self, half_life_days: int = 30):
        self.half_life_days = half_life_days
    
    def calculate_current_importance(
        self,
        base_importance: float,
        created_at: datetime,
        access_count: int = 0,
        last_accessed: Optional[datetime] = None
    ) -> float:
        """计算当前重要性
        
        公式:
        current = base * time_decay + access_boost + recent_boost
        """
        
        # 1. 时间衰减 (指数)
        days_old = (datetime.now() - created_at).days
        # 避免除零
        if days_old < 0: days_old = 0
        
        time_decay = math.exp(-days_old / self.half_life_days)
        
        # 2. 访问频率加成 (最多+0.3)
        access_boost = min(access_count * 0.05, 0.3)
        
        # 3. 最近访问加成 (7天内)
        recent_boost = 0
        if last_accessed:
            days_since = (datetime.now() - last_accessed).days
            if days_since < 7:
                recent_boost = 0.2 * (1 - days_since / 7)
        
        # 4. 综合评分
        score = base_importance * time_decay + access_boost + recent_boost
        
        # 归一化 [0, 1] (允许稍微溢出，但在存储时截断)
        return min(max(score, 0.0), 1.0)
    
    def should_archive(
        self,
        current_importance: float,
        threshold: float = 0.1
    ) -> bool:
        """判断是否应该归档"""
        return current_importance < threshold
