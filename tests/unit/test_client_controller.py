from unittest.mock import Mock

import pytest

from app.controllers.client_controller import ClientController
from app.models.client import Client
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
    ClientController,
    Mock,
    CurrentSession,
    Employee,
]:
    """Construit un ClientController avec un service simulé."""
    current_session, employee = create_current_session()
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
    (
        controller,
        client_service,
        _current_session,
        employee,
    ) = create_controller()

    client = create_client_mock()
    client_service.list_clients.return_value = [client]

    controller.list_clients()

    captured = capsys.readouterr()

    assert "Liste des clients" in captured.out
    assert "Jean Dupont" in captured.out
    assert "Dupont SAS" in captured.out
    assert "jean.dupont@test.com" in captured.out
    client_service.list_clients.assert_called_once_with(employee)


def test_list_clients_displays_empty_message(capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        employee,
    ) = create_controller()

    client_service.list_clients.return_value = []

    controller.list_clients()

    captured = capsys.readouterr()

    assert "Aucun client trouvé" in captured.out
    client_service.list_clients.assert_called_once_with(employee)


def test_list_clients_displays_service_error(capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        employee,
    ) = create_controller()

    client_service.list_clients.side_effect = AuthorizationError("Accès interdit.")

    controller.list_clients()

    captured = capsys.readouterr()

    assert "Erreur : Accès interdit." in captured.out
    client_service.list_clients.assert_called_once_with(employee)


def test_get_client_displays_client(monkeypatch, capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        employee,
    ) = create_controller()

    client = create_client_mock()
    client_service.get_client.return_value = client

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "2",
    )

    controller.get_client()

    captured = capsys.readouterr()

    assert "=== Client ===" in captured.out
    assert "ID : 2" in captured.out
    assert "Nom : Jean Dupont" in captured.out
    assert "Email : jean.dupont@test.com" in captured.out
    assert "Téléphone : 0601020304" in captured.out
    assert "Entreprise : Dupont SAS" in captured.out
    assert "Commercial ID : 1" in captured.out
    assert "Créé le : 2026-07-01 10:00:00" in captured.out
    assert "Mis à jour le : 2026-07-02 11:00:00" in captured.out
    client_service.get_client.assert_called_once_with(
        current_employee=employee,
        client_id=2,
    )


def test_get_client_rejects_invalid_identifier(monkeypatch, capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        _employee,
    ) = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    controller.get_client()

    captured = capsys.readouterr()

    assert "L'identifiant doit être un nombre entier." in captured.out
    client_service.get_client.assert_not_called()


def test_get_client_displays_not_found_error(monkeypatch, capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        employee,
    ) = create_controller()

    client_service.get_client.side_effect = NotFoundError("Client introuvable.")

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "999",
    )

    controller.get_client()

    captured = capsys.readouterr()

    assert "Erreur : Client introuvable." in captured.out
    client_service.get_client.assert_called_once_with(
        current_employee=employee,
        client_id=999,
    )


def test_create_client_calls_service(monkeypatch, capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        employee,
    ) = create_controller()

    client = create_client_mock()
    client_service.create_client.return_value = client

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

    captured = capsys.readouterr()

    assert "Création d'un client" in captured.out
    assert "Client créé avec succès" in captured.out
    assert "Jean Dupont" in captured.out
    assert "id=2" in captured.out
    client_service.create_client.assert_called_once_with(
        current_employee=employee,
        full_name="Jean Dupont",
        email="jean.dupont@test.com",
        phone="0601020304",
        company="Dupont SAS",
    )


def test_create_client_displays_service_error(monkeypatch, capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        employee,
    ) = create_controller()

    client_service.create_client.side_effect = AuthorizationError("Création interdite.")

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

    captured = capsys.readouterr()

    assert "Erreur : Création interdite." in captured.out
    client_service.create_client.assert_called_once_with(
        current_employee=employee,
        full_name="Jean Dupont",
        email="jean.dupont@test.com",
        phone="0601020304",
        company="Dupont SAS",
    )


def test_update_client_calls_service(monkeypatch, capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        employee,
    ) = create_controller()

    client = create_client_mock()
    client_service.update_client.return_value = client

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

    captured = capsys.readouterr()

    assert "Client 2 mis à jour avec succès." in captured.out
    client_service.update_client.assert_called_once_with(
        current_employee=employee,
        client_id=2,
        full_name="Jean Martin",
        email="jean.martin@test.com",
        phone="0611223344",
        company="Martin SAS",
    )


def test_update_client_passes_none_for_empty_fields(monkeypatch) -> None:
    (
        controller,
        client_service,
        _current_session,
        employee,
    ) = create_controller()

    client = create_client_mock()
    client_service.update_client.return_value = client

    input_values = iter(
        [
            "2",
            "",
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

    client_service.update_client.assert_called_once_with(
        current_employee=employee,
        client_id=2,
        full_name=None,
        email=None,
        phone=None,
        company=None,
    )


def test_update_client_rejects_invalid_identifier(monkeypatch, capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        _employee,
    ) = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "invalid",
    )

    controller.update_client()

    captured = capsys.readouterr()

    assert "L'identifiant doit être un nombre entier." in captured.out
    client_service.update_client.assert_not_called()


def test_update_client_displays_service_error(monkeypatch, capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        employee,
    ) = create_controller()

    client_service.update_client.side_effect = AuthorizationError(
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

    captured = capsys.readouterr()

    assert "Erreur : Modification interdite." in captured.out
    client_service.update_client.assert_called_once_with(
        current_employee=employee,
        client_id=2,
        full_name="Jean Martin",
        email=None,
        phone=None,
        company=None,
    )


def test_delete_client_calls_service_when_confirmed(monkeypatch, capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        employee,
    ) = create_controller()

    input_values = iter(
        [
            "2",
            "o",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_client()

    captured = capsys.readouterr()

    assert "Client supprimé avec succès." in captured.out
    client_service.delete_client.assert_called_once_with(
        current_employee=employee,
        client_id=2,
    )


def test_delete_client_does_not_call_service_when_cancelled(
    monkeypatch, capsys
) -> None:
    (
        controller,
        client_service,
        _current_session,
        _employee,
    ) = create_controller()

    input_values = iter(
        [
            "2",
            "n",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_client()

    captured = capsys.readouterr()

    assert "Suppression annulée." in captured.out
    client_service.delete_client.assert_not_called()


def test_delete_client_rejects_invalid_identifier(monkeypatch, capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        _employee,
    ) = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "invalid",
    )

    controller.delete_client()

    captured = capsys.readouterr()

    assert "L'identifiant doit être un nombre entier." in captured.out
    client_service.delete_client.assert_not_called()


def test_delete_client_displays_service_error(monkeypatch, capsys) -> None:
    (
        controller,
        client_service,
        _current_session,
        employee,
    ) = create_controller()

    client_service.delete_client.side_effect = AuthorizationError(
        "Suppression interdite."
    )

    input_values = iter(
        [
            "2",
            "o",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_client()

    captured = capsys.readouterr()

    assert "Erreur : Suppression interdite." in captured.out
    client_service.delete_client.assert_called_once_with(
        current_employee=employee,
        client_id=2,
    )


@pytest.mark.parametrize(
    ("choice", "method_name"),
    [
        ("1", "list_clients"),
        ("2", "get_client"),
        ("3", "create_client"),
        ("4", "update_client"),
        ("5", "delete_client"),
    ],
)
def test_run_calls_selected_action(
    monkeypatch,
    choice: str,
    method_name: str,
) -> None:

    (
        controller,
        _client_service,
        _current_session,
        _employee,
    ) = create_controller()

    selected_method = Mock()
    monkeypatch.setattr(controller, method_name, selected_method)

    input_values = iter(
        [
            choice,
            "0",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.run()

    selected_method.assert_called_once_with()


def test_run_displays_invalid_choice(monkeypatch, capsys) -> None:
    (
        controller,
        _client_service,
        _current_session,
        _employee,
    ) = create_controller()

    input_values = iter(
        [
            "99",
            "0",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.run()

    captured = capsys.readouterr()

    assert "Choix invalide." in captured.out


def test_get_current_employee_raises_when_session_is_empty() -> None:

    client_service = Mock()
    current_session = CurrentSession()

    controller = ClientController(
        client_service=client_service,
        current_session=current_session,
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

    assert ClientController._ask_integer("ID : ") == expected


def test_ask_integer_returns_none_for_invalid_value(monkeypatch, capsys) -> None:

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    result = ClientController._ask_integer("ID : ")

    captured = capsys.readouterr()

    assert result is None
    assert "L'identifiant doit être un nombre entier." in captured.out