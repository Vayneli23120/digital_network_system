"""Validated request models for configuration templates."""

import json
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, JsonValue, RootModel, field_validator

MAX_TEMPLATE_CONTENT_CHARS = 1_000_000
MAX_TEMPLATE_VARIABLES_BYTES = 100_000


def _serialize_variables(value: JsonValue) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if len(serialized.encode("utf-8")) > MAX_TEMPLATE_VARIABLES_BYTES:
        raise ValueError("模板变量定义超过大小限制")
    return serialized


class TemplateCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=10_000)
    template_content: str = Field(min_length=1, max_length=MAX_TEMPLATE_CONTENT_CHARS)
    variables: JsonValue = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("模板名称不能为空")
        return normalized

    @field_validator("variables", mode="before")
    @classmethod
    def parse_variables(cls, value):
        if value in (None, ""):
            return {}
        if isinstance(value, str):
            if len(value.encode("utf-8")) > MAX_TEMPLATE_VARIABLES_BYTES:
                raise ValueError("模板变量定义超过大小限制")
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError("模板变量定义必须是有效 JSON") from exc
        if not isinstance(value, (dict, list)):
            raise ValueError("模板变量定义必须是 JSON 对象或数组")
        _serialize_variables(value)
        return value

    def to_service_dict(self) -> dict:
        data = self.model_dump()
        data["variables"] = _serialize_variables(data["variables"])
        return data


class TemplateUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=10_000)
    template_content: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=MAX_TEMPLATE_CONTENT_CHARS,
    )
    variables: Optional[JsonValue] = None

    _normalize_name = field_validator("name")(TemplateCreateRequest.normalize_name.__func__)
    _parse_variables = field_validator("variables", mode="before")(
        TemplateCreateRequest.parse_variables.__func__
    )

    def to_service_dict(self) -> dict:
        data = self.model_dump(exclude_unset=True)
        if "variables" in data:
            data["variables"] = _serialize_variables(data["variables"])
        return data


class TemplateRenderRequest(RootModel[dict[str, JsonValue]]):
    root: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("root")
    @classmethod
    def validate_size(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        _serialize_variables(value)
        return value
