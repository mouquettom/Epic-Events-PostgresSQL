from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models.employee import Role
from app.services.client_service import ClientService
from app.utils.exceptions import (
    AuthorizationError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)


def make_employee(
    *,
    employee_id: int = 1,
    role: Role = Role.COMMERCIAL,
):
    """ Crée un employé minimal utilisable par ClientService. """
    return SimpleNamespace(
        id=employee_id,
        first_name="Alice",
        last_name="Martin",
        email="alice@example.com",
        role=role,
    )


def make_client(
    *,
    client_id: int = 10,
    commercial_id: int = 1,
    full_name: str = "Jean Dupont",
    email: str = "jean@example.com",
    phone: str = "0102030405",
    company: str = "Epic Corp",
):
    """Crée un client minimal utilisable par ClientService."""
    return SimpleNamespace(
        id=client_id,
        commercial_id=commercial_id,
        full_name=full_name,
        email=email,
        phone=phone,
        company=company,
    )


@pytest.fixture
def session():
    session_mock = Mock()
    session_mock.commit = Mock()
    session_mock.rollback = Mock()
    return session_mock


@pytest.fixture
def service(session):
    client_service = ClientService(session)
    client_service.repository = Mock()
    return client_service


# ---------------------------------------------------------------------------
# create_client
# ---------------------------------------------------------------------------


def test_create_client_creates_normalized_client(
    service,
    session,
) -> None:
    employee = make_employee()
    service.repository.get_by_email.return_value = None
    service.repository.create.side_effect = lambda client: client

    result = service.create_client(
        current_employee=employee,
        full_name="  Jean Dupont  ",
        email="  JEAN@EXAMPLE.COM  ",
        phone="  01 02 03 04 05  ",
        company="  Epic Corp  ",
    )

    assert result.full_name == "Jean Dupont"
    assert result.email == "jean@example.com"
    assert result.phone == "01 02 03 04 05"
    assert result.company == "Epic Corp"
    assert result.commercial_id == employee.id

    service.repository.get_by_email.assert_called_once_with("jean@example.com")
    service.repository.create.assert_called_once_with(result)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_create_client_rejects_non_commercial_employee(
    service,
    session,
    role,
) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Seul un commercial peut créer un client",
    ):
        service.create_client(
            current_employee=employee,
            full_name="Jean Dupont",
            email="jean@example.com",
            phone="0102030405",
            company="Epic Corp",
        )

    service.repository.get_by_email.assert_not_called()
    service.repository.create.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        ("full_name", "   ", "Le nom du client est obligatoire"),
        ("email", "   ", "L'email du client est obligatoire"),
        ("phone", "   ", "Le téléphone du client est obligatoire"),
        ("company", "   ", "L'entreprise du client est obligatoire"),
    ],
)
def test_create_client_rejects_empty_required_field(
    service,
    session,
    field_name,
    invalid_value,
    message,
) -> None:
    employee = make_employee()
    values = {
        "full_name": "Jean Dupont",
        "email": "jean@example.com",
        "phone": "0102030405",
        "company": "Epic Corp",
    }
    values[field_name] = invalid_value

    with pytest.raises(ValidationError, match=message):
        service.create_client(
            current_employee=employee,
            **values,
        )

    service.repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_create_client_rejects_duplicate_email(
    service,
    session,
) -> None:
    employee = make_employee()
    service.repository.get_by_email.return_value = make_client()

    with pytest.raises(
        DuplicateError,
        match="Un client utilise déjà cette adresse email",
    ):
        service.create_client(
            current_employee=employee,
            full_name="Jean Dupont",
            email=" JEAN@EXAMPLE.COM ",
            phone="0102030405",
            company="Epic Corp",
        )

    service.repository.get_by_email.assert_called_once_with("jean@example.com")
    service.repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_create_client_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    employee = make_employee()
    service.repository.get_by_email.return_value = None
    service.repository.create.side_effect = RuntimeError("database failure")

    with pytest.raises(RuntimeError, match="database failure"):
        service.create_client(
            current_employee=employee,
            full_name="Jean Dupont",
            email="jean@example.com",
            phone="0102030405",
            company="Epic Corp",
        )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# get_client
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.GESTION, Role.SUPPORT],
)
def test_get_client_returns_accessible_client(
    service,
    role,
) -> None:
    employee = make_employee(role=role)
    client = make_client(commercial_id=employee.id)
    service.repository.get_by_id.return_value = client

    result = service.get_client(employee, client.id)

    assert result is client
    service.repository.get_by_id.assert_called_once_with(client.id)


def test_get_client_rejects_unknown_client(service) -> None:
    employee = make_employee()
    service.repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Client introuvable"):
        service.get_client(employee, 999)

    service.repository.get_by_id.assert_called_once_with(999)


def test_get_client_rejects_commercial_access_to_another_owner(
    service,
) -> None:
    employee = make_employee(employee_id=1)
    client = make_client(commercial_id=2)
    service.repository.get_by_id.return_value = client

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez consulter que vos propres clients",
    ):
        service.get_client(employee, client.id)


def test_get_client_rejects_unknown_role(service) -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"
    client = make_client()
    service.repository.get_by_id.return_value = client

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter ce client",
    ):
        service.get_client(employee, client.id)


# ---------------------------------------------------------------------------
# list_clients
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.GESTION, Role.SUPPORT],
)
def test_list_clients_returns_repository_clients(
    service,
    role,
) -> None:
    employee = make_employee(role=role)
    clients = [make_client(client_id=1), make_client(client_id=2)]
    service.repository.get_all.return_value = clients

    result = service.list_clients(employee)

    assert result is clients
    service.repository.get_all.assert_called_once_with()


def test_list_clients_rejects_unknown_role(service) -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter les clients",
    ):
        service.list_clients(employee)

    service.repository.get_all.assert_not_called()


# ---------------------------------------------------------------------------
# update_client
# ---------------------------------------------------------------------------


def test_update_client_updates_all_fields_and_commits(
    service,
    session,
) -> None:
    employee = make_employee()
    client = make_client(commercial_id=employee.id)
    service.repository.get_by_id.return_value = client
    service.repository.get_by_email.return_value = None
    service.repository.update.side_effect = lambda value: value

    result = service.update_client(
        current_employee=employee,
        client_id=client.id,
        full_name="  Jeanne Martin  ",
        email="  JEANNE@EXAMPLE.COM  ",
        phone="  0600000000  ",
        company="  New Company  ",
    )

    assert result is client
    assert client.full_name == "Jeanne Martin"
    assert client.email == "jeanne@example.com"
    assert client.phone == "0600000000"
    assert client.company == "New Company"

    service.repository.get_by_id.assert_called_once_with(client.id)
    service.repository.get_by_email.assert_called_once_with("jeanne@example.com")
    service.repository.update.assert_called_once_with(client)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_update_client_without_changes_still_persists_client(
    service,
    session,
) -> None:
    employee = make_employee()
    client = make_client(commercial_id=employee.id)
    service.repository.get_by_id.return_value = client
    service.repository.update.return_value = client

    result = service.update_client(
        current_employee=employee,
        client_id=client.id,
    )

    assert result is client
    service.repository.get_by_email.assert_not_called()
    service.repository.update.assert_called_once_with(client)
    session.commit.assert_called_once_with()


def test_update_client_accepts_same_client_email(
    service,
    session,
) -> None:
    employee = make_employee()
    client = make_client(
        client_id=10,
        commercial_id=employee.id,
        email="old@example.com",
    )
    service.repository.get_by_id.return_value = client
    service.repository.get_by_email.return_value = client
    service.repository.update.return_value = client

    result = service.update_client(
        current_employee=employee,
        client_id=client.id,
        email=" SAME@EXAMPLE.COM ",
    )

    assert result is client
    assert client.email == "same@example.com"
    session.commit.assert_called_once_with()


def test_update_client_rejects_unknown_client(
    service,
    session,
) -> None:
    service.repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Client introuvable"):
        service.update_client(
            current_employee=make_employee(),
            client_id=999,
            full_name="New Name",
        )

    service.repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_update_client_rejects_non_commercial_employee(
    service,
    session,
    role,
) -> None:
    employee = make_employee(role=role)
    client = make_client(commercial_id=employee.id)
    service.repository.get_by_id.return_value = client

    with pytest.raises(
        AuthorizationError,
        match="Seul un commercial peut modifier un client",
    ):
        service.update_client(
            current_employee=employee,
            client_id=client.id,
            full_name="New Name",
        )

    service.repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_client_rejects_another_commercial_client(
    service,
    session,
) -> None:
    employee = make_employee(employee_id=1)
    client = make_client(commercial_id=2)
    service.repository.get_by_id.return_value = client

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez modifier que vos propres clients",
    ):
        service.update_client(
            current_employee=employee,
            client_id=client.id,
            full_name="New Name",
        )

    service.repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("field_name", "message"),
    [
        ("full_name", "Le nom du client ne peut pas être vide"),
        ("email", "L'email du client ne peut pas être vide"),
        ("phone", "Le téléphone du client ne peut pas être vide"),
        ("company", "L'entreprise du client ne peut pas être vide"),
    ],
)
def test_update_client_rejects_empty_field(
    service,
    session,
    field_name,
    message,
) -> None:
    employee = make_employee()
    client = make_client(commercial_id=employee.id)
    service.repository.get_by_id.return_value = client

    values = {
        "full_name": None,
        "email": None,
        "phone": None,
        "company": None,
    }
    values[field_name] = "   "

    with pytest.raises(ValidationError, match=message):
        service.update_client(
            current_employee=employee,
            client_id=client.id,
            **values,
        )

    service.repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_client_rejects_email_used_by_another_client(
    service,
    session,
) -> None:
    employee = make_employee()
    client = make_client(
        client_id=10,
        commercial_id=employee.id,
    )
    other_client = make_client(
        client_id=20,
        commercial_id=employee.id,
        email="taken@example.com",
    )
    service.repository.get_by_id.return_value = client
    service.repository.get_by_email.return_value = other_client

    with pytest.raises(
        DuplicateError,
        match="Un client utilise déjà cette adresse email",
    ):
        service.update_client(
            current_employee=employee,
            client_id=client.id,
            email=" TAKEN@EXAMPLE.COM ",
        )

    service.repository.get_by_email.assert_called_once_with("taken@example.com")
    service.repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_client_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    employee = make_employee()
    client = make_client(commercial_id=employee.id)
    service.repository.get_by_id.return_value = client
    service.repository.update.side_effect = RuntimeError("update failure")

    with pytest.raises(RuntimeError, match="update failure"):
        service.update_client(
            current_employee=employee,
            client_id=client.id,
            full_name="New Name",
        )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# delete_client
# ---------------------------------------------------------------------------


def test_delete_client_deletes_owned_client_and_commits(
    service,
    session,
) -> None:
    employee = make_employee()
    client = make_client(commercial_id=employee.id)
    service.repository.get_by_id.return_value = client

    result = service.delete_client(employee, client.id)

    assert result is None
    service.repository.delete.assert_called_once_with(client)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_delete_client_rejects_unknown_client(
    service,
    session,
) -> None:
    service.repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Client introuvable"):
        service.delete_client(make_employee(), 999)

    service.repository.delete.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_delete_client_rejects_non_commercial_employee(
    service,
    session,
    role,
) -> None:
    employee = make_employee(role=role)
    client = make_client(commercial_id=employee.id)
    service.repository.get_by_id.return_value = client

    with pytest.raises(
        AuthorizationError,
        match="Seul un commercial peut modifier un client",
    ):
        service.delete_client(employee, client.id)

    service.repository.delete.assert_not_called()
    session.commit.assert_not_called()


def test_delete_client_rejects_another_commercial_client(
    service,
    session,
) -> None:
    employee = make_employee(employee_id=1)
    client = make_client(commercial_id=2)
    service.repository.get_by_id.return_value = client

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez modifier que vos propres clients",
    ):
        service.delete_client(employee, client.id)

    service.repository.delete.assert_not_called()
    session.commit.assert_not_called()


def test_delete_client_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    employee = make_employee()
    client = make_client(commercial_id=employee.id)
    service.repository.get_by_id.return_value = client
    service.repository.delete.side_effect = RuntimeError("delete failure")

    with pytest.raises(RuntimeError, match="delete failure"):
        service.delete_client(employee, client.id)

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# Private business-rule helpers
# ---------------------------------------------------------------------------


def test_get_existing_client_returns_client(service) -> None:
    client = make_client()
    service.repository.get_by_id.return_value = client

    result = service._get_existing_client(client.id)

    assert result is client


def test_get_existing_client_raises_not_found(service) -> None:
    service.repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Client introuvable"):
        service._get_existing_client(999)


def test_require_commercial_role_accepts_commercial() -> None:
    employee = make_employee(role=Role.COMMERCIAL)

    assert ClientService._require_commercial_role(employee) is None


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_require_commercial_role_rejects_other_roles(role) -> None:
    employee = make_employee(role=role)

    with pytest.raises(AuthorizationError):
        ClientService._require_commercial_role(employee)


def test_require_client_owner_accepts_owner() -> None:
    employee = make_employee(employee_id=1)
    client = make_client(commercial_id=1)

    assert ClientService._require_client_owner(employee, client) is None


def test_require_client_owner_rejects_non_commercial() -> None:
    employee = make_employee(role=Role.GESTION)
    client = make_client(commercial_id=employee.id)

    with pytest.raises(
        AuthorizationError,
        match="Seul un commercial peut modifier un client",
    ):
        ClientService._require_client_owner(employee, client)


def test_require_client_owner_rejects_wrong_owner() -> None:
    employee = make_employee(employee_id=1)
    client = make_client(commercial_id=2)

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez modifier que vos propres clients",
    ):
        ClientService._require_client_owner(employee, client)


def test_require_client_access_accepts_owner_commercial() -> None:
    employee = make_employee(employee_id=1)
    client = make_client(commercial_id=1)

    assert ClientService._require_client_access(employee, client) is None


def test_require_client_access_rejects_wrong_commercial() -> None:
    employee = make_employee(employee_id=1)
    client = make_client(commercial_id=2)

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez consulter que vos propres clients",
    ):
        ClientService._require_client_access(employee, client)


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_require_client_access_accepts_management_and_support(
    role,
) -> None:
    employee = make_employee(role=role)
    client = make_client(commercial_id=999)

    assert ClientService._require_client_access(employee, client) is None


def test_require_client_access_rejects_unknown_role() -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"
    client = make_client()

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter ce client",
    ):
        ClientService._require_client_access(employee, client)