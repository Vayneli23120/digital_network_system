"""
AI 分析 Celery 任务

包含：
- 设备配置索引任务（RAG）
- AI 分析任务
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


@celery_app.task(
    name="app.tasks.ai_tasks.analyze_fault",
    queue="ai_tasks",
    soft_time_limit=120,
    time_limit=180,
    acks_late=True,
)
def analyze_fault_task(
    fault_id: int,
    device_id: int,
    fault_description: str,
    context: dict = None
) -> dict:
    """
    AI 分析故障根因

    Args:
        fault_id: 故障 ID
        device_id: 设备 ID
        fault_description: 故障描述
        context: 上下文信息

    Returns:
        分析结果
    """
    from app.services.rag import rag_engine
    from app.services.ai_tools import AIToolRegistry
    from app.shared.database import get_db_manager
    from app.shared.models import AIAnalysisRecord, Device
    import uuid
    from datetime import datetime

    # 获取设备信息
    db_manager = get_db_manager()
    with db_manager.session_scope() as db:
        device = db.query(Device).filter(Device.id == device_id).first()
        device_name = device.name if device else "unknown"
        device_vendor = device.vendor if device else "cisco"

    # 搜索相关知识
    knowledge_results = []
    if rag_engine.is_available():
        # 搜索设备相关配置
        knowledge_results = rag_engine.search(
            query=f"故障 {fault_description} 配置问题",
            device_id=device_id,
            top_k=5,
        )

        # 搜索历史故障解决方案
        fault_knowledge = rag_engine.search(
            query=fault_description,
            doc_types=["fault_record"],
            top_k=3,
        )
        knowledge_results.extend(fault_knowledge)

    # 构建分析提示词
    prompt = f"""
分析以下网络故障并提供根因分析和解决方案：

设备: {device_name} ({device_vendor})
故障描述: {fault_description}

相关知识:
{format_knowledge(knowledge_results)}

请提供：
1. 可能的根因
2. 推荐的排查步骤
3. 解决方案建议
"""

    # 调用 AI 分析（使用 LiteLLM）
    try:
        import litellm
        from app.shared.config import get_config

        config = get_config()
        model = "gpt-4o-mini"  # 默认模型

        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业的网络运维专家，擅长分析网络故障并提供解决方案。"},
                {"role": "user", "content": prompt},
            ],
            timeout=120,
        )

        analysis_result = response.choices[0].message.content

        # 记录分析结果
        with db_manager.session_scope() as db:
            record = AIAnalysisRecord(
                id=str(uuid.uuid4()),
                analysis_type="fault_analysis",
                target_type="fault",
                target_id=fault_id,
                prompt=prompt,
                response=analysis_result,
                model_name=model,
                ai_provider="litellm",
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                processing_time_ms=int(response._response_ms or 0),
                success=True,
                created_at=datetime.utcnow(),
            )
            db.add(record)
            db.commit()
            record_id = record.id

        logger.info(f"故障 {fault_id} AI 分析完成")

        return {
            "success": True,
            "fault_id": fault_id,
            "record_id": record_id,
            "analysis": analysis_result,
            "knowledge_used": len(knowledge_results),
        }

    except Exception as e:
        logger.error(f"AI 分析失败: {e}")
        return {
            "success": False,
            "fault_id": fault_id,
            "error": str(e),
        }


def format_knowledge(knowledge_results: list) -> str:
    """格式化知识检索结果"""
    if not knowledge_results:
        return "无相关知识"

    formatted = []
    for kr in knowledge_results[:5]:
        score = kr.get("score", 0)
        content = kr.get("content", "")[:500]
        metadata = kr.get("metadata", {})
        doc_type = metadata.get("doc_type", "unknown")

        formatted.append(f"[{doc_type}] (相似度: {score:.2f})\n{content}")

    return "\n\n".join(formatted)