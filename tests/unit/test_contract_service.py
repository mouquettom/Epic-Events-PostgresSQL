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
    role: Role = Role.GESTION,
):
    """Crée un collaborateur minimal pour les tests du service."""
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
    commercial_id: int = 3,
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
    commercial_id: int = 3,
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


def test_create_contract_by_management_creates_normalized_contract(
    service,
    session,
) -> None:
    manager = make_employee(
        employee_id=1,
        role=Role.GESTION,
    )
    client = make_client(
        client_id=10,
        commercial_id=7,
    )

    service.client_repository.get_by_id.return_value = client
    service.contract_repository.create.side_effect = lambda contract: contract

    result = service.create_contract(
        current_employee=manager,
        client_id=client.id,
        total_amount="1000.129",
        remaining_amount=500,
        is_signed=True,
    )

    assert result.client_id == client.id
    assert result.commercial_id == client.commercial_id
    assert result.total_amount == Decimal("1000.13")
    assert result.remaining_amount == Decimal("500.00")
    assert result.is_signed is True

    service.client_repository.get_by_id.assert_called_once_with(client.id)
    service.contract_repository.create.assert_called_once_with(result)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_create_contract_requires_management_role(
    service,
    session,
    role,
) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
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
    manager = make_employee(role=Role.GESTION)
    service.client_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Client introuvable"):
        service.create_contract(
            current_employee=manager,
            client_id=999,
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
    manager = make_employee(role=Role.GESTION)
    client = make_client()
    service.client_repository.get_by_id.return_value = client

    with pytest.raises(ValidationError, match=message):
        service.create_contract(
            current_employee=manager,
            client_id=client.id,
            total_amount=total_amount,
            remaining_amount=remaining_amount,
        )

    service.contract_repository.create.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        (
            "total_amount",
            "abc",
            "Le montant total doit être un nombre valide",
        ),
        (
            "remaining_amount",
            "abc",
            "Le montant restant doit être un nombre valide",
        ),
        (
            "total_amount",
            None,
            "Le montant total doit être un nombre valide",
        ),
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
    manager = make_employee(role=Role.GESTION)
    client = make_client()
    service.client_repository.get_by_id.return_value = client

    values = {
        "total_amount": 1000,
        "remaining_amount": 500,
    }
    values[field_name] = invalid_value

    with pytest.raises(ValidationError, match=message):
        service.create_contract(
            current_employee=manager,
            client_id=client.id,
            **values,
        )

    service.contract_repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_create_contract_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    manager = make_employee(role=Role.GESTION)
    client = make_client()

    service.client_repository.get_by_id.return_value = client
    service.contract_repository.create.side_effect = RuntimeError(
        "database failure"
    )

    with pytest.raises(RuntimeError, match="database failure"):
        service.create_contract(
            current_employee=manager,
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
    [Role.GESTION, Role.COMMERCIAL, Role.SUPPORT],
)
def test_get_contract_is_available_to_all_valid_roles(
    service,
    role,
) -> None:
    employee = make_employee(role=role)
    contract = make_contract(commercial_id=999)
    service.contract_repository.get_by_id.return_value = contract

    result = service.get_contract(
        current_employee=employee,
        contract_id=contract.id,
    )

    assert result is contract
    service.contract_repository.get_by_id.assert_called_once_with(
        contract.id
    )


def test_get_contract_allows_commercial_to_view_another_contract(
    service,
) -> None:
    commercial = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    contract = make_contract(commercial_id=2)
    service.contract_repository.get_by_id.return_value = contract

    result = service.get_contract(
        current_employee=commercial,
        contract_id=contract.id,
    )

    assert result is contract


def test_get_contract_rejects_unknown_contract(service) -> None:
    service.contract_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Contrat introuvable"):
        service.get_contract(
            current_employee=make_employee(),
            contract_id=999,
        )


def test_get_contract_rejects_unknown_role_before_repository_lookup(
    service,
) -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter les contrats",
    ):
        service.get_contract(
            current_employee=employee,
            contract_id=20,
        )

    service.contract_repository.get_by_id.assert_not_called()


# ---------------------------------------------------------------------------
# list_contracts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.COMMERCIAL, Role.SUPPORT],
)
def test_list_contracts_returns_all_contracts_for_valid_roles(
    service,
    role,
) -> None:
    employee = make_employee(role=role)
    contracts = [
        make_contract(contract_id=1, commercial_id=1),
        make_contract(contract_id=2, commercial_id=2),
    ]
    service.contract_repository.get_all.return_value = contracts

    result = service.list_contracts(employee)

    assert result is contracts
    service.contract_repository.get_all.assert_called_once_with()


def test_list_contracts_rejects_unknown_role(service) -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter les contrats",
    ):
        service.list_contracts(employee)

    service.contract_repository.get_all.assert_not_called()


# ---------------------------------------------------------------------------
# list_unsigned_contracts
# ---------------------------------------------------------------------------


def test_list_unsigned_contracts_filters_for_connected_commercial(
    service,
) -> None:
    commercial = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    own_contract = make_contract(
        contract_id=1,
        commercial_id=1,
        is_signed=False,
    )
    other_contract = make_contract(
        contract_id=2,
        commercial_id=2,
        is_signed=False,
    )

    service.contract_repository.get_unsigned_contracts.return_value = [
        own_contract,
        other_contract,
    ]

    result = service.list_unsigned_contracts(commercial)

    assert result == [own_contract]
    service.contract_repository.get_unsigned_contracts.assert_called_once_with()


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_list_unsigned_contracts_requires_commercial_role(
    service,
    role,
) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service commercial",
    ):
        service.list_unsigned_contracts(employee)

    service.contract_repository.get_unsigned_contracts.assert_not_called()


# ---------------------------------------------------------------------------
# list_unpaid_contracts
# ---------------------------------------------------------------------------


def test_list_unpaid_contracts_filters_for_connected_commercial(
    service,
) -> None:
    commercial = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    own_contract = make_contract(
        contract_id=1,
        commercial_id=1,
        remaining_amount=Decimal("400.00"),
    )
    other_contract = make_contract(
        contract_id=2,
        commercial_id=2,
        remaining_amount=Decimal("300.00"),
    )

    service.contract_repository.get_unpaid_contracts.return_value = [
        own_contract,
        other_contract,
    ]

    result = service.list_unpaid_contracts(commercial)

    assert result == [own_contract]
    service.contract_repository.get_unpaid_contracts.assert_called_once_with()


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_list_unpaid_contracts_requires_commercial_role(
    service,
    role,
) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service commercial",
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
    employee = make_employee(
        employee_id=1,
        role=role,
    )
    commercial_id = (
        employee.id
        if role == Role.COMMERCIAL
        else 999
    )
    contract = make_contract(
        commercial_id=commercial_id,
    )

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


def test_management_can_update_any_contract(
    service,
    session,
) -> None:
    manager = make_employee(
        employee_id=1,
        role=Role.GESTION,
    )
    contract = make_contract(commercial_id=999)

    service.contract_repository.get_by_id.return_value = contract
    service.contract_repository.update.return_value = contract

    result = service.update_contract(
        current_employee=manager,
        contract_id=contract.id,
        is_signed=True,
    )

    assert result is contract
    assert result.is_signed is True
    session.commit.assert_called_once_with()


def test_commercial_can_update_own_contract(
    service,
    session,
) -> None:
    commercial = make_employee(
        employee_id=4,
        role=Role.COMMERCIAL,
    )
    contract = make_contract(commercial_id=4)

    service.contract_repository.get_by_id.return_value = contract
    service.contract_repository.update.return_value = contract

    result = service.update_contract(
        current_employee=commercial,
        contract_id=contract.id,
        remaining_amount=250,
    )

    assert result.remaining_amount == Decimal("250.00")
    session.commit.assert_called_once_with()


def test_update_contract_without_values_keeps_existing_data(
    service,
    session,
) -> None:
    manager = make_employee(role=Role.GESTION)
    contract = make_contract(
        total_amount=Decimal("1000.00"),
        remaining_amount=Decimal("500.00"),
        is_signed=False,
    )

    service.contract_repository.get_by_id.return_value = contract
    service.contract_repository.update.return_value = contract

    result = service.update_contract(
        current_employee=manager,
        contract_id=contract.id,
    )

    assert result is contract
    assert contract.total_amount == Decimal("1000.00")
    assert contract.remaining_amount == Decimal("500.00")
    assert contract.is_signed is False
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
    support = make_employee(role=Role.SUPPORT)
    contract = make_contract()
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à modifier ce contrat",
    ):
        service.update_contract(
            current_employee=support,
            contract_id=contract.id,
            is_signed=True,
        )

    service.contract_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_contract_rejects_another_commercial_contract(
    service,
    session,
) -> None:
    commercial = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    contract = make_contract(commercial_id=2)
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à modifier ce contrat",
    ):
        service.update_contract(
            current_employee=commercial,
            contract_id=contract.id,
            is_signed=True,
        )

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
    manager = make_employee(role=Role.GESTION)
    contract = make_contract(
        total_amount=Decimal("1000.00"),
        remaining_amount=Decimal("500.00"),
    )
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(ValidationError, match=message):
        service.update_contract(
            current_employee=manager,
            contract_id=contract.id,
            total_amount=total_amount,
            remaining_amount=remaining_amount,
        )

    service.contract_repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        (
            "total_amount",
            "invalid",
            "Le montant total doit être un nombre valide",
        ),
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
    manager = make_employee(role=Role.GESTION)
    contract = make_contract()
    service.contract_repository.get_by_id.return_value = contract

    values = {
        "total_amount": None,
        "remaining_amount": None,
    }
    values[field_name] = invalid_value

    with pytest.raises(ValidationError, match=message):
        service.update_contract(
            current_employee=manager,
            contract_id=contract.id,
            **values,
        )

    service.contract_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_contract_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    manager = make_employee(role=Role.GESTION)
    contract = make_contract()
    service.contract_repository.get_by_id.return_value = contract
    service.contract_repository.update.side_effect = RuntimeError(
        "update failure"
    )

    with pytest.raises(RuntimeError, match="update failure"):
        service.update_contract(
            current_employee=manager,
            contract_id=contract.id,
            is_signed=True,
        )

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
    service.contract_repository.get_by_id.assert_called_once_with(
        contract.id
    )


def test_get_existing_contract_raises_not_found(service) -> None:
    service.contract_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Contrat introuvable"):
        service._get_existing_contract(999)


def test_get_existing_client_returns_client(service) -> None:
    client = make_client()
    service.client_repository.get_by_id.return_value = client

    result = service._get_existing_client(client.id)

    assert result is client
    service.client_repository.get_by_id.assert_called_once_with(client.id)


def test_get_existing_client_raises_not_found(service) -> None:
    service.client_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Client introuvable"):
        service._get_existing_client(999)


def test_require_management_role_accepts_management() -> None:
    employee = make_employee(role=Role.GESTION)

    assert ContractService._require_management_role(employee) is None


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
        ContractService._require_management_role(employee)


def test_require_commercial_role_accepts_commercial() -> None:
    employee = make_employee(role=Role.COMMERCIAL)

    assert ContractService._require_commercial_role(employee) is None


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_require_commercial_role_rejects_other_roles(role) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service commercial",
    ):
        ContractService._require_commercial_role(employee)


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.COMMERCIAL, Role.SUPPORT],
)
def test_require_valid_role_accepts_application_roles(role) -> None:
    employee = make_employee(role=role)

    assert ContractService._require_valid_role(employee) is None


def test_require_valid_role_rejects_unknown_role() -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter les contrats",
    ):
        ContractService._require_valid_role(employee)


def test_require_contract_update_permission_accepts_management() -> None:
    manager = make_employee(role=Role.GESTION)
    contract = make_contract(commercial_id=999)

    assert (
        ContractService._require_contract_update_permission(
            manager,
            contract,
        )
        is None
    )


def test_require_contract_update_permission_accepts_owner_commercial() -> None:
    commercial = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    contract = make_contract(commercial_id=1)

    assert (
        ContractService._require_contract_update_permission(
            commercial,
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
    employee = make_employee(
        employee_id=employee_id,
        role=role,
    )
    contract = make_contract(
        commercial_id=commercial_id,
    )

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
    result = ContractService._normalize_amount(
        value,
        "Montant",
    )

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
        ContractService._normalize_amount(
            value,
            "Montant",
        )


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
    assert (
        ContractService._validate_amounts(
            total_amount=total,
            remaining_amount=remaining,
        )
        is None
    )


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
            Decimal("-1.00"),
            "Le montant restant ne peut pas être négatif",
        ),
        (
            Decimal("100.00"),
            Decimal("101.00"),
            "Le montant restant ne peut pas dépasser",
        ),
    ],
)
def test_validate_amounts_rejects_invalid_values(
    total,
    remaining,
    message,
) -> None:
    with pytest.raises(
        ValidationError,
        match=message,
    ):
        ContractService._validate_amounts(
            total_amount=total,
            remaining_amount=remaining,
        )