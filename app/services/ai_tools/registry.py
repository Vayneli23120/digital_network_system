"""
AI 工具注册表

所有可被 AI Agent 调用的工具必须在此注册。
每个工具声明所需权限、是否只读、超时限制。
"""

from dataclasses import dataclass
from typing import Callable, List, Optional, Dict, Any
from loguru import logger


@dataclass
class AITool:
    """AI 工具定义"""
    name: str                    # tool 唯一名称
    description: str             # 供 LLM 理解的描述
    parameters_schema: dict      # JSON Schema 参数定义
    handler: Callable            # 执行函数
    requires_permission: str     # 执行需要的权限（如 "device:read"）
    is_readonly: bool = True     # 是否为只读操作
    is_destructive: bool = False # 是否为高危操作
    timeout_seconds: int = 30    # 执行超时
    rate_limit_per_minute: int = 10  # 每分钟最大调用次数


class AIToolRegistry:
    """
    AI 工具注册表

    管理 AI Agent 可调用的所有工具。
    """

    _tools: Dict[str, AITool] = {}

    @classmethod
    def register(cls, tool: AITool) -> None:
        """
        注册工具

        Args:
            tool: AITool 实例
        """
        if tool.is_destructive and tool.is_readonly:
            raise ValueError(f"工具 {tool.name} 不能同时是只读和破坏性操作")

        cls._tools[tool.name] = tool
        logger.debug(f"AI Tool 已注册: {tool.name} (readonly={tool.is_readonly})")

    @classmethod
    def get(cls, name: str) -> Optional[AITool]:
        """
        获取工具

        Args:
            name: 工具名称

        Returns:
            AITool 实例，或 None（未找到）
        """
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        """
        列出所有工具

        Returns:
            工具信息列表
        """
        return [
            {
                "name": t.name,
                "description": t.description,
                "is_readonly": t.is_readonly,
                "is_destructive": t.is_destructive,
                "requires_permission": t.requires_permission,
                "parameters_schema": t.parameters_schema,
            }
            for t in cls._tools.values()
        ]

    @classmethod
    def get_readonly_tools(cls) -> List[AITool]:
        """获取所有只读工具"""
        return [t for t in cls._tools.values() if t.is_readonly]

    @classmethod
    def get_destructive_tools(cls) -> List[AITool]:
        """获取所有高危工具"""
        return [t for t in cls._tools.values() if t.is_destructive]

    @classmethod
    def execute(cls, name: str, parameters: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行工具

        Args:
            name: 工具名称
            parameters: 执行参数
            context: 执行上下文（如 db session）

        Returns:
            执行结果
        """
        tool = cls.get(name)
        if not tool:
            return {"success": False, "error": f"工具 '{name}' 未注册"}

        try:
            result = tool.handler(parameters, context or {})
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"工具执行失败 {name}: {e}")
            return {"success": False, "error": str(e)}


# ===== 内置工具定义 =====

def _get_device_config_handler(params: Dict, context: Dict) -> Dict[str, Any]:
    """获取设备配置"""
    from app.shared.database import get_db_manager
    from app.shared.models import Device, BackupRecord

    device_id = params.get("device_id")
    if not device_id:
        return {"error": "缺少 device_id 参数"}

    db_manager = get_db_manager()
    with db_manager.session_scope() as db:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {"error": f"设备 {device_id} 不存在"}

        # 获取最近备份
        backup = db.query(BackupRecord).filter(
            BackupRecord.device_id == device_id
        ).order_by(BackupRecord.backup_time.desc()).first()

        if not backup:
            return {"error": f"设备 {device.name} 无备份记录"}

        # 读取配置文件
        from pathlib import Path
        backup_path = Path(backup.backup_file)
        if backup_path.exists():
            config_content = backup_path.read_text(encoding='utf-8', errors='ignore')
            return {
                "device_name": device.name,
                "device_ip": device.ip,
                "vendor": device.vendor,
                "config": config_content[:50000],  # 限制长度
                "backup_time": backup.backup_time.isoformat() if backup.backup_time else None,
            }
        else:
            return {"error": f"备份文件不存在: {backup.backup_file}"}


def _get_device_facts_handler(params: Dict, context: Dict) -> Dict[str, Any]:
    """获取设备基本信息"""
    from app.shared.database import get_db_manager
    from app.shared.models import Device

    device_id = params.get("device_id")
    if not device_id:
        return {"error": "缺少 device_id 参数"}

    db_manager = get_db_manager()
    with db_manager.session_scope() as db:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {"error": f"设备 {device_id} 不存在"}

        return {
            "id": device.id,
            "name": device.name,
            "ip": device.ip,
            "vendor": device.vendor,
            "model": device.model,
            "serial_number": device.serial_number,
            "location": device.location,
            "role": device.role,
            "deployment_status": device.deployment_status,
            "reachability": device.reachability,
        }


def _search_knowledge_base_handler(params: Dict, context: Dict) -> Dict[str, Any]:
    """搜索知识库"""
    from app.services.rag import rag_engine

    query = params.get("query")
    if not query:
        return {"error": "缺少 query 参数"}

    doc_types = params.get("doc_types")
    device_id = params.get("device_id")
    top_k = params.get("top_k", 5)

    if not rag_engine.is_available():
        return {"error": "RAG 知识库不可用（需要 PostgreSQL + pgvector）"}

    results = rag_engine.search(
        query=query,
        doc_types=doc_types,
        device_id=device_id,
        top_k=top_k,
    )

    return {
        "query": query,
        "results": results,
        "count": len(results),
    }


def _get_fault_history_handler(params: Dict, context: Dict) -> Dict[str, Any]:
    """获取故障历史"""
    from app.shared.database import get_db_manager
    from app.shared.models import FaultRecord

    device_id = params.get("device_id")
    limit = params.get("limit", 10)

    db_manager = get_db_manager()
    with db_manager.session_scope() as db:
        query = db.query(FaultRecord).order_by(FaultRecord.fault_time.desc())
        if device_id:
            query = query.filter(FaultRecord.device_id == device_id)

        faults = query.limit(limit).all()

        return {
            "faults": [
                {
                    "id": f.id,
                    "fault_no": f.fault_no,
                    "title": f.title,
                    "severity": f.severity,
                    "status": f.status,
                    "fault_time": f.fault_time.isoformat() if f.fault_time else None,
                    "resolved_at": f.resolved_at.isoformat() if f.resolved_at else None,
                    "description": f.description[:500] if f.description else None,
                }
                for f in faults
            ],
            "count": len(faults),
        }


def _get_compliance_status_handler(params: Dict, context: Dict) -> Dict[str, Any]:
    """获取合规状态"""
    from app.shared.database import get_db_manager
    from app.shared.models import ComplianceResult, Device

    device_id = params.get("device_id")

    db_manager = get_db_manager()
    with db_manager.session_scope() as db:
        if device_id:
            results = db.query(ComplianceResult).filter(
                ComplianceResult.device_id == device_id
            ).order_by(ComplianceResult.checked_at.desc()).limit(10).all()
        else:
            results = db.query(ComplianceResult).order_by(
                ComplianceResult.checked_at.desc()
            ).limit(50).all()

        return {
            "results": [
                {
                    "id": r.id,
                    "device_id": r.device_id,
                    "result_status": r.result_status,
                    "checked_at": r.checked_at.isoformat() if r.checked_at else None,
                    "evidence": r.evidence[:200] if r.evidence else None,
                }
                for r in results
            ],
            "count": len(results),
        }


# ===== 注册内置工具 =====

get_device_config_tool = AITool(
    name="get_device_config",
    description="获取指定设备的配置文件内容",
    parameters_schema={
        "type": "object",
        "properties": {
            "device_id": {"type": "integer", "description": "设备 ID"},
        },
        "required": ["device_id"],
    },
    handler=_get_device_config_handler,
    requires_permission="device:read",
    is_readonly=True,
    timeout_seconds=60,
)

get_device_facts_tool = AITool(
    name="get_device_facts",
    description="获取设备基本信息（名称、IP、型号、状态等）",
    parameters_schema={
        "type": "object",
        "properties": {
            "device_id": {"type": "integer", "description": "设备 ID"},
        },
        "required": ["device_id"],
    },
    handler=_get_device_facts_handler,
    requires_permission="device:read",
    is_readonly=True,
)

search_knowledge_base_tool = AITool(
    name="search_knowledge_base",
    description="在 RAG 知识库中搜索相关信息",
    parameters_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索问题"},
            "device_id": {"type": "integer", "description": "限定设备范围（可选）"},
            "doc_types": {"type": "array", "items": {"type": "string"}, "description": "限定文档类型"},
            "top_k": {"type": "integer", "default": 5, "description": "返回数量"},
        },
        "required": ["query"],
    },
    handler=_search_knowledge_base_handler,
    requires_permission="knowledge:read",
    is_readonly=True,
)

get_fault_history_tool = AITool(
    name="get_fault_history",
    description="获取设备或系统的故障历史记录",
    parameters_schema={
        "type": "object",
        "properties": {
            "device_id": {"type": "integer", "description": "设备 ID（可选）"},
            "limit": {"type": "integer", "default": 10, "description": "返回数量限制"},
        },
    },
    handler=_get_fault_history_handler,
    requires_permission="fault:read",
    is_readonly=True,
)

get_compliance_status_tool = AITool(
    name="get_compliance_status",
    description="获取设备的合规检查状态",
    parameters_schema={
        "type": "object",
        "properties": {
            "device_id": {"type": "integer", "description": "设备 ID（可选）"},
        },
    },
    handler=_get_compliance_status_handler,
    requires_permission="compliance:read",
    is_readonly=True,
)


# 初始化注册
def _register_builtin_tools():
    """注册内置工具"""
    for tool in [
        get_device_config_tool,
        get_device_facts_tool,
        search_knowledge_base_tool,
        get_fault_history_tool,
        get_compliance_status_tool,
    ]:
        AIToolRegistry.register(tool)


_register_builtin_tools()