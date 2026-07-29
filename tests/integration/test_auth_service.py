import pytest
from sqlalchemy.orm import Session

from app.models.employee import Employee, Role
from app.services.auth_service import AuthService
from app.utils.exceptions import AuthorizationError
from app.utils.password import hash_password
from tests.factories import create_employee


def test_authenticate_returns_valid_token(db_session: Session) -> None:

    employee = Employee(
        first_name="Alice",
        last_name="Martin",
        email="alice@test.com",
        password_hash=hash_password("CorrectPassword123!"),
        role=Role.GESTION,
    )

    db_session.add(employee)
    db_session.flush()

    service = AuthService(db_session)

    token = service.authenticate(
        "alice@test.com",
        "CorrectPassword123!",
    )

    current_employee = service.get_current_employee(token)

    assert isinstance(token, str)
    assert current_employee.id == employee.id
    assert current_employee.email == "alice@test.com"


def test_authenticate_rejects_wrong_password(db_session: Session) -> None:

    employee = Employee(
        first_name="Alice",
        last_name="Martin",
        email="alice@test.com",
        password_hash=hash_password("CorrectPassword123!"),
        role=Role.GESTION,
    )

    db_session.add(employee)
    db_session.flush()

    service = AuthService(db_session)

    with pytest.raises(AuthorizationError):
        service.authenticate(
            "alice@test.com",
            "WrongPassword",
        )


def test_authenticate_rejects_unknown_email(db_session: Session) -> None:

    service = AuthService(db_session)

    with pytest.raises(AuthorizationError):
        service.authenticate(
            "unknown.employee@test.com",
            "Password123!",
        )


def test_get_current_employee_rejects_invalid_token(db_session: Session) -> None:

    service = AuthService(db_session)

    with pytest.raises(AuthorizationError):
        service.get_current_employee("invalid-token")


def test_get_current_employee_rejects_deleted_employee(db_session: Session) -> None:
    employee = create_employee(
        db_session,
        role=Role.GESTION,
        email="deleted.employee@test.com",
        password="Password123!",
    )

    service = AuthService(db_session)

    token = service.authenticate(
        "deleted.employee@test.com",
        "Password123!",
    )

    db_session.delete(employee)
    db_session.commit()

    with pytest.raises(AuthorizationError):
        service.get_current_employee(token)