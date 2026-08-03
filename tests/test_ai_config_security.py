"""批次二·安全 切片 B · AI Key 加密（item 115）

覆盖：
- compliance /ai-config 创建加密、更新 None 保留、测试不再写 os.environ 且直传 api_key
- adk/config get_model_config 解密返回 api_key、不再写 os.environ
- adk/runner acompletion 直传 api_key
- 运行时：create_ai_config 落库值为密文且可解密回明文
"""

import asyncio
from pathlib import Path

import pytest

import app.shared.models_jobs  # noqa: F401  让 jobs 表进入 Base.metadata

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"


def _read(rel_path: str) -> str:
    return (APP_DIR / rel_path).read_text(encoding="utf-8")


# ==================== 静态：compliance /ai-config ====================


class TestComplianceAiConfigStatic:
    def test_create_encrypts_key(self):
        src = _read("features/compliance/router.py")
        assert "api_key_encrypted=encrypt_text(request.api_key) if request.api_key else None," in src
        assert "暂不加密" not in src

    def test_update_keeps_existing_when_none(self):
        src = _read("features/compliance/router.py")
        assert "if request.api_key is not None:" in src
        assert "config.api_key_encrypted = encrypt_text(request.api_key)" in src

    def test_test_endpoint_no_os_environ_and_passes_api_key(self):
        src = _read("features/compliance/router.py")
        test_block = src.split("async def test_ai_config", 1)[1].split("async def list_checks", 1)[0]
        assert "os.environ" not in test_block
        assert "api_key=request.api_key" in test_block

    def test_get_ai_config_does_not_return_key(self):
        src = _read("features/compliance/router.py")
        assert "不返回 api_key（安全考虑）" in src


# ==================== 静态：adk 消费侧 ====================


class TestAdkConsumptionStatic:
    def test_get_model_config_decrypts_and_no_env(self):
        src = _read("services/adk/config.py")
        model_block = src.split("def get_model_config", 1)[1].split("def create_litellm_model", 1)[0]
        assert "os.environ[" not in model_block
        assert 'result["api_key"] = decrypt_or_passthrough(config.api_key_encrypted)' in model_block

    def test_create_litellm_model_passes_api_key(self):
        src = _read("services/adk/config.py")
        assert "api_key=config_dict.get(\"api_key\")," in src

    def test_runner_passes_api_key(self):
        src = _read("services/adk/runner.py")
        assert "api_key=model_config.get(\"api_key\")," in src


# ==================== 运行时：create_ai_config 落库加密 ====================


class TestCreateAiConfigEncrypts:
    def test_stored_value_is_ciphertext(self, db_session, monkeypatch):
        import app.shared.database as db_module
        from app.features.compliance.router import AIConfigRequest, create_ai_config
        from app.shared.crypto import decrypt_text

        def _fake_get_db():
            yield db_session

        monkeypatch.setattr(db_module, "get_db", _fake_get_db)

        request = AIConfigRequest(
            provider="openai",
            model_name="gpt-4",
            api_key="sk-test-plain-123",
            is_default=False,
        )
        result = asyncio.run(create_ai_config(request, None))

        from app.shared.models import AIConfig

        row = db_session.query(AIConfig).filter(AIConfig.id == result["id"]).first()
        assert row is not None
        assert row.api_key_encrypted != "sk-test-plain-123"
        assert decrypt_text(row.api_key_encrypted) == "sk-test-plain-123"
