from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.models.employee import Role
from app.services.employee_service import EmployeeService
from app.utils.exceptions import (
    AuthorizationError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)


def make_employee(
    *,
    employee_id: int = 1,
    first_name: str = "Alice",
    last_name: str = "Martin",
    email: str = "alice@example.com",
    role: Role = Role.GESTION,
    password_hash: str = "hashed-password",
):
    """Crée un collaborateur minimal utilisable dans les tests."""
    return SimpleNamespace(
        id=employee_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        role=role,
        password_hash=password_hash,
    )


@pytest.fixture
def session():
    session_mock = Mock()
    session_mock.commit = Mock()
    session_mock.rollback = Mock()
    return session_mock


@pytest.fixture
def service(session):
    employee_service = EmployeeService(session)
    employee_service.repository = Mock()
    return employee_service


# ---------------------------------------------------------------------------
# create_employee
# ---------------------------------------------------------------------------


@patch(
    "app.services.employee_service.hash_password",
    return_value="hashed-secret",
)
def test_create_employee_creates_normalized_employee(
    hash_password_mock,
    service,
    session,
) -> None:
    current_employee = make_employee(role=Role.GESTION)
    service.repository.get_by_email.return_value = None
    service.repository.create.side_effect = lambda employee: employee

    result = service.create_employee(
        current_employee=current_employee,
        first_name="  Jean  ",
        last_name="  Dupont  ",
        email="  JEAN.DUPONT@EXAMPLE.COM  ",
        password="secret-password",
        role=Role.COMMERCIAL,
    )

    assert result.first_name == "Jean"
    assert result.last_name == "Dupont"
    assert result.email == "jean.dupont@example.com"
    assert result.password_hash == "hashed-secret"
    assert result.role == Role.COMMERCIAL

    hash_password_mock.assert_called_once_with("secret-password")
    service.repository.get_by_email.assert_called_once_with(
        "jean.dupont@example.com"
    )
    service.repository.create.assert_called_once_with(result)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_create_employee_requires_management_role(
    service,
    session,
    role,
) -> None:
    current_employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        service.create_employee(
            current_employee=current_employee,
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            password="secret-password",
            role=Role.COMMERCIAL,
        )

    service.repository.get_by_email.assert_not_called()
    service.repository.create.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        ("first_name", "   ", "Le prénom est obligatoire"),
        ("last_name", "   ", "Le nom est obligatoire"),
        ("email", "   ", "L'email est obligatoire"),
        ("password", "", "Le mot de passe est obligatoire"),
    ],
)
def test_create_employee_rejects_missing_required_field(
    service,
    session,
    field_name,
    invalid_value,
    message,
) -> None:
    values = {
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "jean@example.com",
        "password": "secret-password",
        "role": Role.COMMERCIAL,
    }
    values[field_name] = invalid_value

    with pytest.raises(ValidationError, match=message):
        service.create_employee(
            current_employee=make_employee(role=Role.GESTION),
            **values,
        )

    service.repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_create_employee_rejects_duplicate_email(
    service,
    session,
) -> None:
    service.repository.get_by_email.return_value = make_employee(
        employee_id=2,
        email="jean@example.com",
    )

    with pytest.raises(
        DuplicateError,
        match="Un collaborateur utilise déjà cette adresse email",
    ):
        service.create_employee(
            current_employee=make_employee(role=Role.GESTION),
            first_name="Jean",
            last_name="Dupont",
            email=" JEAN@EXAMPLE.COM ",
            password="secret-password",
            role=Role.COMMERCIAL,
        )

    service.repository.get_by_email.assert_called_once_with(
        "jean@example.com"
    )
    service.repository.create.assert_not_called()
    session.commit.assert_not_called()


@patch(
    "app.services.employee_service.hash_password",
    return_value="hashed-secret",
)
def test_create_employee_rolls_back_when_repository_fails(
    hash_password_mock,
    service,
    session,
) -> None:
    service.repository.get_by_email.return_value = None
    service.repository.create.side_effect = RuntimeError(
        "database failure"
    )

    with pytest.raises(RuntimeError, match="database failure"):
        service.create_employee(
            current_employee=make_employee(role=Role.GESTION),
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            password="secret-password",
            role=Role.COMMERCIAL,
        )

    hash_password_mock.assert_called_once_with("secret-password")
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# get_employee
# ---------------------------------------------------------------------------


def test_get_employee_returns_employee(service) -> None:
    current_employee = make_employee(role=Role.GESTION)
    employee = make_employee(employee_id=2)
    service.repository.get_by_id.return_value = employee

    result = service.get_employee(
        current_employee=current_employee,
        employee_id=2,
    )

    assert result is employee
    service.repository.get_by_id.assert_called_once_with(2)


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_get_employee_requires_management_role(
    service,
    role,
) -> None:
    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        service.get_employee(
            current_employee=make_employee(role=role),
            employee_id=2,
        )

    service.repository.get_by_id.assert_not_called()


def test_get_employee_rejects_unknown_employee(service) -> None:
    service.repository.get_by_id.return_value = None

    with pytest.raises(
        NotFoundError,
        match="Collaborateur introuvable",
    ):
        service.get_employee(
            current_employee=make_employee(role=Role.GESTION),
            employee_id=999,
        )


# ---------------------------------------------------------------------------
# list_employees
# ---------------------------------------------------------------------------


def test_list_employees_returns_repository_result(service) -> None:
    current_employee = make_employee(role=Role.GESTION)
    employees = [
        make_employee(employee_id=2, role=Role.COMMERCIAL),
        make_employee(employee_id=3, role=Role.SUPPORT),
    ]
    service.repository.get_all.return_value = employees

    result = service.list_employees(current_employee)

    assert result is employees
    service.repository.get_all.assert_called_once_with()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_list_employees_requires_management_role(
    service,
    role,
) -> None:
    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        service.list_employees(make_employee(role=role))

    service.repository.get_all.assert_not_called()


# ---------------------------------------------------------------------------
# update_employee
# ---------------------------------------------------------------------------


def test_update_employee_updates_all_fields_and_commits(
    service,
    session,
) -> None:
    current_employee = make_employee(
        employee_id=1,
        role=Role.GESTION,
    )
    employee = make_employee(
        employee_id=2,
        first_name="Jean",
        last_name="Dupont",
        email="old@example.com",
        role=Role.COMMERCIAL,
    )

    service.repository.get_by_id.return_value = employee
    service.repository.get_by_email.return_value = None
    service.repository.update.side_effect = lambda value: value

    result = service.update_employee(
        current_employee=current_employee,
        employee_id=employee.id,
        first_name="  Jeanne  ",
        last_name="  Martin  ",
        email="  JEANNE@EXAMPLE.COM  ",
        role=Role.SUPPORT,
    )

    assert result is employee
    assert employee.first_name == "Jeanne"
    assert employee.last_name == "Martin"
    assert employee.email == "jeanne@example.com"
    assert employee.role == Role.SUPPORT

    service.repository.get_by_id.assert_called_once_with(employee.id)
    service.repository.get_by_email.assert_called_once_with(
        "jeanne@example.com"
    )
    service.repository.update.assert_called_once_with(employee)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_update_employee_without_changes_still_updates_and_commits(
    service,
    session,
) -> None:
    employee = make_employee(employee_id=2)
    service.repository.get_by_id.return_value = employee
    service.repository.update.return_value = employee

    result = service.update_employee(
        current_employee=make_employee(role=Role.GESTION),
        employee_id=employee.id,
    )

    assert result is employee
    service.repository.get_by_email.assert_not_called()
    service.repository.update.assert_called_once_with(employee)
    session.commit.assert_called_once_with()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_update_employee_requires_management_role(
    service,
    session,
    role,
) -> None:
    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        service.update_employee(
            current_employee=make_employee(role=role),
            employee_id=2,
            first_name="New Name",
        )

    service.repository.get_by_id.assert_not_called()
    service.repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_employee_rejects_unknown_employee(
    service,
    session,
) -> None:
    service.repository.get_by_id.return_value = None

    with pytest.raises(
        NotFoundError,
        match="Collaborateur introuvable",
    ):
        service.update_employee(
            current_employee=make_employee(role=Role.GESTION),
            employee_id=999,
            first_name="New Name",
        )

    service.repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("field_name", "message"),
    [
        ("first_name", "Le prénom ne peut pas être vide"),
        ("last_name", "Le nom ne peut pas être vide"),
        ("email", "L'email ne peut pas être vide"),
    ],
)
def test_update_employee_rejects_empty_field(
    service,
    session,
    field_name,
    message,
) -> None:
    employee = make_employee(employee_id=2)
    service.repository.get_by_id.return_value = employee

    values = {
        "first_name": None,
        "last_name": None,
        "email": None,
        "role": None,
    }
    values[field_name] = "   "

    with pytest.raises(ValidationError, match=message):
        service.update_employee(
            current_employee=make_employee(role=Role.GESTION),
            employee_id=employee.id,
            **values,
        )

    service.repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_employee_accepts_same_email(
    service,
    session,
) -> None:
    employee = make_employee(
        employee_id=2,
        email="old@example.com",
    )
    service.repository.get_by_id.return_value = employee
    service.repository.get_by_email.return_value = employee
    service.repository.update.return_value = employee

    result = service.update_employee(
        current_employee=make_employee(role=Role.GESTION),
        employee_id=employee.id,
        email=" SAME@EXAMPLE.COM ",
    )

    assert result.email == "same@example.com"
    session.commit.assert_called_once_with()


def test_update_employee_rejects_email_used_by_another_employee(
    service,
    session,
) -> None:
    employee = make_employee(
        employee_id=2,
        email="old@example.com",
    )
    other_employee = make_employee(
        employee_id=3,
        email="taken@example.com",
    )

    service.repository.get_by_id.return_value = employee
    service.repository.get_by_email.return_value = other_employee

    with pytest.raises(
        DuplicateError,
        match="Un collaborateur utilise déjà cette adresse email",
    ):
        service.update_employee(
            current_employee=make_employee(role=Role.GESTION),
            employee_id=employee.id,
            email=" TAKEN@EXAMPLE.COM ",
        )

    service.repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_employee_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    employee = make_employee(employee_id=2)
    service.repository.get_by_id.return_value = employee
    service.repository.update.side_effect = RuntimeError(
        "update failure"
    )

    with pytest.raises(RuntimeError, match="update failure"):
        service.update_employee(
            current_employee=make_employee(role=Role.GESTION),
            employee_id=employee.id,
            first_name="New Name",
        )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# delete_employee
# ---------------------------------------------------------------------------


def test_delete_employee_deletes_and_commits(
    service,
    session,
) -> None:
    current_employee = make_employee(
        employee_id=1,
        role=Role.GESTION,
    )
    employee_to_delete = make_employee(
        employee_id=2,
        role=Role.SUPPORT,
    )
    service.repository.get_by_id.return_value = employee_to_delete

    result = service.delete_employee(
        current_employee=current_employee,
        employee_id=employee_to_delete.id,
    )

    assert result is None
    service.repository.delete.assert_called_once_with(
        employee_to_delete
    )
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_delete_employee_requires_management_role(
    service,
    session,
    role,
) -> None:
    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        service.delete_employee(
            current_employee=make_employee(role=role),
            employee_id=2,
        )

    service.repository.get_by_id.assert_not_called()
    service.repository.delete.assert_not_called()
    session.commit.assert_not_called()


def test_delete_employee_rejects_unknown_employee(
    service,
    session,
) -> None:
    service.repository.get_by_id.return_value = None

    with pytest.raises(
        NotFoundError,
        match="Collaborateur introuvable",
    ):
        service.delete_employee(
            current_employee=make_employee(role=Role.GESTION),
            employee_id=999,
        )

    service.repository.delete.assert_not_called()
    session.commit.assert_not_called()


def test_delete_employee_rejects_self_deletion(
    service,
    session,
) -> None:
    current_employee = make_employee(
        employee_id=1,
        role=Role.GESTION,
    )
    service.repository.get_by_id.return_value = current_employee

    with pytest.raises(
        ValidationError,
        match="Vous ne pouvez pas supprimer votre propre compte",
    ):
        service.delete_employee(
            current_employee=current_employee,
            employee_id=current_employee.id,
        )

    service.repository.delete.assert_not_called()
    session.commit.assert_not_called()


def test_delete_employee_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    current_employee = make_employee(
        employee_id=1,
        role=Role.GESTION,
    )
    employee_to_delete = make_employee(employee_id=2)
    service.repository.get_by_id.return_value = employee_to_delete
    service.repository.delete.side_effect = RuntimeError(
        "delete failure"
    )

    with pytest.raises(RuntimeError, match="delete failure"):
        service.delete_employee(
            current_employee=current_employee,
            employee_id=employee_to_delete.id,
        )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def test_get_existing_employee_returns_employee(service) -> None:
    employee = make_employee(employee_id=2)
    service.repository.get_by_id.return_value = employee

    result = service._get_existing_employee(employee.id)

    assert result is employee
    service.repository.get_by_id.assert_called_once_with(employee.id)


def test_get_existing_employee_raises_not_found(service) -> None:
    service.repository.get_by_id.return_value = None

    with pytest.raises(
        NotFoundError,
        match="Collaborateur introuvable",
    ):
        service._get_existing_employee(999)


def test_require_management_role_accepts_management() -> None:
    employee = make_employee(role=Role.GESTION)

    assert EmployeeService._require_management_role(employee) is None


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_require_management_role_rejects_other_roles(role) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        EmployeeService._require_management_role(employee)