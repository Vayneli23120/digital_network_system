"""
RAG 检索引擎

使用 LangChain + pgvector 构建企业级知识检索能力。
"""

from typing import List, Optional, Dict, Any
from loguru import logger


class RAGEngine:
    """RAG 知识检索引擎"""

    def __init__(self):
        self._vector_store = None
        self._embeddings = None

    def _get_embeddings(self):
        """获取 Embedding 模型（复用 LiteLLM 配置）"""
        if self._embeddings:
            return self._embeddings

        try:
            from langchain_openai import OpenAIEmbeddings
            from app.shared.config import get_config

            config = get_config()
            # 使用 LiteLLM 代理，兼容 OpenAI 接口
            api_key = "not-set"
            base_url = None

            # 尝试获取 AI 配置
            if hasattr(config, 'ai') and hasattr(config.ai, 'api_key'):
                api_key = config.ai.api_key
                base_url = config.ai.base_url if hasattr(config.ai, 'base_url') else None

            self._embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                base_url=base_url,
                api_key=api_key,
                dimensions=1536,
            )
            return self._embeddings
        except ImportError:
            logger.warning("langchain_openai 未安装，RAG 功能不可用")
            return None

    def _get_vector_store(self):
        """获取 pgvector 向量存储"""
        if self._vector_store:
            return self._vector_store

        try:
            from langchain_community.vectorstores import PGVector
            from app.shared.config import get_config
            from app.shared.database import get_db_manager

            config = get_config()
            if not config.database.is_postgresql:
                logger.warning("RAG 需要 PostgreSQL + pgvector，当前使用 SQLite，知识检索不可用")
                return None

            # PGVector 使用 psycopg2 同步连接
            db_manager = get_db_manager()
            pg_url = db_manager.db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
            pg_url = pg_url.replace("sqlite+aiosqlite", "sqlite")

            embeddings = self._get_embeddings()
            if not embeddings:
                return None

            self._vector_store = PGVector(
                connection_string=pg_url,
                embedding_function=embeddings,
                collection_name="nas_knowledge",
                pre_delete_collection=False,
            )
            return self._vector_store
        except ImportError as e:
            logger.error(f"pgvector/LangChain 未安装: {e}")
            return None
        except Exception as e:
            logger.error(f"初始化向量存储失败: {e}")
            return None

    def is_available(self) -> bool:
        """检查 RAG 是否可用"""
        from app.shared.config import get_config
        config = get_config()
        return config.database.is_postgresql and self._get_embeddings() is not None

    def index_document(
        self,
        doc_type: str,
        title: str,
        content: str,
        device_id: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        将文档索引到向量库

        Args:
            doc_type: 文档类型
            title: 文档标题
            content: 文档内容
            device_id: 关联设备 ID
            metadata: 元数据字典

        Returns:
            是否成功
        """
        vector_store = self._get_vector_store()
        if not vector_store:
            logger.warning("向量存储不可用，跳过索引")
            return False

        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            from langchain.schema import Document
            import uuid

            # 按配置段落分块（interface/router/policy 等）
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100,
                separators=["\n!\n", "\n !\n", "\ninterface ", "\nrouter ", "\n", " "],
            )

            chunks = splitter.split_text(content)

            doc_metadata = {
                "doc_type": doc_type,
                "title": title,
                "device_id": device_id or 0,
            }
            if metadata:
                doc_metadata.update(metadata)

            docs = [
                Document(
                    page_content=chunk,
                    metadata={**doc_metadata, "chunk_index": i}
                )
                for i, chunk in enumerate(chunks)
            ]

            vector_store.add_documents(docs)
            logger.info(f"文档 '{title}' 已索引，共 {len(docs)} 个块")
            return True

        except Exception as e:
            logger.error(f"文档索引失败: {e}")
            return False

    def index_device_config(
        self,
        device_id: int,
        device_name: str,
        config_content: str,
        vendor: str = "cisco"
    ) -> bool:
        """
        将设备配置索引到向量库

        Args:
            device_id: 设备 ID
            device_name: 设备名称
            config_content: 配置文本
            vendor: 设备厂商

        Returns:
            是否成功
        """
        return self.index_document(
            doc_type="device_config",
            title=f"{device_name} 配置快照",
            content=config_content,
            device_id=device_id,
            metadata={
                "device_name": device_name,
                "vendor": vendor,
            }
        )

    def search(
        self,
        query: str,
        doc_types: Optional[List[str]] = None,
        device_id: Optional[int] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        语义检索知识库

        Args:
            query: 检索问题
            doc_types: 限制文档类型（None 表示全部）
            device_id: 限制设备范围
            top_k: 返回最相关的 K 个结果

        Returns:
            相关文档列表，按相似度降序
        """
        vector_store = self._get_vector_store()
        if not vector_store:
            return []

        try:
            # 构建过滤器
            filter_dict = {}
            if doc_types:
                # PGVector filter 格式
                filter_dict["doc_type"] = {"$in": doc_types}
            if device_id:
                filter_dict["device_id"] = device_id

            docs_with_scores = vector_store.similarity_search_with_score(
                query=query,
                k=top_k,
                filter=filter_dict if filter_dict else None,
            )

            return [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score),
                }
                for doc, score in docs_with_scores
            ]

        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []

    def search_device_knowledge(
        self,
        device_id: int,
        query: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        搜索特定设备的相关知识

        Args:
            device_id: 设备 ID
            query: 检索问题
            top_k: 返回数量

        Returns:
            相关文档列表
        """
        return self.search(
            query=query,
            device_id=device_id,
            top_k=top_k,
        )


# 全局 RAG 引擎实例
rag_engine = RAGEngine()