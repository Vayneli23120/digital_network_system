"""
Celery 层测试（批次八切片 C）：app/tasks/ai_tasks.py 设备配置索引任务。

无 broker，直调 @celery_app.task 装饰的函数。RAG 引擎在函数内
`from app.services.rag import rag_engine` 导入，patch 目标是
`app.services.rag.rag_engine` 模块属性；数据库经 `database._db_manager`
monkeypatch 路由到测试库。

批次九遗留清理：analyze_fault_task 为死代码（app 内无 .delay/.apply_async
调用，活跃的 /faults/{id}/analyze 走 ADK agent），按用户决定整体删除
（含 format_knowledge），本文件仅保留 index_device_config_task 测试。
见 docs/CODE_REVIEW_ISSUES.md 批次九条目。
"""


class FakeRagEngine:
    """最小 RAG 引擎替身"""

    def __init__(self, available=False, indexed=True):
        self._available = available
        self._indexed = indexed

    def is_available(self):
        return self._available

    def index_device_config(self, **kwargs):
        return self._indexed


class TestIndexDeviceConfigTask:
    def test_success_indexes_document(self, db_manager, db_session, monkeypatch):
        from app.shared import database
        from app.shared.models import AIKnowledgeDocument
        from app.tasks.ai_tasks import index_device_config_task

        monkeypatch.setattr(database, "_db_manager", db_manager)
        monkeypatch.setattr("app.services.rag.rag_engine", FakeRagEngine(available=True, indexed=True))

        result = index_device_config_task(
            device_id=1,
            device_name="SW-01",
            config_content="hostname SW-01\ninterface Gi0/1\n",
            vendor="cisco",
        )

        assert result["success"] is True
        assert result["indexed"] is True
        assert result["doc_id"]

        doc = db_session.query(AIKnowledgeDocument).filter_by(device_id=1).first()
        assert doc is not None
        assert doc.title == "SW-01 配置快照"
        assert doc.doc_type == "device_config"

    def test_rag_unavailable_skips(self, db_manager, monkeypatch):
        from app.shared import database
        from app.tasks.ai_tasks import index_device_config_task

        monkeypatch.setattr(database, "_db_manager", db_manager)
        monkeypatch.setattr("app.services.rag.rag_engine", FakeRagEngine(available=False))

        result = index_device_config_task(device_id=2, device_name="SW-02", config_content="x")
        assert result == {"success": False, "error": "RAG not available", "device_id": 2}
