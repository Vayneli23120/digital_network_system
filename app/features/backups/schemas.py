"""Validated request models for backup operations."""

from pydantic import Field, PositiveInt, RootModel


class BatchBackupRequest(RootModel[list[PositiveInt]]):
    root: list[PositiveInt] = Field(min_length=1, max_length=100)
