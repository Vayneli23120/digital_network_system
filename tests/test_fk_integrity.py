"""
批次十 · 数据层 P2 遗留测试：裸 Integer 伪外键转真 FK 后的完整性。

models.py / models_jobs.py 的 6 处 *_id 列已改为 ForeignKey("devices.id", ondelete=...)：
- SET NULL：fault_records.peer_device_id、device_interfaces.peer_device_id、
  ai_knowledge_documents.device_id、jobs.device_id
- CASCADE：interface_traffic_samples.device_id、deploy_device_results.device_id

SQLite（测试库）PRAGMA foreign_keys=ON（database.py:65-70），故 DB 级约束与
ondelete 行为在测试中真实生效。本文件覆盖：孤儿写入拒绝 + 两类 ondelete。
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.shared.models import (
    AIKnowledgeDocument,
    DeployDeviceResult,
    DeployHistory,
    Device,
    DeviceInterface,
    FaultRecord,
    InterfaceTrafficSample,
)


def _seed_device(db_session, *, name="FK-Device", ip="10.99.0.1", **kw):
    dev = Device(name=name, ip=ip, **kw)
    db_session.add(dev)
    db_session.flush()
    return dev


def _fetch(db_session, model, row_id):
    return db_session.query(model).filter_by(id=row_id).first()


class TestFkEnforcement:
    def test_orphan_interface_sample_device_rejected(self, db_session):
        """interface_traffic_samples.device_id → devices.id：孤儿 device_id 写入被拒绝。"""
        dev = _seed_device(db_session, name="FK-Orphan-Device")
        iface = DeviceInterface(device_id=dev.id, if_index=1, if_name="Gi0/1")
        db_session.add(iface)
        db_session.flush()
        # 提交父行：孤儿写入的 rollback 不会连带回滚它们（否则合法写入也引用不到父行）
        db_session.commit()
        dev_id, iface_id = dev.id, iface.id

        db_session.add(
            InterfaceTrafficSample(device_id=999999, interface_id=iface_id, ts=datetime.utcnow())
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

        # 合法 device_id 正常写入
        sample = InterfaceTrafficSample(device_id=dev_id, interface_id=iface_id, ts=datetime.utcnow())
        db_session.add(sample)
        db_session.flush()
        assert sample.id is not None


class TestOnDeleteSetNull:
    def test_fault_peer_device_nulled_on_delete(self, db_session):
        """fault_records.peer_device_id → devices.id SET NULL：删对端设备后置 NULL。"""
        peer = _seed_device(db_session, name="FK-Peer", ip="10.99.0.2")
        owner = _seed_device(db_session, name="FK-Owner", ip="10.99.0.3")
        fault = FaultRecord(fault_no="FK-001", device_id=owner.id, peer_device_id=peer.id)
        db_session.add(fault)
        db_session.flush()

        db_session.delete(peer)
        db_session.commit()
        db_session.expire_all()

        reloaded = _fetch(db_session, FaultRecord, fault.id)
        assert reloaded is not None  # 故障单保留
        assert reloaded.peer_device_id is None  # 对端引用置 NULL

    def test_knowledge_doc_survives_device_delete(self, db_session):
        """ai_knowledge_documents.device_id → devices.id SET NULL：删设备后文档保留、device_id 置 NULL。"""
        dev = _seed_device(db_session, name="FK-Doc-Device", ip="10.99.0.4")
        doc = AIKnowledgeDocument(
            id="00000000-0000-0000-0000-000000000001",
            doc_type="device_config",
            title="FK 配置快照",
            content="hostname x\n",
            device_id=dev.id,
        )
        db_session.add(doc)
        db_session.flush()

        db_session.delete(dev)
        db_session.commit()
        db_session.expire_all()

        reloaded = _fetch(db_session, AIKnowledgeDocument, doc.id)
        assert reloaded is not None  # 文档保留
        assert reloaded.device_id is None  # 设备引用置 NULL


class TestOnDeleteCascade:
    def test_deploy_device_result_cascade_on_device_delete(self, db_session):
        """deploy_device_results.device_id → devices.id CASCADE：删设备后结果行删除。"""
        dev = _seed_device(db_session, name="FK-Deploy-Device", ip="10.99.0.5")
        history = DeployHistory(operation_type="deploy", engine="netmiko", success=True)
        db_session.add(history)
        db_session.flush()
        result = DeployDeviceResult(
            deploy_id=history.id,
            device_id=dev.id,
            device_name=dev.name,
            status="completed",
        )
        db_session.add(result)
        db_session.flush()
        result_id = result.id  # 先捕获 id：删设备后 ORM 对象行已级联消失，再取属性会 ObjectDeletedError

        db_session.delete(dev)
        db_session.commit()
        db_session.expire_all()

        assert _fetch(db_session, DeployDeviceResult, result_id) is None  # 随设备级联删除
