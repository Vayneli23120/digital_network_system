"""Validated request models for maintenance operations."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, condecimal, field_validator

MAX_MAINTENANCE_TEXT_CHARS = 100_000
MAX_MAINTENANCE_JSON_CHARS = 1_000_000

MaintenanceType = Literal["preventive", "corrective", "upgrade", "emergency"]
MaintenancePriority = Literal["P1", "P2", "P3", "P4"]
TransitionStatus = Literal["repairing", "verifying", "completed", "cancelled"]
VerificationResult = Literal["passed", "failed", "partial"]
Money = condecimal(ge=0, max_digits=10, decimal_places=2)
LaborHours = condecimal(ge=0, max_digits=5, decimal_places=2)


class MaintenanceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: int = Field(gt=0)
    device_name: Optional[str] = Field(default=None, max_length=100)
    maint_type: MaintenanceType = "corrective"
    maint_time: Optional[datetime] = None
    parts_replaced: Optional[str] = Field(
        default=None,
        max_length=MAX_MAINTENANCE_JSON_CHARS,
    )
    parts_cost: Optional[Money] = None
    labor_hours: Optional[LaborHours] = None
    labor_cost: Optional[Money] = None
    vendor: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=MAX_MAINTENANCE_TEXT_CHARS)
    post_status: Optional[str] = Field(default=None, max_length=50)
    priority: MaintenancePriority = "P3"
    current_owner: Optional[str] = Field(default=None, max_length=100)
    sla_deadline: Optional[datetime] = None

    def to_record_dict(self) -> dict:
        return self.model_dump(exclude_none=True)


class MaintenanceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: Optional[int] = Field(default=None, gt=0)
    device_name: Optional[str] = Field(default=None, max_length=100)
    maint_type: Optional[MaintenanceType] = None
    maint_time: Optional[datetime] = None
    parts_replaced: Optional[str] = Field(
        default=None,
        max_length=MAX_MAINTENANCE_JSON_CHARS,
    )
    parts_cost: Optional[Money] = None
    labor_hours: Optional[LaborHours] = None
    labor_cost: Optional[Money] = None
    vendor: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=MAX_MAINTENANCE_TEXT_CHARS)
    post_status: Optional[str] = Field(default=None, max_length=50)
    priority: Optional[MaintenancePriority] = None
    current_owner: Optional[str] = Field(default=None, max_length=100)
    sla_deadline: Optional[datetime] = None
    diagnosis_text: Optional[str] = Field(default=None, max_length=MAX_MAINTENANCE_TEXT_CHARS)
    diagnosis_result: Optional[str] = Field(default=None, max_length=50)
    repair_actions: Optional[str] = Field(
        default=None,
        max_length=MAX_MAINTENANCE_JSON_CHARS,
    )
    verification_result: Optional[VerificationResult] = None
    verification_notes: Optional[str] = Field(
        default=None,
        max_length=MAX_MAINTENANCE_TEXT_CHARS,
    )
    verify_passed: Optional[bool] = None

    def to_record_dict(self) -> dict:
        return self.model_dump(exclude_unset=True)


class MaintenanceTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TransitionStatus
    notes: Optional[str] = Field(default=None, max_length=500)


class MaintenanceAssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: str = Field(min_length=1, max_length=100)

    @field_validator("owner")
    @classmethod
    def normalize_owner(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("负责人不能为空")
        return normalized


class MaintenanceWorkNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=1, max_length=500)

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("日志内容不能为空")
        return normalized


class MaintenanceSubmitVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spare_parts: Optional[str] = Field(
        default=None,
        max_length=MAX_MAINTENANCE_JSON_CHARS,
    )
    parts_cost: Optional[Money] = None


class MaintenanceVerifyPassRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verification_notes: Optional[str] = Field(default=None, max_length=10_000)


class MaintenanceStatusContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[TransitionStatus] = None
    repair_actions: Optional[str] = Field(
        default=None,
        max_length=MAX_MAINTENANCE_JSON_CHARS,
    )
    parts_replaced: Optional[str] = Field(
        default=None,
        max_length=MAX_MAINTENANCE_JSON_CHARS,
    )
    spare_parts_list: Optional[str] = Field(
        default=None,
        max_length=MAX_MAINTENANCE_JSON_CHARS,
    )
    verification_result: Optional[VerificationResult] = None
    verification_notes: Optional[str] = Field(default=None, max_length=10_000)
    verify_passed: Optional[bool] = None

    def to_context_dict(self) -> dict:
        return self.model_dump(exclude_none=True)