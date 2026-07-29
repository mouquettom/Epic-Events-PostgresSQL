import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Role(enum.Enum):

    COMMERCIAL = 'COMMERCIAL'
    GESTION = 'GESTION'
    SUPPORT = 'SUPPORT'


class Employee(Base):

    __tablename__ = 'employee'

    id: Mapped[int] = mapped_column(primary_key=True)

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[Role] = mapped_column(
        Enum(Role),
        nullable=False,
    )

    clients = relationship('Client', back_populates='commercial')

    contracts = relationship('Contract', back_populates='commercial')

    events = relationship('Event', back_populates='support')

    def __repr__(self) -> str:
        return f"Employee: id={self.id}, email='{self.email}', role='{self.role.value}'"