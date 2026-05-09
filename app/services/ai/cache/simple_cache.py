"""AI响应缓存

简单内存缓存，用于减少重复AI调用。
"""

import time
import hashlib
import json
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    ttl: int  # 秒
    hits: int = 0


class AICache:
    """AI响应缓存"""

    def __init__(self, default_ttl: int = 3600):
        """
        Args:
            default_ttl: 默认缓存时间（秒），默认1小时
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl

    def _generate_key(self, prompt: str, context: Optional[str] = None) -> str:
        """生成缓存键"""
        content = f"{prompt}|{context or ''}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, prompt: str, context: Optional[str] = None) -> Optional[Any]:
        """获取缓存"""
        key = self._generate_key(prompt, context)
        entry = self.cache.get(key)

        if entry:
            # 检查是否过期
            if time.time() - entry.created_at > entry.ttl:
                del self.cache[key]
                return None

            entry.hits += 1
            return entry.value

        return None

    def set(
        self,
        prompt: str,
        value: Any,
        context: Optional[str] = None,
        ttl: Optional[int] = None
    ):
        """设置缓存"""
        key = self._generate_key(prompt, context)
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl or self.default_ttl
        )
        self.cache[key] = entry

    def clear(self):
        """清空缓存"""
        self.cache.clear()

    def cleanup(self):
        """清理过期缓存"""
        now = time.time()
        expired_keys = [
            k for k, e in self.cache.items()
            if now - e.created_at > e.ttl
        ]
        for key in expired_keys:
            del self.cache[key]

    def stats(self) -> Dict:
        """获取缓存统计"""
        total_hits = sum(e.hits for e in self.cache.values())
        return {
            'entries': len(self.cache),
            'total_hits': total_hits,
            'size_bytes': sum(len(json.dumps(e.value)) for e in self.cache.values())
        }


# 单例实例
ai_cache = AICache()