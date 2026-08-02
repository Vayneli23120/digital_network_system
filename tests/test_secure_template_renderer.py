"""安全网络配置模板渲染器回归测试。"""

import pytest

from app.shared.template_renderer import (
    MAX_RENDERED_BYTES,
    NetworkTemplateRenderError,
    render_network_template,
)


def test_renders_variables_loops_conditions_and_time_helpers():
    template = """! {{ now_str }}
! {{ now().strftime('%Y-%m-%d') }}
hostname {{ HOSTNAME }}
{% if ENABLE_VLAN %}{% for vlan in vlans %}vlan {{ vlan.id }}
 name {{ vlan.name }}
{% endfor %}{% endif %}"""

    rendered = render_network_template(template, {
        "HOSTNAME": "SW-01",
        "ENABLE_VLAN": True,
        "vlans": [
            {"id": 10, "name": "USERS"},
            {"id": 20, "name": "VOICE"},
        ],
    })

    assert "hostname SW-01" in rendered
    assert "vlan 10" in rendered
    assert "name VOICE" in rendered
    assert "{{" not in rendered


def test_missing_variable_remains_empty_for_compatibility():
    rendered = render_network_template(
        "hostname {{ HOSTNAME }}\nsysname {{ SYSNAME }}\n",
        {"HOSTNAME": "SW-01"},
    )

    assert "hostname SW-01" in rendered
    assert "sysname " in rendered


def test_device_context_is_copied_as_plain_data():
    rendered = render_network_template(
        "hostname {{ device.name }}\nip address {{ device.ip }}",
        {},
        device={"name": "SW-01", "ip": "192.0.2.10"},
    )

    assert "hostname SW-01" in rendered
    assert "ip address 192.0.2.10" in rendered


@pytest.mark.parametrize("payload", [
    "{{ ''.__class__.__mro__[1].__subclasses__() }}",
    "{{ cycler.__init__.__globals__.os.popen('whoami').read() }}",
    "{{ lipsum.__globals__['os'].popen('whoami').read() }}",
    "{{ config.__class__.__init__.__globals__['os'].system('whoami') }}",
])
def test_blocks_ssti_attribute_and_global_escape(payload):
    with pytest.raises(NetworkTemplateRenderError):
        render_network_template(payload)


@pytest.mark.parametrize("value", [object(), RuntimeError, lambda: "unsafe"])
def test_rejects_non_json_context_values(value):
    with pytest.raises(NetworkTemplateRenderError, match="JSON"):
        render_network_template("{{ value }}", {"value": value})


def test_rejects_reserved_context_overrides():
    with pytest.raises(NetworkTemplateRenderError, match="保留变量"):
        render_network_template("{{ now }}", {"now": "fake"})


def test_rejects_invalid_syntax_without_leaking_detail():
    with pytest.raises(NetworkTemplateRenderError, match="模板语法或渲染无效") as exc:
        render_network_template("hostname {{ INVALID SYNTAX")

    assert "INVALID" not in str(exc.value)


def test_limits_rendered_output_size(monkeypatch):
    import app.shared.template_renderer as renderer

    monkeypatch.setattr(renderer, "MAX_RENDERED_BYTES", 8)

    with pytest.raises(NetworkTemplateRenderError, match="渲染结果"):
        render_network_template("123456789")

    assert MAX_RENDERED_BYTES > 8


def test_rejects_oversized_context_before_render(monkeypatch):
    import app.shared.template_renderer as renderer

    monkeypatch.setattr(renderer, "MAX_CONTEXT_BYTES", 8)

    with pytest.raises(NetworkTemplateRenderError, match="变量内容"):
        render_network_template("{{ value }}", {"value": "123456789"})


@pytest.mark.parametrize("payload", [
    "{{ 'x' * 999999999 }}",
    "{{ 999999999 ** 999999999 }}",
])
def test_blocks_expression_resource_amplification(payload):
    with pytest.raises(NetworkTemplateRenderError, match="不安全"):
        render_network_template(payload)


def test_all_builtin_templates_render_in_sandbox(monkeypatch):
    import app.shared.db_init as db_init

    captured_templates = []

    class QueryStub:
        @staticmethod
        def first():
            return None

    class SessionStub:
        @staticmethod
        def query(_model):
            return QueryStub()

        @staticmethod
        def add(template):
            captured_templates.append(template)

        @staticmethod
        def commit():
            return None

        @staticmethod
        def rollback():
            return None

        @staticmethod
        def close():
            return None

    class ManagerStub:
        @staticmethod
        def get_session():
            return SessionStub()

    monkeypatch.setattr(db_init, "get_db_manager", ManagerStub)

    db_init.init_default_templates()

    assert len(captured_templates) == 4
    for template in captured_templates:
        rendered = render_network_template(template.template_content)
        assert rendered.strip()
        assert "{{" not in rendered
        assert "{%" not in rendered
