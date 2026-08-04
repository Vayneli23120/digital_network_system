"""
AI 分析 Celery 任务

包含：
- 设备配置索引任务（RAG）
"""

from loguru import logger

from app.core.celery_app import celery_app


@celery_app.task(
    name="app.tasks.ai_tasks.index_device_config",
    queue="ai_tasks",
    soft_time_limit=60,
    time_limit=120,
    acks_late=True,
)
def index_device_config_task(
    device_id: int,
    device_name: str,
    config_content: str,
    vendor: str = "cisco"
) -> dict:
    """
    将设备配置索引到 RAG 知识库

    Args:
        device_id: 设备 ID
        device_name: 设备名称
        config_content: 配置文本
        vendor: 设备厂商

    Returns:
        执行结果
    """
    from app.services.rag import rag_engine
    from app.shared.database import get_db_manager
    from app.shared.models import AIKnowledgeDocument
    import uuid
    from datetime import datetime

    # 检查 RAG 是否可用
    if not rag_engine.is_available():
        logger.warning(f"RAG 不可用，跳过设备 {device_name} 配置索引")
        return {"success": False, "error": "RAG not available", "device_id": device_id}

    # 同时保存到数据库
    db_manager = get_db_manager()
    with db_manager.session_scope() as db:
        # 创建知识文档记录
        doc = AIKnowledgeDocument(
            id=str(uuid.uuid4()),
            doc_type="device_config",
            title=f"{device_name} 配置快照",
            content=config_content,
            device_id=device_id,
            indexed_at=datetime.utcnow(),
            embedding_model="text-embedding-3-small",
        )
        db.add(doc)
        db.commit()

        doc_id = doc.id

    # 索引到向量库
    success = rag_engine.index_device_config(
        device_id=device_id,
        device_name=device_name,
        config_content=config_content,
        vendor=vendor,
    )

    logger.info(f"设备 {device_name} 配置索引完成，向量索引: {success}")

    return {
        "success": success,
        "device_id": device_id,
        "doc_id": doc_id,
        "indexed": success,
    }
