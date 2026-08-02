"""Validated request models for spare movement operations."""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

MovementType = Literal["in", "out", "scrap_in", "scrap_out"]


class MovementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_id: PositiveInt
    movement_type: MovementType
    quantity: int = Field(gt=0, le=100_000)
    serial_number: Optional[str] = Field(default=None, min_length=1, max_length=100)
    reason: Optional[str] = Field(default=None, max_length=500)
    reference: Optional[str] = Field(default=None, max_length=200)
    target_device_id: Optional[PositiveInt] = None
    source_device_id: Optional[PositiveInt] = None


class SpareMovementInput(MovementCreate):
    """备件动作（批量请求 / 嵌入主记录更新时使用）。"""


class BatchMovementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    movements: List[SpareMovementInput] = Field(min_length=1, max_length=100)
