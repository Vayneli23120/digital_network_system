"""
Celery 层测试（批次八切片 C / 批次九修复）：app/tasks/ai_tasks.py 两个任务。

无 broker，直调 @celery_app.task 装饰的函数。RAG 引擎在函数内
`from app.services.rag import rag_engine` 导入，patch 目标是
`app.services.rag.rag_engine` 模块属性；litellm 用 `sys.modules['litellm']`
注入 stub；数据库经 `database._db_manager` monkeypatch 路由到测试库。

批次九修复后 analyze_fault_task 成功路径不再因 AIAnalysisRecord 列名
不匹配（prompt/response/input_tokens/output_tokens/success）而恒失败，
改为对齐模型列（input_data/output_result/tokens_used/status），本测试
断言成功落库。任务仍为死代码（app 内无 .delay/.apply_async 调用，
活跃的 /faults/{id}/analyze 走 ADK agent），见 docs/CODE_REVIEW_ISSUES.md
批次九条目。
"""

import sys
from types import SimpleNamespace
from unittest import mock


class FakeRagEngine:
    """最小 RAG 引擎替身"""

    def __init__(self, available=False, indexed=True):
        self._available = available
        self._indexed = indexed

    def is_available(self):
        return self._available

    def index_device_config(self, **kwargs):
        return self._indexed

    def search(self, **kwargs):
        return []


def _make_litellm_response(content="根因分析结果"):
    resp = mock.MagicMock()
    resp.choices[0].message.content = content
    resp.usage.prompt_tokens = 10
    resp.usage.completion_tokens = 20
    resp._response_ms = 100
    return resp


def _inject_litellm(monkeypatch, *, completion=None, response=None):
    stub = SimpleNamespace()
    if response is not None:
        stub.completion = mock.MagicMock(return_value=response)
    elif completion is not None:
        stub.completion = completion
    else:
        stub.completion = mock.MagicMock(return_value=None)
    monkeypatch.setitem(sys.modules, "litellm", stub)
    return stub


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


class TestAnalyzeFaultTask:
    def _seed_device(self, db_session, device_id=10):
        from app.shared.models import Device

        dev = Device(id=device_id, name="SW-10", ip="10.0.0.10", vendor="cisco")
        db_session.add(dev)
        db_session.commit()

    def test_success_records_analysis(self, db_manager, db_session, monkeypatch):
        """批次九修复后：AIAnalysisRecord 成功落库（列对齐 canonical 用法）。"""
        from app.shared import database
        from app.shared.models import AIAnalysisRecord
        from app.tasks.ai_tasks import analyze_fault_task

        self._seed_device(db_session)
        monkeypatch.setattr(database, "_db_manager", db_manager)
        monkeypatch.setattr("app.services.rag.rag_engine", FakeRagEngine(available=False))
        _inject_litellm(monkeypatch, response=_make_litellm_response())

        result = analyze_fault_task(
            fault_id=5,
            device_id=10,
            fault_description="端口翻动",
            context={},
        )

        assert result["success"] is True
        assert result["fault_id"] == 5
        assert isinstance(result["record_id"], int)  # id 自增，非 uuid 字符串
        assert result["analysis"] == "根因分析结果"

        record = db_session.query(AIAnalysisRecord).filter_by(id=result["record_id"]).first()
        assert record is not None
        assert record.status == "completed"
        assert record.target_type == "fault"
        assert record.target_id == 5
        assert record.output_result == "根因分析结果"
        assert record.tokens_used == 30  # prompt 10 + completion 20
        assert record.ai_provider == "litellm"

    def test_litellm_error_returns_failure(self, db_manager, db_session, monkeypatch):
        from app.shared import database
        from app.tasks.ai_tasks import analyze_fault_task

        self._seed_device(db_session)
        monkeypatch.setattr(database, "_db_manager", db_manager)
        monkeypatch.setattr("app.services.rag.rag_engine", FakeRagEngine(available=False))

        def failing_completion(**kwargs):
            raise RuntimeError("upstream timeout")

        _inject_litellm(monkeypatch, completion=failing_completion)

        result = analyze_fault_task(
            fault_id=6,
            device_id=10,
            fault_description="CPU 高",
            context={},
        )

        assert result["success"] is False
        assert result["error"] == "upstream timeout"
