from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, event
from sqlmodel import Field, SQLModel

SQLModel.metadata.naming_convention = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}


class IDMixin:
    id: UUID = Field(primary_key=True, default_factory=uuid4)


class TimestampMixin:
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        sa_type=DateTime(timezone=True),
        nullable=False,
    )


@event.listens_for(TimestampMixin, "before_update", propagate=True)
def _set_updated_at(_mapper: object, _connection: object, target: TimestampMixin) -> None:
    target.updated_at = datetime.now(tz=UTC)


@event.listens_for(SQLModel, "load", propagate=True)
def _init_pydantic_extra(target: SQLModel, _context: object) -> None:
    if target.__pydantic_extra__ is None:
        object.__setattr__(target, "__pydantic_extra__", {})
