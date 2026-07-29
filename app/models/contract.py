from datetime import datetime, UTC
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Contract(Base):

    __tablename__ = 'contract'

    id: Mapped[int] = mapped_column(primary_key=True)

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    remaining_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    is_signed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    client_id: Mapped[int] = mapped_column(
        ForeignKey('client.id'),
        nullable=False,
    )

    commercial_id: Mapped[int] = mapped_column(
        ForeignKey('employee.id'),
        nullable=False,
    )

    client = relationship('Client', back_populates='contracts')

    commercial = relationship('Employee', back_populates='contracts')

    events = relationship('Event', back_populates='contract')

    def __repr__(self):
        return f"Contract: id={self.id}, client_id={self.client_id}, is_signed={self.is_signed}"