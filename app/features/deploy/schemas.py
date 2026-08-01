"""Deploy API 与 WebSocket 的请求模型。"""

from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    PositiveInt,
    field_validator,
    model_validator,
)

DeployMode = Literal["backup", "template", "snippet"]
DeployEngine = Literal["napalm", "netmiko"]
NapalmMode = Literal["merge", "replace"]
TransferMode = Literal["inline", "scp"]
SnippetPosition = Literal["smart", "append", "prepend", "replace"]


class DeployRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: DeployMode = "backup"
    engine: DeployEngine = "napalm"
    napalm_mode: NapalmMode = "merge"
    transfer_mode: TransferMode = "inline"
    backup_file: Optional[str] = Field(default=None, max_length=1024)
    template_id: Optional[PositiveInt] = None
    snippet: Optional[str] = Field(default=None, max_length=1_000_000)
    snippet_position: SnippetPosition = "append"
    base_backup_file: Optional[str] = Field(default=None, max_length=1024)
    target_devices: list[PositiveInt] = Field(min_length=1, max_length=100)
    variables: dict[str, JsonValue] = Field(default_factory=dict)
    dry_run: bool = False
    parallel_limit: int = Field(default=1, ge=1, le=5)
    parent_id: Optional[PositiveInt] = None

    @field_validator(
        "backup_file",
        "template_id",
        "snippet",
        "base_backup_file",
        mode="before",
    )
    @classmethod
    def normalize_empty_optional_fields(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_mode_source(self):
        if len(self.variables) > 500:
            raise ValueError("模板变量数量超过限制")
        if any(len(key) > 128 for key in self.variables):
            raise ValueError("模板变量名超过长度限制")
        if self.mode == "backup" and not self.backup_file:
            raise ValueError("backup 模式必须提供 backup_file")
        if self.mode == "template" and self.template_id is None:
            raise ValueError("template 模式必须提供 template_id")
        if self.mode == "snippet" and not (self.snippet or "").strip():
            raise ValueError("snippet 模式必须提供非空 snippet")
        return self


class WebSocketDeployRequest(DeployRequest):
    action: Literal["start_deploy"]
    engine: DeployEngine = "netmiko"
    access_token: Optional[str] = Field(default=None, min_length=1, max_length=8192)


class RollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_devices: list[PositiveInt] = Field(min_length=1, max_length=100)
    parent_id: Optional[PositiveInt] = None


class ScheduleDeployRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_id: str = Field(pattern=r"^\d{8}_(morning|afternoon|evening)$")
    deploy_data: DeployRequest
