from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.controllers.contract_controller import ContractController
from app.models.contract import Contract
from app.models.employee import Employee, Role
from app.session.current_session import CurrentSession
from app.utils.exceptions import AuthorizationError, NotFoundError


def create_current_session() -> tuple[CurrentSession, Employee]:
    """Crée une session contenant un employé connecté."""
    employee = Mock(spec=Employee)
    employee.id = 1
    employee.first_name = "Alice"
    employee.last_name = "Martin"
    employee.email = "alice@test.com"
    employee.role = Role.COMMERCIAL

    current_session = CurrentSession()
    current_session.login(
        employee=employee,
        access_token="fake-token",
    )

    return current_session, employee


def create_controller() -> tuple[
    ContractController,
    Mock,
    CurrentSession,
    Employee,
]:
    """Construit un ContractController avec un service simulé."""
    current_session, employee = create_current_session()
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
    commercial_id: int = 1,
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


def test_list_contracts_displays_contracts(capsys) -> None:
    controller, service, _session, employee = create_controller()
    contract = create_contract_mock()
    service.list_contracts.return_value = [contract]

    controller.list_contracts()

    captured = capsys.readouterr()

    assert "Liste des contrats" in captured.out
    assert "Client 10" in captured.out
    assert "1000.00 €" in captured.out
    assert "400.00 €" in captured.out
    assert "Signé : Oui" in captured.out
    service.list_contracts.assert_called_once_with(employee)


def test_list_contracts_displays_empty_message(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_contracts.return_value = []

    controller.list_contracts()

    captured = capsys.readouterr()

    assert "Aucun contrat trouvé." in captured.out
    service.list_contracts.assert_called_once_with(employee)


def test_list_contracts_displays_service_error(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_contracts.side_effect = AuthorizationError("Accès interdit.")

    controller.list_contracts()

    captured = capsys.readouterr()

    assert "Erreur : Accès interdit." in captured.out
    service.list_contracts.assert_called_once_with(employee)


def test_get_contract_displays_contract(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    contract = create_contract_mock()
    service.get_contract.return_value = contract

    monkeypatch.setattr("builtins.input", lambda _message="": "2")

    controller.get_contract()

    captured = capsys.readouterr()

    assert "=== Contrat ===" in captured.out
    assert "ID : 2" in captured.out
    assert "Client ID : 10" in captured.out
    assert "Commercial ID : 1" in captured.out
    assert "Montant total : 1000.00 €" in captured.out
    assert "Montant restant : 400.00 €" in captured.out
    assert "Signé : Oui" in captured.out
    assert "Créé le : 2026-07-01 10:00:00" in captured.out
    service.get_contract.assert_called_once_with(
        current_employee=employee,
        contract_id=2,
    )


def test_get_contract_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    monkeypatch.setattr("builtins.input", lambda _message="": "abc")

    controller.get_contract()

    captured = capsys.readouterr()

    assert "La valeur doit être un nombre entier." in captured.out
    service.get_contract.assert_not_called()


def test_get_contract_displays_not_found_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.get_contract.side_effect = NotFoundError("Contrat introuvable.")

    monkeypatch.setattr("builtins.input", lambda _message="": "999")

    controller.get_contract()

    captured = capsys.readouterr()

    assert "Erreur : Contrat introuvable." in captured.out
    service.get_contract.assert_called_once_with(
        current_employee=employee,
        contract_id=999,
    )


def test_create_contract_calls_service(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
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

    captured = capsys.readouterr()

    assert "Création d'un contrat" in captured.out
    assert "Contrat créé avec succès" in captured.out
    assert "id=2" in captured.out
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
    controller, service, _session, _employee = create_controller()

    monkeypatch.setattr("builtins.input", lambda _message="": "abc")

    controller.create_contract()

    captured = capsys.readouterr()

    assert "La valeur doit être un nombre entier." in captured.out
    service.create_contract.assert_not_called()


def test_create_contract_stops_for_invalid_total_amount(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    input_values = iter(["10", "invalid"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_contract()

    captured = capsys.readouterr()

    assert "Le montant doit être un nombre valide." in captured.out
    service.create_contract.assert_not_called()


def test_create_contract_stops_for_invalid_remaining_amount(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    input_values = iter(["10", "1000", "invalid"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_contract()

    captured = capsys.readouterr()

    assert "Le montant doit être un nombre valide." in captured.out
    service.create_contract.assert_not_called()


def test_create_contract_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.create_contract.side_effect = AuthorizationError("Création interdite.")

    input_values = iter(["10", "1000", "400", "n"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_contract()

    captured = capsys.readouterr()

    assert "Erreur : Création interdite." in captured.out
    service.create_contract.assert_called_once_with(
        current_employee=employee,
        client_id=10,
        total_amount=Decimal("1000"),
        remaining_amount=Decimal("400"),
        is_signed=False,
    )


def test_update_contract_calls_service(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
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

    captured = capsys.readouterr()

    assert "Contrat 2 mis à jour avec succès." in captured.out
    service.update_contract.assert_called_once_with(
        current_employee=employee,
        contract_id=2,
        total_amount=Decimal("1200"),
        remaining_amount=Decimal("300"),
        is_signed=True,
    )


def test_update_contract_passes_none_for_empty_values(
    monkeypatch,
) -> None:
    controller, service, _session, employee = create_controller()
    contract = create_contract_mock()
    service.update_contract.return_value = contract

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
    controller, service, _session, employee = create_controller()
    contract = create_contract_mock(is_signed=False)
    service.update_contract.return_value = contract

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

    monkeypatch.setattr("builtins.input", lambda _message="": "invalid")

    controller.update_contract()

    captured = capsys.readouterr()

    assert "La valeur doit être un nombre entier." in captured.out
    service.update_contract.assert_not_called()


def test_update_contract_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.update_contract.side_effect = AuthorizationError("Modification interdite.")

    input_values = iter(["2", "1200", "", "n"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_contract()

    captured = capsys.readouterr()

    assert "Erreur : Modification interdite." in captured.out
    service.update_contract.assert_called_once_with(
        current_employee=employee,
        contract_id=2,
        total_amount=Decimal("1200"),
        remaining_amount=None,
        is_signed=None,
    )


def test_list_unsigned_contracts_displays_contracts(capsys) -> None:
    controller, service, _session, employee = create_controller()
    contract = create_contract_mock(is_signed=False)
    service.list_unsigned_contracts.return_value = [contract]

    controller.list_unsigned_contracts()

    captured = capsys.readouterr()

    assert "Liste des contrats" in captured.out
    assert "Signé : Non" in captured.out
    service.list_unsigned_contracts.assert_called_once_with(employee)


def test_list_unsigned_contracts_displays_empty_message(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_unsigned_contracts.return_value = []

    controller.list_unsigned_contracts()

    captured = capsys.readouterr()

    assert "Aucun contrat trouvé." in captured.out
    service.list_unsigned_contracts.assert_called_once_with(employee)


def test_list_unsigned_contracts_displays_service_error(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_unsigned_contracts.side_effect = AuthorizationError("Accès interdit.")

    controller.list_unsigned_contracts()

    captured = capsys.readouterr()

    assert "Erreur : Accès interdit." in captured.out
    service.list_unsigned_contracts.assert_called_once_with(employee)


def test_list_unpaid_contracts_displays_contracts(capsys) -> None:
    controller, service, _session, employee = create_controller()
    contract = create_contract_mock(remaining_amount=Decimal("400.00"))
    service.list_unpaid_contracts.return_value = [contract]

    controller.list_unpaid_contracts()

    captured = capsys.readouterr()

    assert "Liste des contrats" in captured.out
    assert "Restant : 400.00 €" in captured.out
    service.list_unpaid_contracts.assert_called_once_with(employee)


def test_list_unpaid_contracts_displays_empty_message(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_unpaid_contracts.return_value = []

    controller.list_unpaid_contracts()

    captured = capsys.readouterr()

    assert "Aucun contrat trouvé." in captured.out
    service.list_unpaid_contracts.assert_called_once_with(employee)


def test_list_unpaid_contracts_displays_service_error(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_unpaid_contracts.side_effect = AuthorizationError("Accès interdit.")

    controller.list_unpaid_contracts()

    captured = capsys.readouterr()

    assert "Erreur : Accès interdit." in captured.out
    service.list_unpaid_contracts.assert_called_once_with(employee)


def test_delete_contract_calls_service_when_confirmed(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()

    input_values = iter(["2", "o"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_contract()

    captured = capsys.readouterr()

    assert "Contrat supprimé avec succès." in captured.out
    service.delete_contract.assert_called_once_with(
        current_employee=employee,
        contract_id=2,
    )


def test_delete_contract_does_not_call_service_when_cancelled(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    input_values = iter(["2", "n"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_contract()

    captured = capsys.readouterr()

    assert "Suppression annulée." in captured.out
    service.delete_contract.assert_not_called()


def test_delete_contract_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    monkeypatch.setattr("builtins.input", lambda _message="": "invalid")

    controller.delete_contract()

    captured = capsys.readouterr()

    assert "La valeur doit être un nombre entier." in captured.out
    service.delete_contract.assert_not_called()


def test_delete_contract_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.delete_contract.side_effect = AuthorizationError("Suppression interdite.")

    input_values = iter(["2", "o"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_contract()

    captured = capsys.readouterr()

    assert "Erreur : Suppression interdite." in captured.out
    service.delete_contract.assert_called_once_with(
        current_employee=employee,
        contract_id=2,
    )


@pytest.mark.parametrize(
    ("choice", "method_name"),
    [
        ("1", "list_contracts"),
        ("2", "get_contract"),
        ("3", "create_contract"),
        ("4", "update_contract"),
        ("5", "list_unsigned_contracts"),
        ("6", "list_unpaid_contracts"),
        ("7", "delete_contract"),
    ],
)
def test_run_calls_selected_action(
    monkeypatch,
    choice: str,
    method_name: str,
) -> None:
    controller, _service, _session, _employee = create_controller()

    selected_method = Mock()
    monkeypatch.setattr(controller, method_name, selected_method)

    input_values = iter([choice, "0"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.run()

    selected_method.assert_called_once_with()


def test_run_displays_invalid_choice(
    monkeypatch,
    capsys,
) -> None:
    controller, _service, _session, _employee = create_controller()

    input_values = iter(["99", "0"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.run()

    captured = capsys.readouterr()

    assert "Choix invalide." in captured.out


def test_get_current_employee_raises_when_session_is_empty() -> None:
    controller = ContractController(
        contract_service=Mock(),
        current_session=CurrentSession(),
    )

    with pytest.raises(
        RuntimeError,
        match="Aucun employé connecté dans la session",
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
    raw_value: str,
    expected: int,
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
    monkeypatch.setattr("builtins.input", lambda _message="": "abc")

    result = ContractController._ask_integer("ID : ")

    captured = capsys.readouterr()

    assert result is None
    assert "La valeur doit être un nombre entier." in captured.out


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
    raw_value: str,
    expected: Decimal,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": raw_value,
    )

    assert ContractController._ask_decimal("Montant : ") == expected


def test_ask_decimal_returns_none_for_invalid_value(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "invalid",
    )

    result = ContractController._ask_decimal("Montant : ")

    captured = capsys.readouterr()

    assert result is None
    assert "Le montant doit être un nombre valide." in captured.out


def test_ask_optional_decimal_returns_none_for_empty_value(
    monkeypatch,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _message="": "   ")

    result = ContractController._ask_optional_decimal("Montant : ")

    assert result is None


def test_ask_optional_decimal_returns_decimal(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "150,25",
    )

    result = ContractController._ask_optional_decimal("Montant : ")

    assert result == Decimal("150.25")


def test_ask_optional_decimal_returns_none_for_invalid_value(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "invalid",
    )

    result = ContractController._ask_optional_decimal("Montant : ")

    captured = capsys.readouterr()

    assert result is None
    assert "Le montant doit être un nombre valide." in captured.out


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
    raw_value: str,
    expected: bool,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": raw_value,
    )

    assert ContractController._ask_boolean("Signé ? ") is expected


def test_display_contract_displays_unsigned_contract(capsys) -> None:
    contract = create_contract_mock(is_signed=False)

    ContractController._display_contract(contract)

    captured = capsys.readouterr()

    assert "Signé : Non" in captured.out


def test_display_contract_list_displays_empty_message(capsys) -> None:
    ContractController._display_contract_list([])

    captured = capsys.readouterr()

    assert "Aucun contrat trouvé." in captured.out


def test_display_contract_list_displays_signed_and_unsigned_contracts(
    capsys,
) -> None:
    signed_contract = create_contract_mock(
        contract_id=1,
        is_signed=True,
    )
    unsigned_contract = create_contract_mock(
        contract_id=2,
        is_signed=False,
    )

    ContractController._display_contract_list([signed_contract, unsigned_contract])

    captured = capsys.readouterr()

    assert "Liste des contrats" in captured.out
    assert "Signé : Oui" in captured.out
    assert "Signé : Non" in captured.out