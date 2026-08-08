from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.controllers.contract_controller import ContractController
from app.models.contract import Contract
from app.models.employee import Employee, Role
from app.session.current_session import CurrentSession
from app.utils.exceptions import AuthorizationError, NotFoundError


def create_current_session(
    role: Role = Role.GESTION,
) -> tuple[CurrentSession, Employee]:
    """Crée une session contenant un collaborateur connecté."""
    employee = Mock(spec=Employee)
    employee.id = 1
    employee.first_name = "Alice"
    employee.last_name = "Martin"
    employee.email = "alice@test.com"
    employee.role = role

    current_session = CurrentSession()
    current_session.login(
        employee=employee,
        access_token="fake-token",
    )

    return current_session, employee


def create_controller(
    role: Role = Role.GESTION,
) -> tuple[
    ContractController,
    Mock,
    CurrentSession,
    Employee,
]:
    """Construit un ContractController avec un service simulé."""
    current_session, employee = create_current_session(role)
    contract_service = Mock()

    controller = ContractController(
        contract_service=contract_service,
        current_session=current_session,
    )

    return (
        controller,
        contract_service,
        current_session,
        employee,
    )


def create_contract_mock(
    *,
    contract_id: int = 2,
    client_id: int = 10,
    commercial_id: int = 3,
    total_amount: Decimal = Decimal("1000.00"),
    remaining_amount: Decimal = Decimal("400.00"),
    is_signed: bool = True,
) -> Contract:
    """Crée un faux contrat réutilisable."""
    contract = Mock(spec=Contract)
    contract.id = contract_id
    contract.client_id = client_id
    contract.commercial_id = commercial_id
    contract.total_amount = total_amount
    contract.remaining_amount = remaining_amount
    contract.is_signed = is_signed
    contract.created_at = "2026-07-01 10:00:00"

    return contract


# ---------------------------------------------------------------------------
# Consultation
# ---------------------------------------------------------------------------


def test_list_contracts_displays_contracts(capsys) -> None:
    controller, service, _session, employee = create_controller()
    contract = create_contract_mock()
    service.list_contracts.return_value = [contract]

    controller.list_contracts()

    output = capsys.readouterr().out

    assert "Liste des contrats" in output
    assert "Client 10" in output
    assert "1000.00 €" in output
    assert "400.00 €" in output
    assert "Signé : Oui" in output
    service.list_contracts.assert_called_once_with(employee)


def test_list_contracts_displays_empty_message(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_contracts.return_value = []

    controller.list_contracts()

    assert "Aucun contrat trouvé." in capsys.readouterr().out
    service.list_contracts.assert_called_once_with(employee)


def test_list_contracts_displays_service_error(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_contracts.side_effect = AuthorizationError(
        "Accès interdit."
    )

    controller.list_contracts()

    assert "Erreur : Accès interdit." in capsys.readouterr().out
    service.list_contracts.assert_called_once_with(employee)


def test_get_contract_displays_contract(monkeypatch, capsys) -> None:
    controller, service, _session, employee = create_controller()
    contract = create_contract_mock()
    service.get_contract.return_value = contract

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "2",
    )

    controller.get_contract()

    output = capsys.readouterr().out

    assert "=== Contrat ===" in output
    assert "ID : 2" in output
    assert "Client ID : 10" in output
    assert "Commercial responsable ID : 3" in output
    assert "Montant total : 1000.00 €" in output
    assert "Montant restant : 400.00 €" in output
    assert "Signé : Oui" in output

    service.get_contract.assert_called_once_with(
        current_employee=employee,
        contract_id=2,
    )


def test_get_contract_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    controller.get_contract()

    assert (
        "La valeur doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.get_contract.assert_not_called()


def test_get_contract_displays_not_found_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.get_contract.side_effect = NotFoundError(
        "Contrat introuvable."
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "999",
    )

    controller.get_contract()

    assert "Erreur : Contrat introuvable." in capsys.readouterr().out
    service.get_contract.assert_called_once_with(
        current_employee=employee,
        contract_id=999,
    )


# ---------------------------------------------------------------------------
# Création - service gestion
# ---------------------------------------------------------------------------


def test_create_contract_calls_service(monkeypatch, capsys) -> None:
    controller, service, _session, employee = create_controller(
        Role.GESTION
    )
    contract = create_contract_mock()
    service.create_contract.return_value = contract

    input_values = iter(
        [
            "10",
            "1000,00",
            "400.00",
            "o",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_contract()

    output = capsys.readouterr().out

    assert "Création d'un contrat" in output
    assert "Contrat créé avec succès" in output
    assert "id=2" in output

    service.create_contract.assert_called_once_with(
        current_employee=employee,
        client_id=10,
        total_amount=Decimal("1000.00"),
        remaining_amount=Decimal("400.00"),
        is_signed=True,
    )


def test_create_contract_stops_for_invalid_client_id(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller(
        Role.GESTION
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    controller.create_contract()

    assert (
        "La valeur doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.create_contract.assert_not_called()


def test_create_contract_stops_for_invalid_total_amount(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller(
        Role.GESTION
    )

    input_values = iter(["10", "invalid"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_contract()

    assert (
        "Le montant doit être un nombre valide."
        in capsys.readouterr().out
    )
    service.create_contract.assert_not_called()


def test_create_contract_stops_for_invalid_remaining_amount(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller(
        Role.GESTION
    )

    input_values = iter(["10", "1000", "invalid"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_contract()

    assert (
        "Le montant doit être un nombre valide."
        in capsys.readouterr().out
    )
    service.create_contract.assert_not_called()


def test_create_contract_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller(
        Role.GESTION
    )
    service.create_contract.side_effect = AuthorizationError(
        "Création interdite."
    )

    input_values = iter(["10", "1000", "400", "n"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_contract()

    assert "Erreur : Création interdite." in capsys.readouterr().out
    service.create_contract.assert_called_once_with(
        current_employee=employee,
        client_id=10,
        total_amount=Decimal("1000"),
        remaining_amount=Decimal("400"),
        is_signed=False,
    )


# ---------------------------------------------------------------------------
# Modification - gestion ou commercial autorisé par le service
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.COMMERCIAL],
)
def test_update_contract_calls_service(
    monkeypatch,
    capsys,
    role,
) -> None:
    controller, service, _session, employee = create_controller(role)
    contract = create_contract_mock()
    service.update_contract.return_value = contract

    input_values = iter(
        [
            "2",
            "1200",
            "300",
            "o",
            "o",
        ]
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_contract()

    assert (
        "Contrat 2 mis à jour avec succès."
        in capsys.readouterr().out
    )

    service.update_contract.assert_called_once_with(
        current_employee=employee,
        contract_id=2,
        total_amount=Decimal("1200"),
        remaining_amount=Decimal("300"),
        is_signed=True,
    )


def test_update_contract_passes_none_for_unchanged_values(
    monkeypatch,
) -> None:
    controller, service, _session, employee = create_controller(
        Role.COMMERCIAL
    )
    service.update_contract.return_value = create_contract_mock()

    input_values = iter(
        [
            "2",
            "",
            "",
            "n",
        ]
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_contract()

    service.update_contract.assert_called_once_with(
        current_employee=employee,
        contract_id=2,
        total_amount=None,
        remaining_amount=None,
        is_signed=None,
    )


def test_update_contract_can_set_signed_to_false(
    monkeypatch,
) -> None:
    controller, service, _session, employee = create_controller(
        Role.GESTION
    )
    service.update_contract.return_value = create_contract_mock(
        is_signed=False
    )

    input_values = iter(
        [
            "2",
            "",
            "",
            "o",
            "n",
        ]
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_contract()

    service.update_contract.assert_called_once_with(
        current_employee=employee,
        contract_id=2,
        total_amount=None,
        remaining_amount=None,
        is_signed=False,
    )


def test_update_contract_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "invalid",
    )

    controller.update_contract()

    assert (
        "La valeur doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.update_contract.assert_not_called()


def test_update_contract_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller(
        Role.COMMERCIAL
    )
    service.update_contract.side_effect = AuthorizationError(
        "Modification interdite."
    )

    input_values = iter(["2", "1200", "", "n"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_contract()

    assert (
        "Erreur : Modification interdite."
        in capsys.readouterr().out
    )

    service.update_contract.assert_called_once_with(
        current_employee=employee,
        contract_id=2,
        total_amount=Decimal("1200"),
        remaining_amount=None,
        is_signed=None,
    )


# ---------------------------------------------------------------------------
# Filtres commerciaux
# ---------------------------------------------------------------------------


def test_list_unsigned_contracts_displays_contracts(capsys) -> None:
    controller, service, _session, employee = create_controller(
        Role.COMMERCIAL
    )
    contract = create_contract_mock(is_signed=False)
    service.list_unsigned_contracts.return_value = [contract]

    controller.list_unsigned_contracts()

    output = capsys.readouterr().out

    assert "Liste des contrats" in output
    assert "Signé : Non" in output
    service.list_unsigned_contracts.assert_called_once_with(employee)


def test_list_unsigned_contracts_displays_empty_message(capsys) -> None:
    controller, service, _session, employee = create_controller(
        Role.COMMERCIAL
    )
    service.list_unsigned_contracts.return_value = []

    controller.list_unsigned_contracts()

    assert "Aucun contrat trouvé." in capsys.readouterr().out
    service.list_unsigned_contracts.assert_called_once_with(employee)


def test_list_unpaid_contracts_displays_contracts(capsys) -> None:
    controller, service, _session, employee = create_controller(
        Role.COMMERCIAL
    )
    contract = create_contract_mock(
        remaining_amount=Decimal("400.00")
    )
    service.list_unpaid_contracts.return_value = [contract]

    controller.list_unpaid_contracts()

    output = capsys.readouterr().out

    assert "Liste des contrats" in output
    assert "Restant : 400.00 €" in output
    service.list_unpaid_contracts.assert_called_once_with(employee)


def test_list_unpaid_contracts_displays_empty_message(capsys) -> None:
    controller, service, _session, employee = create_controller(
        Role.COMMERCIAL
    )
    service.list_unpaid_contracts.return_value = []

    controller.list_unpaid_contracts()

    assert "Aucun contrat trouvé." in capsys.readouterr().out
    service.list_unpaid_contracts.assert_called_once_with(employee)


# ---------------------------------------------------------------------------
# Menus par rôle
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("choice", "method_name"),
    [
        ("1", "list_contracts"),
        ("2", "get_contract"),
        ("3", "create_contract"),
        ("4", "update_contract"),
    ],
)
def test_management_menu_calls_selected_action(
    monkeypatch,
    choice,
    method_name,
) -> None:
    controller, _service, _session, _employee = create_controller(
        Role.GESTION
    )

    selected_method = Mock()
    monkeypatch.setattr(
        controller,
        method_name,
        selected_method,
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": choice,
    )

    should_return = controller._run_management_menu()

    assert should_return is False
    selected_method.assert_called_once_with()


@pytest.mark.parametrize(
    ("choice", "method_name"),
    [
        ("1", "list_contracts"),
        ("2", "get_contract"),
        ("3", "update_contract"),
        ("4", "list_unsigned_contracts"),
        ("5", "list_unpaid_contracts"),
    ],
)
def test_commercial_menu_calls_selected_action(
    monkeypatch,
    choice,
    method_name,
) -> None:
    controller, _service, _session, _employee = create_controller(
        Role.COMMERCIAL
    )

    selected_method = Mock()
    monkeypatch.setattr(
        controller,
        method_name,
        selected_method,
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": choice,
    )

    should_return = controller._run_commercial_menu()

    assert should_return is False
    selected_method.assert_called_once_with()


@pytest.mark.parametrize(
    ("choice", "method_name"),
    [
        ("1", "list_contracts"),
        ("2", "get_contract"),
    ],
)
def test_read_only_menu_calls_selected_action(
    monkeypatch,
    choice,
    method_name,
) -> None:
    controller, _service, _session, _employee = create_controller(
        Role.SUPPORT
    )

    selected_method = Mock()
    monkeypatch.setattr(
        controller,
        method_name,
        selected_method,
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": choice,
    )

    should_return = controller._run_read_only_menu()

    assert should_return is False
    selected_method.assert_called_once_with()


@pytest.mark.parametrize(
    ("role", "menu_method"),
    [
        (Role.GESTION, "_run_management_menu"),
        (Role.COMMERCIAL, "_run_commercial_menu"),
        (Role.SUPPORT, "_run_read_only_menu"),
    ],
)
def test_run_dispatches_menu_by_role(
    monkeypatch,
    role,
    menu_method,
) -> None:
    controller, _service, current_session, _employee = (
        create_controller(role)
    )

    states = iter([True, False])
    monkeypatch.setattr(
        type(current_session),
        "is_authenticated",
        property(lambda _self: next(states, False)),
    )

    management_menu = Mock(return_value=False)
    commercial_menu = Mock(return_value=False)
    read_only_menu = Mock(return_value=False)

    monkeypatch.setattr(
        controller,
        "_run_management_menu",
        management_menu,
    )
    monkeypatch.setattr(
        controller,
        "_run_commercial_menu",
        commercial_menu,
    )
    monkeypatch.setattr(
        controller,
        "_run_read_only_menu",
        read_only_menu,
    )

    controller.run()

    menus = {
        "_run_management_menu": management_menu,
        "_run_commercial_menu": commercial_menu,
        "_run_read_only_menu": read_only_menu,
    }

    for name, mocked_menu in menus.items():
        if name == menu_method:
            mocked_menu.assert_called_once_with()
        else:
            mocked_menu.assert_not_called()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_get_current_employee_raises_when_session_is_empty() -> None:
    controller = ContractController(
        contract_service=Mock(),
        current_session=CurrentSession(),
    )

    with pytest.raises(
        RuntimeError,
        match="Aucun .* connecté dans la session",
    ):
        controller._get_current_employee()


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("1", 1),
        (" 42 ", 42),
        ("-3", -3),
    ],
)
def test_ask_integer_returns_integer(
    monkeypatch,
    raw_value,
    expected,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": raw_value,
    )

    assert ContractController._ask_integer("ID : ") == expected


def test_ask_integer_returns_none_for_invalid_value(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    result = ContractController._ask_integer("ID : ")

    assert result is None
    assert (
        "La valeur doit être un nombre entier."
        in capsys.readouterr().out
    )


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("1000", Decimal("1000")),
        ("1000.50", Decimal("1000.50")),
        ("1000,50", Decimal("1000.50")),
        (" 25,75 ", Decimal("25.75")),
    ],
)
def test_ask_decimal_returns_decimal(
    monkeypatch,
    raw_value,
    expected,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": raw_value,
    )

    assert ContractController._ask_decimal(
        "Montant : "
    ) == expected


def test_ask_decimal_returns_none_for_invalid_value(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "invalid",
    )

    result = ContractController._ask_decimal("Montant : ")

    assert result is None
    assert (
        "Le montant doit être un nombre valide."
        in capsys.readouterr().out
    )


def test_ask_optional_decimal_returns_none_for_empty_value(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "   ",
    )

    assert (
        ContractController._ask_optional_decimal("Montant : ")
        is None
    )


def test_ask_optional_decimal_returns_decimal(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "150,25",
    )

    assert ContractController._ask_optional_decimal(
        "Montant : "
    ) == Decimal("150.25")


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("o", True),
        ("O", True),
        (" o ", True),
        ("n", False),
        ("", False),
        ("oui", False),
    ],
)
def test_ask_boolean_returns_expected_value(
    monkeypatch,
    raw_value,
    expected,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": raw_value,
    )

    assert (
        ContractController._ask_boolean("Signé ? ")
        is expected
    )


def test_display_contract_displays_unsigned_contract(capsys) -> None:
    contract = create_contract_mock(is_signed=False)

    ContractController._display_contract(contract)

    assert "Signé : Non" in capsys.readouterr().out


def test_display_contract_list_displays_empty_message(capsys) -> None:
    ContractController._display_contract_list([])

    assert "Aucun contrat trouvé." in capsys.readouterr().out