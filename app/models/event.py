from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Event(Base):

    __tablename__ = 'event'

    id: Mapped[int] = mapped_column(primary_key=True)

    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    location: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    attendees: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    notes: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    contract_id: Mapped[int] = mapped_column(
        ForeignKey('contract.id'),
        nullable=False,
    )

    support_id: Mapped[int | None] = mapped_column(
        ForeignKey('employee.id'),
        nullable=True,
    )

    contract = relationship('Contract', back_populates='events')

    support = relationship('Employee', back_populates='events')

    def __repr__(self) -> str:
        return f"Event: id={self.id}, location='{self.location}', start_date='{self.start_date}'"