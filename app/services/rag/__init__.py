"""
RAG 服务模块

提供：
- rag_engine: RAG 检索引擎
"""

from app.services.rag.rag_engine import RAGEngine, rag_engine

__all__ = ["RAGEngine", "rag_engine"]