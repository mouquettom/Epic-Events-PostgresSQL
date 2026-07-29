from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models.employee import Role
from app.services.contract_service import ContractService
from app.utils.exceptions import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)


def make_employee(
    *,
    employee_id: int = 1,
    role: Role = Role.COMMERCIAL,
):
    """Crée un employé minimal pour les tests du service."""
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
):
    """Crée un client minimal pour les tests du service."""
    return SimpleNamespace(
        id=client_id,
        full_name="Jean Dupont",
        email="jean@example.com",
        phone="0102030405",
        company="Epic Corp",
        commercial_id=commercial_id,
    )


def make_contract(
    *,
    contract_id: int = 20,
    client_id: int = 10,
    commercial_id: int = 1,
    total_amount: Decimal = Decimal("1000.00"),
    remaining_amount: Decimal = Decimal("500.00"),
    is_signed: bool = False,
):
    """Crée un contrat minimal pour les tests du service."""
    return SimpleNamespace(
        id=contract_id,
        client_id=client_id,
        commercial_id=commercial_id,
        total_amount=total_amount,
        remaining_amount=remaining_amount,
        is_signed=is_signed,
    )


@pytest.fixture
def session():
    session_mock = Mock()
    session_mock.commit = Mock()
    session_mock.rollback = Mock()
    return session_mock


@pytest.fixture
def service(session):
    contract_service = ContractService(session)
    contract_service.contract_repository = Mock()
    contract_service.client_repository = Mock()
    return contract_service


# ---------------------------------------------------------------------------
# create_contract
# ---------------------------------------------------------------------------


def test_create_contract_creates_normalized_contract(
    service,
    session,
) -> None:
    employee = make_employee(employee_id=1)
    client = make_client(client_id=10, commercial_id=1)

    service.client_repository.get_by_id.return_value = client
    service.contract_repository.create.side_effect = lambda contract: contract

    result = service.create_contract(
        current_employee=employee,
        client_id=client.id,
        total_amount="1000.129",
        remaining_amount=500,
        is_signed=True,
    )

    assert result.client_id == client.id
    assert result.commercial_id == employee.id
    assert result.total_amount == Decimal("1000.13")
    assert result.remaining_amount == Decimal("500.00")
    assert result.is_signed is True

    service.client_repository.get_by_id.assert_called_once_with(client.id)
    service.contract_repository.create.assert_called_once_with(result)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_create_contract_rejects_non_commercial(
    service,
    session,
    role,
) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Seul un commercial peut créer un contrat",
    ):
        service.create_contract(
            current_employee=employee,
            client_id=10,
            total_amount=1000,
            remaining_amount=500,
        )

    service.client_repository.get_by_id.assert_not_called()
    service.contract_repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_create_contract_rejects_unknown_client(
    service,
    session,
) -> None:
    employee = make_employee()
    service.client_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Client introuvable"):
        service.create_contract(
            current_employee=employee,
            client_id=999,
            total_amount=1000,
            remaining_amount=500,
        )

    service.contract_repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_create_contract_rejects_client_owned_by_another_commercial(
    service,
    session,
) -> None:
    employee = make_employee(employee_id=1)
    client = make_client(commercial_id=2)
    service.client_repository.get_by_id.return_value = client

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez créer un contrat que pour vos propres clients",
    ):
        service.create_contract(
            current_employee=employee,
            client_id=client.id,
            total_amount=1000,
            remaining_amount=500,
        )

    service.contract_repository.create.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("total_amount", "remaining_amount", "message"),
    [
        (0, 0, "Le montant total doit être supérieur à zéro"),
        (-1, 0, "Le montant total doit être supérieur à zéro"),
        (100, -1, "Le montant restant ne peut pas être négatif"),
        (100, 101, "Le montant restant ne peut pas dépasser"),
    ],
)
def test_create_contract_rejects_invalid_amount_relationship(
    service,
    session,
    total_amount,
    remaining_amount,
    message,
) -> None:
    employee = make_employee()
    client = make_client(commercial_id=employee.id)
    service.client_repository.get_by_id.return_value = client

    with pytest.raises(ValidationError, match=message):
        service.create_contract(
            current_employee=employee,
            client_id=client.id,
            total_amount=total_amount,
            remaining_amount=remaining_amount,
        )

    service.contract_repository.create.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        ("total_amount", "abc", "Le montant total doit être un nombre valide"),
        (
            "remaining_amount",
            "abc",
            "Le montant restant doit être un nombre valide",
        ),
        ("total_amount", None, "Le montant total doit être un nombre valide"),
        (
            "remaining_amount",
            None,
            "Le montant restant doit être un nombre valide",
        ),
    ],
)
def test_create_contract_rejects_non_numeric_amount(
    service,
    session,
    field_name,
    invalid_value,
    message,
) -> None:
    employee = make_employee()
    client = make_client(commercial_id=employee.id)
    service.client_repository.get_by_id.return_value = client

    values = {
        "total_amount": 1000,
        "remaining_amount": 500,
    }
    values[field_name] = invalid_value

    with pytest.raises(ValidationError, match=message):
        service.create_contract(
            current_employee=employee,
            client_id=client.id,
            **values,
        )

    service.contract_repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_create_contract_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    employee = make_employee()
    client = make_client(commercial_id=employee.id)
    service.client_repository.get_by_id.return_value = client
    service.contract_repository.create.side_effect = RuntimeError("database failure")

    with pytest.raises(RuntimeError, match="database failure"):
        service.create_contract(
            current_employee=employee,
            client_id=client.id,
            total_amount=1000,
            remaining_amount=500,
        )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# get_contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.GESTION, Role.SUPPORT],
)
def test_get_contract_returns_accessible_contract(
    service,
    role,
) -> None:
    employee = make_employee(role=role)
    contract = make_contract(commercial_id=employee.id)
    service.contract_repository.get_by_id.return_value = contract

    result = service.get_contract(employee, contract.id)

    assert result is contract
    service.contract_repository.get_by_id.assert_called_once_with(contract.id)


def test_get_contract_rejects_unknown_contract(service) -> None:
    service.contract_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Contrat introuvable"):
        service.get_contract(make_employee(), 999)


def test_get_contract_rejects_other_commercial_contract(
    service,
) -> None:
    employee = make_employee(employee_id=1)
    contract = make_contract(commercial_id=2)
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez consulter que vos propres contrats",
    ):
        service.get_contract(employee, contract.id)


def test_get_contract_rejects_unknown_role(service) -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"
    contract = make_contract()
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter ce contrat",
    ):
        service.get_contract(employee, contract.id)


# ---------------------------------------------------------------------------
# list_contracts
# ---------------------------------------------------------------------------


def test_list_contracts_returns_only_commercial_contracts(
    service,
) -> None:
    employee = make_employee(employee_id=7, role=Role.COMMERCIAL)
    contracts = [
        make_contract(contract_id=1, commercial_id=7),
        make_contract(contract_id=2, commercial_id=7),
    ]
    service.contract_repository.get_by_commercial_id.return_value = contracts

    result = service.list_contracts(employee)

    assert result is contracts
    service.contract_repository.get_by_commercial_id.assert_called_once_with(7)
    service.contract_repository.get_all.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_list_contracts_returns_all_for_management_and_support(
    service,
    role,
) -> None:
    employee = make_employee(role=role)
    contracts = [make_contract()]
    service.contract_repository.get_all.return_value = contracts

    result = service.list_contracts(employee)

    assert result is contracts
    service.contract_repository.get_all.assert_called_once_with()
    service.contract_repository.get_by_commercial_id.assert_not_called()


def test_list_contracts_rejects_unknown_role(service) -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter les contrats",
    ):
        service.list_contracts(employee)

    service.contract_repository.get_all.assert_not_called()
    service.contract_repository.get_by_commercial_id.assert_not_called()


# ---------------------------------------------------------------------------
# list_unsigned_contracts
# ---------------------------------------------------------------------------


def test_list_unsigned_contracts_returns_repository_result(
    service,
) -> None:
    employee = make_employee(role=Role.GESTION)
    contracts = [make_contract(is_signed=False)]
    service.contract_repository.get_unsigned_contracts.return_value = contracts

    result = service.list_unsigned_contracts(employee)

    assert result is contracts
    service.contract_repository.get_unsigned_contracts.assert_called_once_with()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_list_unsigned_contracts_requires_management(
    service,
    role,
) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        service.list_unsigned_contracts(employee)

    service.contract_repository.get_unsigned_contracts.assert_not_called()


# ---------------------------------------------------------------------------
# list_unpaid_contracts
# ---------------------------------------------------------------------------


def test_list_unpaid_contracts_returns_all_for_management(
    service,
) -> None:
    employee = make_employee(role=Role.GESTION)
    contracts = [
        make_contract(contract_id=1, commercial_id=1),
        make_contract(contract_id=2, commercial_id=2),
    ]
    service.contract_repository.get_unpaid_contracts.return_value = contracts

    result = service.list_unpaid_contracts(employee)

    assert result is contracts
    service.contract_repository.get_unpaid_contracts.assert_called_once_with()


def test_list_unpaid_contracts_filters_for_commercial(
    service,
) -> None:
    employee = make_employee(employee_id=1, role=Role.COMMERCIAL)
    own_contract = make_contract(contract_id=1, commercial_id=1)
    other_contract = make_contract(contract_id=2, commercial_id=2)
    service.contract_repository.get_unpaid_contracts.return_value = [
        own_contract,
        other_contract,
    ]

    result = service.list_unpaid_contracts(employee)

    assert result == [own_contract]


def test_list_unpaid_contracts_rejects_support(service) -> None:
    employee = make_employee(role=Role.SUPPORT)

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter les contrats non soldés",
    ):
        service.list_unpaid_contracts(employee)

    service.contract_repository.get_unpaid_contracts.assert_not_called()


# ---------------------------------------------------------------------------
# update_contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.COMMERCIAL],
)
def test_update_contract_updates_all_fields_and_commits(
    service,
    session,
    role,
) -> None:
    employee = make_employee(employee_id=1, role=role)
    contract = make_contract(commercial_id=1)
    service.contract_repository.get_by_id.return_value = contract
    service.contract_repository.update.side_effect = lambda value: value

    result = service.update_contract(
        current_employee=employee,
        contract_id=contract.id,
        total_amount="2000.555",
        remaining_amount="750.444",
        is_signed=True,
    )

    assert result is contract
    assert contract.total_amount == Decimal("2000.56")
    assert contract.remaining_amount == Decimal("750.44")
    assert contract.is_signed is True

    service.contract_repository.update.assert_called_once_with(contract)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_update_contract_without_values_keeps_existing_data(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.GESTION)
    contract = make_contract(
        total_amount=Decimal("1000.00"),
        remaining_amount=Decimal("500.00"),
        is_signed=False,
    )
    service.contract_repository.get_by_id.return_value = contract
    service.contract_repository.update.return_value = contract

    result = service.update_contract(employee, contract.id)

    assert result is contract
    assert contract.total_amount == Decimal("1000.00")
    assert contract.remaining_amount == Decimal("500.00")
    assert contract.is_signed is False
    session.commit.assert_called_once_with()


def test_update_contract_can_change_only_signature(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.GESTION)
    contract = make_contract(is_signed=False)
    service.contract_repository.get_by_id.return_value = contract
    service.contract_repository.update.return_value = contract

    result = service.update_contract(
        current_employee=employee,
        contract_id=contract.id,
        is_signed=True,
    )

    assert result.is_signed is True
    session.commit.assert_called_once_with()


def test_update_contract_rejects_unknown_contract(
    service,
    session,
) -> None:
    service.contract_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Contrat introuvable"):
        service.update_contract(
            current_employee=make_employee(role=Role.GESTION),
            contract_id=999,
            total_amount=1000,
        )

    service.contract_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_contract_rejects_support_employee(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.SUPPORT)
    contract = make_contract()
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à modifier ce contrat",
    ):
        service.update_contract(employee, contract.id, is_signed=True)

    service.contract_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_contract_rejects_other_commercial_contract(
    service,
    session,
) -> None:
    employee = make_employee(employee_id=1, role=Role.COMMERCIAL)
    contract = make_contract(commercial_id=2)
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à modifier ce contrat",
    ):
        service.update_contract(employee, contract.id, is_signed=True)

    service.contract_repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("total_amount", "remaining_amount", "message"),
    [
        (0, None, "Le montant total doit être supérieur à zéro"),
        (-1, None, "Le montant total doit être supérieur à zéro"),
        (None, -1, "Le montant restant ne peut pas être négatif"),
        (100, 101, "Le montant restant ne peut pas dépasser"),
    ],
)
def test_update_contract_rejects_invalid_amounts(
    service,
    session,
    total_amount,
    remaining_amount,
    message,
) -> None:
    employee = make_employee(role=Role.GESTION)
    contract = make_contract(
        total_amount=Decimal("1000.00"),
        remaining_amount=Decimal("500.00"),
    )
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(ValidationError, match=message):
        service.update_contract(
            current_employee=employee,
            contract_id=contract.id,
            total_amount=total_amount,
            remaining_amount=remaining_amount,
        )

    service.contract_repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        ("total_amount", "invalid", "Le montant total doit être un nombre valide"),
        (
            "remaining_amount",
            "invalid",
            "Le montant restant doit être un nombre valide",
        ),
    ],
)
def test_update_contract_rejects_non_numeric_amounts(
    service,
    session,
    field_name,
    invalid_value,
    message,
) -> None:
    employee = make_employee(role=Role.GESTION)
    contract = make_contract()
    service.contract_repository.get_by_id.return_value = contract

    values = {
        "total_amount": None,
        "remaining_amount": None,
    }
    values[field_name] = invalid_value

    with pytest.raises(ValidationError, match=message):
        service.update_contract(
            current_employee=employee,
            contract_id=contract.id,
            **values,
        )

    service.contract_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_contract_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.GESTION)
    contract = make_contract()
    service.contract_repository.get_by_id.return_value = contract
    service.contract_repository.update.side_effect = RuntimeError("update failure")

    with pytest.raises(RuntimeError, match="update failure"):
        service.update_contract(
            current_employee=employee,
            contract_id=contract.id,
            is_signed=True,
        )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# delete_contract
# ---------------------------------------------------------------------------


def test_delete_contract_deletes_and_commits(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.GESTION)
    contract = make_contract()
    service.contract_repository.get_by_id.return_value = contract

    result = service.delete_contract(employee, contract.id)

    assert result is None
    service.contract_repository.delete.assert_called_once_with(contract)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_delete_contract_requires_management(
    service,
    session,
    role,
) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        service.delete_contract(employee, 20)

    service.contract_repository.get_by_id.assert_not_called()
    service.contract_repository.delete.assert_not_called()
    session.commit.assert_not_called()


def test_delete_contract_rejects_unknown_contract(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.GESTION)
    service.contract_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Contrat introuvable"):
        service.delete_contract(employee, 999)

    service.contract_repository.delete.assert_not_called()
    session.commit.assert_not_called()


def test_delete_contract_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.GESTION)
    contract = make_contract()
    service.contract_repository.get_by_id.return_value = contract
    service.contract_repository.delete.side_effect = RuntimeError("delete failure")

    with pytest.raises(RuntimeError, match="delete failure"):
        service.delete_contract(employee, contract.id)

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def test_get_existing_contract_returns_contract(service) -> None:
    contract = make_contract()
    service.contract_repository.get_by_id.return_value = contract

    result = service._get_existing_contract(contract.id)

    assert result is contract


def test_get_existing_contract_raises_not_found(service) -> None:
    service.contract_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Contrat introuvable"):
        service._get_existing_contract(999)


def test_get_existing_client_returns_client(service) -> None:
    client = make_client()
    service.client_repository.get_by_id.return_value = client

    result = service._get_existing_client(client.id)

    assert result is client


def test_get_existing_client_raises_not_found(service) -> None:
    service.client_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Client introuvable"):
        service._get_existing_client(999)


def test_require_commercial_role_accepts_commercial() -> None:
    employee = make_employee(role=Role.COMMERCIAL)

    assert ContractService._require_commercial_role(employee) is None


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_require_commercial_role_rejects_other_roles(role) -> None:
    employee = make_employee(role=role)

    with pytest.raises(AuthorizationError):
        ContractService._require_commercial_role(employee)


def test_require_management_role_accepts_management() -> None:
    employee = make_employee(role=Role.GESTION)

    assert ContractService._require_management_role(employee) is None


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_require_management_role_rejects_other_roles(role) -> None:
    employee = make_employee(role=role)

    with pytest.raises(AuthorizationError):
        ContractService._require_management_role(employee)


def test_require_client_owner_accepts_owner() -> None:
    employee = make_employee(employee_id=1)
    client = make_client(commercial_id=1)

    assert ContractService._require_client_owner(employee, client) is None


def test_require_client_owner_rejects_wrong_owner() -> None:
    employee = make_employee(employee_id=1)
    client = make_client(commercial_id=2)

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez créer un contrat",
    ):
        ContractService._require_client_owner(employee, client)


def test_require_contract_access_accepts_owner_commercial() -> None:
    employee = make_employee(employee_id=1, role=Role.COMMERCIAL)
    contract = make_contract(commercial_id=1)

    assert ContractService._require_contract_access(employee, contract) is None


def test_require_contract_access_rejects_wrong_commercial() -> None:
    employee = make_employee(employee_id=1, role=Role.COMMERCIAL)
    contract = make_contract(commercial_id=2)

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez consulter que vos propres contrats",
    ):
        ContractService._require_contract_access(employee, contract)


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_require_contract_access_accepts_management_and_support(
    role,
) -> None:
    employee = make_employee(role=role)
    contract = make_contract(commercial_id=999)

    assert ContractService._require_contract_access(employee, contract) is None


def test_require_contract_access_rejects_unknown_role() -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"
    contract = make_contract()

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter ce contrat",
    ):
        ContractService._require_contract_access(employee, contract)


def test_require_contract_update_permission_accepts_management() -> None:
    employee = make_employee(role=Role.GESTION)
    contract = make_contract(commercial_id=999)

    assert (
        ContractService._require_contract_update_permission(
            employee,
            contract,
        )
        is None
    )


def test_require_contract_update_permission_accepts_owner_commercial() -> None:
    employee = make_employee(employee_id=1, role=Role.COMMERCIAL)
    contract = make_contract(commercial_id=1)

    assert (
        ContractService._require_contract_update_permission(
            employee,
            contract,
        )
        is None
    )


@pytest.mark.parametrize(
    ("role", "employee_id", "commercial_id"),
    [
        (Role.COMMERCIAL, 1, 2),
        (Role.SUPPORT, 1, 1),
    ],
)
def test_require_contract_update_permission_rejects_unauthorized(
    role,
    employee_id,
    commercial_id,
) -> None:
    employee = make_employee(employee_id=employee_id, role=role)
    contract = make_contract(commercial_id=commercial_id)

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à modifier ce contrat",
    ):
        ContractService._require_contract_update_permission(
            employee,
            contract,
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("10", Decimal("10.00")),
        (10, Decimal("10.00")),
        (10.1, Decimal("10.10")),
        (Decimal("10.126"), Decimal("10.13")),
        ("0.005", Decimal("0.00")),
    ],
)
def test_normalize_amount_returns_quantized_decimal(
    value,
    expected,
) -> None:
    result = ContractService._normalize_amount(value, "Montant")

    assert result == expected


@pytest.mark.parametrize(
    "value",
    ["abc", None, object()],
)
def test_normalize_amount_rejects_invalid_values(value) -> None:
    with pytest.raises(
        ValidationError,
        match="Montant doit être un nombre valide",
    ):
        ContractService._normalize_amount(value, "Montant")


@pytest.mark.parametrize(
    ("total", "remaining"),
    [
        (Decimal("1.00"), Decimal("0.00")),
        (Decimal("100.00"), Decimal("100.00")),
        (Decimal("100.00"), Decimal("50.00")),
    ],
)
def test_validate_amounts_accepts_valid_values(
    total,
    remaining,
) -> None:
    assert ContractService._validate_amounts(total, remaining) is None


@pytest.mark.parametrize(
    ("total", "remaining", "message"),
    [
        (
            Decimal("0.00"),
            Decimal("0.00"),
            "Le montant total doit être supérieur à zéro",
        ),
        (
            Decimal("-1.00"),
            Decimal("0.00"),
            "Le montant total doit être supérieur à zéro",
        ),
        (
            Decimal("100.00"),
            Decimal("-0.01"),
            "Le montant restant ne peut pas être négatif",
        ),
        (
            Decimal("100.00"),
            Decimal("100.01"),
            "Le montant restant ne peut pas dépasser",
        ),
    ],
)
def test_validate_amounts_rejects_invalid_values(
    total,
    remaining,
    message,
) -> None:
    with pytest.raises(ValidationError, match=message):
        ContractService._validate_amounts(total, remaining)