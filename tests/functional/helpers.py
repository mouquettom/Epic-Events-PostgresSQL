from collections.abc import Iterator

from sqlalchemy.orm import Session, sessionmaker

from app.models.employee import Employee, Role
from app.utils.password import hash_password


def seed_employee(
    session_factory: sessionmaker[Session],
    *,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    role: Role,
) -> Employee:

    session = session_factory()

    try:
        employee = Employee(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=hash_password(password),
            role=role,
        )

        session.add(employee)
        session.commit()
        session.refresh(employee)

        return employee

    finally:
        session.close()


def fake_input(values: list[str]) -> Iterator[str]:
    return iter(values)