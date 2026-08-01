"""网络配置模板的受限 Jinja 渲染器。"""

from datetime import datetime
from typing import Any, Mapping, Optional

from jinja2 import TemplateError
from jinja2.sandbox import ImmutableSandboxedEnvironment, SecurityError

MAX_TEMPLATE_BYTES = 1_000_000
MAX_RENDERED_BYTES = 2_000_000
MAX_CONTEXT_BYTES = 1_000_000
MAX_CONTEXT_DEPTH = 20
MAX_CONTEXT_ITEMS = 10_000
RESERVED_CONTEXT_KEYS = frozenset({"now", "now_str", "device"})


class NetworkTemplateRenderError(ValueError):
    """模板无法安全渲染。"""


class _ContextBudget:
    def __init__(self) -> None:
        self.items = 0
        self.bytes = 0

    def consume(self) -> None:
        self.items += 1
        if self.items > MAX_CONTEXT_ITEMS:
            raise NetworkTemplateRenderError("模板变量数量超过安全限制")

    def consume_bytes(self, size: int) -> None:
        self.bytes += size
        if self.bytes > MAX_CONTEXT_BYTES:
            raise NetworkTemplateRenderError("模板变量内容超过安全大小限制")


def _normalize_value(value: Any, budget: _ContextBudget, depth: int = 0) -> Any:
    """复制 JSON 兼容值，阻断 ORM、模块、类和任意 Python 对象进入沙箱。"""
    if depth > MAX_CONTEXT_DEPTH:
        raise NetworkTemplateRenderError("模板变量嵌套层级超过安全限制")

    budget.consume()
    if isinstance(value, str):
        budget.consume_bytes(len(value.encode("utf-8")))
        return value
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item, budget, depth + 1) for item in value]
    if isinstance(value, Mapping):
        normalized = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise NetworkTemplateRenderError("模板变量对象的键必须是字符串")
            budget.consume_bytes(len(key.encode("utf-8")))
            normalized[key] = _normalize_value(item, budget, depth + 1)
        return normalized
    raise NetworkTemplateRenderError(
        f"模板变量仅支持 JSON 类型，不支持 {type(value).__name__}"
    )


class _NetworkTemplateEnvironment(ImmutableSandboxedEnvironment):
    intercepted_binops = frozenset({"*", "**"})

    def call_binop(self, context, operator, left, right):
        if operator == "**":
            if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
                raise SecurityError("unsafe exponentiation")
            if abs(left) > 1_000_000 or abs(right) > 8:
                raise SecurityError("exponentiation limit exceeded")
        elif operator == "*":
            repeated_value = None
            repeat_count = None
            if isinstance(right, int) and isinstance(left, (str, list, tuple)):
                repeated_value, repeat_count = left, right
            elif isinstance(left, int) and isinstance(right, (str, list, tuple)):
                repeated_value, repeat_count = right, left
            if repeated_value is not None and repeat_count is not None:
                unit_size = (
                    len(repeated_value.encode("utf-8"))
                    if isinstance(repeated_value, str)
                    else len(repeated_value)
                )
                if repeat_count > 0 and unit_size * repeat_count > MAX_RENDERED_BYTES:
                    raise SecurityError("repetition limit exceeded")
        return super().call_binop(context, operator, left, right)


def _safe_environment() -> ImmutableSandboxedEnvironment:
    environment = _NetworkTemplateEnvironment(autoescape=False)
    environment.globals.clear()
    return environment


def render_network_template(
    template_content: str,
    variables: Optional[Mapping[str, Any]] = None,
    *,
    device: Optional[Mapping[str, Any]] = None,
) -> str:
    """安全渲染网络配置模板，同时保留现有 Jinja 基础语法兼容性。"""
    if not isinstance(template_content, str):
        raise NetworkTemplateRenderError("模板内容必须是字符串")
    if len(template_content.encode("utf-8")) > MAX_TEMPLATE_BYTES:
        raise NetworkTemplateRenderError("模板内容超过安全大小限制")

    variables = variables or {}
    if not isinstance(variables, Mapping):
        raise NetworkTemplateRenderError("模板变量必须是对象")

    conflicting_keys = RESERVED_CONTEXT_KEYS.intersection(variables.keys())
    if conflicting_keys:
        names = ", ".join(sorted(conflicting_keys))
        raise NetworkTemplateRenderError(f"模板变量不能覆盖系统保留变量: {names}")

    budget = _ContextBudget()
    context = _normalize_value(dict(variables), budget)
    if device is not None:
        context["device"] = _normalize_value(dict(device), budget)

    now_value = datetime.utcnow()
    context["now"] = datetime.utcnow
    context["now_str"] = now_value.strftime("%Y-%m-%d %H:%M:%S")

    try:
        template = _safe_environment().from_string(template_content)
        chunks = []
        rendered_size = 0
        for chunk in template.generate(**context):
            rendered_size += len(chunk.encode("utf-8"))
            if rendered_size > MAX_RENDERED_BYTES:
                raise NetworkTemplateRenderError("模板渲染结果超过安全大小限制")
            chunks.append(chunk)
        rendered = "".join(chunks)
    except NetworkTemplateRenderError:
        raise
    except SecurityError as exc:
        raise NetworkTemplateRenderError("模板包含不安全表达式") from exc
    except TemplateError as exc:
        raise NetworkTemplateRenderError("模板语法或渲染无效") from exc
    except (TypeError, ValueError, OverflowError) as exc:
        raise NetworkTemplateRenderError("模板渲染失败") from exc

    return rendered
