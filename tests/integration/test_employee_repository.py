from sqlalchemy.orm import Session

from app.models.employee import Employee, Role
from app.repositories.employee_repository import EmployeeRepository
from app.utils.password import hash_password


def test_create_and_find_employee_by_email(db_session: Session) -> None:
    repository = EmployeeRepository(db_session)

    employee = Employee(
        first_name="Alice",
        last_name="Martin",
        email="alice.integration@test.com",
        password_hash=hash_password("Password123!"),
        role=Role.COMMERCIAL,
    )

    created = repository.create(employee)

    found = repository.get_by_email("alice.integration@test.com")

    assert created.id is not None
    assert found is not None
    assert found.id == created.id
    assert found.role == Role.COMMERCIAL


def test_get_all_employees(db_session: Session) -> None:
    repository = EmployeeRepository(db_session)

    repository.create(
        Employee(
            first_name="Alice",
            last_name="Martin",
            email="alice.list@test.com",
            password_hash=hash_password("Password123!"),
            role=Role.COMMERCIAL,
        )
    )

    repository.create(
        Employee(
            first_name="Bob",
            last_name="Durand",
            email="bob.list@test.com",
            password_hash=hash_password("Password123!"),
            role=Role.SUPPORT,
        )
    )

    employees = repository.get_all()

    assert len(employees) >= 2
    assert {
        "alice.list@test.com",
        "bob.list@test.com",
    }.issubset({employee.email for employee in employees})


def test_delete_employee(db_session: Session) -> None:
    repository = EmployeeRepository(db_session)

    employee = repository.create(
        Employee(
            first_name="Alice",
            last_name="Delete",
            email="alice.delete@test.com",
            password_hash=hash_password("Password123!"),
            role=Role.SUPPORT,
        )
    )

    employee_id = employee.id

    repository.delete(employee)

    assert repository.get_by_id(employee_id) is None