from unittest.mock import Mock

import pytest

from app.controllers.client_controller import ClientController
from app.models.client import Client
from app.models.employee import Employee, Role
from app.session.current_session import CurrentSession
from app.utils.exceptions import AuthorizationError, NotFoundError


def create_current_session(
    role: Role = Role.COMMERCIAL,
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
    role: Role = Role.COMMERCIAL,
) -> tuple[
    ClientController,
    Mock,
    CurrentSession,
    Employee,
]:
    """Construit un ClientController avec un service simulé."""
    current_session, employee = create_current_session(role)
    client_service = Mock()

    controller = ClientController(
        client_service=client_service,
        current_session=current_session,
    )

    return (
        controller,
        client_service,
        current_session,
        employee,
    )


def create_client_mock() -> Client:
    """Crée un faux client réutilisable dans les tests."""
    client = Mock(spec=Client)
    client.id = 2
    client.full_name = "Jean Dupont"
    client.email = "jean.dupont@test.com"
    client.phone = "0601020304"
    client.company = "Dupont SAS"
    client.commercial_id = 1
    client.created_at = "2026-07-01 10:00:00"
    client.updated_at = "2026-07-02 11:00:00"

    return client


def test_list_clients_displays_clients(capsys) -> None:
    controller, service, _session, employee = create_controller()
    client = create_client_mock()
    service.list_clients.return_value = [client]

    controller.list_clients()

    output = capsys.readouterr().out

    assert "Liste des clients" in output
    assert "Jean Dupont" in output
    assert "Dupont SAS" in output
    assert "jean.dupont@test.com" in output
    service.list_clients.assert_called_once_with(employee)


def test_list_clients_displays_empty_message(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_clients.return_value = []

    controller.list_clients()

    output = capsys.readouterr().out

    assert "Aucun client trouvé" in output
    service.list_clients.assert_called_once_with(employee)


def test_list_clients_displays_service_error(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_clients.side_effect = AuthorizationError(
        "Accès interdit."
    )

    controller.list_clients()

    assert "Erreur : Accès interdit." in capsys.readouterr().out
    service.list_clients.assert_called_once_with(employee)


def test_get_client_displays_client(monkeypatch, capsys) -> None:
    controller, service, _session, employee = create_controller()
    client = create_client_mock()
    service.get_client.return_value = client

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "2",
    )

    controller.get_client()

    output = capsys.readouterr().out

    assert "=== Client ===" in output
    assert "ID : 2" in output
    assert "Nom : Jean Dupont" in output
    assert "Email : jean.dupont@test.com" in output
    assert "Téléphone : 0601020304" in output
    assert "Entreprise : Dupont SAS" in output
    assert "Commercial responsable ID : 1" in output

    service.get_client.assert_called_once_with(
        current_employee=employee,
        client_id=2,
    )


def test_get_client_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    controller.get_client()

    assert (
        "L'identifiant doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.get_client.assert_not_called()


def test_get_client_displays_not_found_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()

    service.get_client.side_effect = NotFoundError(
        "Client introuvable."
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "999",
    )

    controller.get_client()

    assert "Erreur : Client introuvable." in capsys.readouterr().out
    service.get_client.assert_called_once_with(
        current_employee=employee,
        client_id=999,
    )


def test_create_client_calls_service(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    client = create_client_mock()
    service.create_client.return_value = client

    input_values = iter(
        [
            "Jean Dupont",
            "jean.dupont@test.com",
            "0601020304",
            "Dupont SAS",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_client()

    output = capsys.readouterr().out

    assert "Création d'un client" in output
    assert "Client créé avec succès" in output
    assert "Jean Dupont" in output
    assert "id=2" in output

    service.create_client.assert_called_once_with(
        current_employee=employee,
        full_name="Jean Dupont",
        email="jean.dupont@test.com",
        phone="0601020304",
        company="Dupont SAS",
    )


def test_create_client_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()

    service.create_client.side_effect = AuthorizationError(
        "Création interdite."
    )

    input_values = iter(
        [
            "Jean Dupont",
            "jean.dupont@test.com",
            "0601020304",
            "Dupont SAS",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_client()

    assert "Erreur : Création interdite." in capsys.readouterr().out
    service.create_client.assert_called_once_with(
        current_employee=employee,
        full_name="Jean Dupont",
        email="jean.dupont@test.com",
        phone="0601020304",
        company="Dupont SAS",
    )


def test_update_client_calls_service(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    client = create_client_mock()
    service.update_client.return_value = client

    input_values = iter(
        [
            "2",
            "Jean Martin",
            "jean.martin@test.com",
            "0611223344",
            "Martin SAS",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_client()

    assert (
        "Client 2 mis à jour avec succès."
        in capsys.readouterr().out
    )

    service.update_client.assert_called_once_with(
        current_employee=employee,
        client_id=2,
        full_name="Jean Martin",
        email="jean.martin@test.com",
        phone="0611223344",
        company="Martin SAS",
    )


def test_update_client_passes_none_for_empty_fields(
    monkeypatch,
) -> None:
    controller, service, _session, employee = create_controller()
    service.update_client.return_value = create_client_mock()

    input_values = iter(["2", "", "", "", ""])

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_client()

    service.update_client.assert_called_once_with(
        current_employee=employee,
        client_id=2,
        full_name=None,
        email=None,
        phone=None,
        company=None,
    )


def test_update_client_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "invalid",
    )

    controller.update_client()

    assert (
        "L'identifiant doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.update_client.assert_not_called()


def test_update_client_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()

    service.update_client.side_effect = AuthorizationError(
        "Modification interdite."
    )

    input_values = iter(
        [
            "2",
            "Jean Martin",
            "",
            "",
            "",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_client()

    assert (
        "Erreur : Modification interdite."
        in capsys.readouterr().out
    )

    service.update_client.assert_called_once_with(
        current_employee=employee,
        client_id=2,
        full_name="Jean Martin",
        email=None,
        phone=None,
        company=None,
    )


@pytest.mark.parametrize(
    ("choice", "method_name"),
    [
        ("1", "list_clients"),
        ("2", "get_client"),
        ("3", "create_client"),
        ("4", "update_client"),
    ],
)
def test_commercial_menu_calls_selected_action(
    monkeypatch,
    choice: str,
    method_name: str,
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


def test_commercial_menu_returns_on_zero(monkeypatch) -> None:
    controller, _service, _session, _employee = create_controller(
        Role.COMMERCIAL
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "0",
    )

    assert controller._run_commercial_menu() is True


@pytest.mark.parametrize(
    ("choice", "method_name"),
    [
        ("1", "list_clients"),
        ("2", "get_client"),
    ],
)
def test_read_only_menu_calls_selected_action(
    monkeypatch,
    choice: str,
    method_name: str,
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


def test_read_only_menu_returns_on_zero(monkeypatch) -> None:
    controller, _service, _session, _employee = create_controller(
        Role.GESTION
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "0",
    )

    assert controller._run_read_only_menu() is True


@pytest.mark.parametrize(
    ("role", "expected_menu"),
    [
        (Role.COMMERCIAL, "_run_commercial_menu"),
        (Role.GESTION, "_run_read_only_menu"),
        (Role.SUPPORT, "_run_read_only_menu"),
    ],
)
def test_run_dispatches_menu_by_role(
    monkeypatch,
    role: Role,
    expected_menu: str,
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

    commercial_menu = Mock(return_value=False)
    read_only_menu = Mock(return_value=False)

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

    if expected_menu == "_run_commercial_menu":
        commercial_menu.assert_called_once_with()
        read_only_menu.assert_not_called()
    else:
        read_only_menu.assert_called_once_with()
        commercial_menu.assert_not_called()


def test_get_current_employee_raises_when_session_is_empty() -> None:
    controller = ClientController(
        client_service=Mock(),
        current_session=CurrentSession(),
    )

    with pytest.raises(
        RuntimeError,
        match="Aucun collaborateur connecté dans la session|"
        "Aucun employé connecté dans la session",
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

    assert ClientController._ask_integer("ID : ") == expected


def test_ask_integer_returns_none_for_invalid_value(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    result = ClientController._ask_integer("ID : ")

    assert result is None
    assert (
        "L'identifiant doit être un nombre entier."
        in capsys.readouterr().out
    )