from unittest.mock import Mock

import pytest

from app.controllers.employee_controller import EmployeeController
from app.models.employee import Employee, Role
from app.session.current_session import CurrentSession
from app.utils.exceptions import (
    AuthorizationError,
    DuplicateError,
    NotFoundError,
)


def create_current_session() -> tuple[CurrentSession, Employee]:
    """Crée une session contenant un gestionnaire connecté."""
    manager = Mock(spec=Employee)
    manager.id = 1
    manager.first_name = "Admin"
    manager.last_name = "Epic Events"
    manager.email = "admin@test.com"
    manager.role = Role.GESTION

    current_session = CurrentSession()
    current_session.login(
        employee=manager,
        access_token="fake-token",
    )

    return current_session, manager


def create_controller() -> tuple[
    EmployeeController,
    Mock,
    CurrentSession,
    Employee,
]:
    """Construit un EmployeeController avec un service simulé."""
    current_session, manager = create_current_session()
    employee_service = Mock()

    controller = EmployeeController(
        employee_service=employee_service,
        current_session=current_session,
    )

    return (
        controller,
        employee_service,
        current_session,
        manager,
    )


def create_employee_mock(
    *,
    employee_id: int = 2,
    first_name: str = "Alice",
    last_name: str = "Martin",
    email: str = "alice@test.com",
    role: Role = Role.COMMERCIAL,
) -> Employee:
    """Crée un faux collaborateur réutilisable."""
    employee = Mock(spec=Employee)
    employee.id = employee_id
    employee.first_name = first_name
    employee.last_name = last_name
    employee.email = email
    employee.role = role
    return employee


# ---------------------------------------------------------------------------
# Consultation
# ---------------------------------------------------------------------------


def test_list_employees_displays_employees(capsys) -> None:
    controller, service, _session, manager = create_controller()
    employee = create_employee_mock()
    service.list_employees.return_value = [employee]

    controller.list_employees()

    output = capsys.readouterr().out

    assert "Liste des collaborateurs" in output
    assert "Alice Martin" in output
    assert "alice@test.com" in output
    assert "COMMERCIAL" in output
    service.list_employees.assert_called_once_with(manager)


def test_list_employees_displays_empty_message(capsys) -> None:
    controller, service, _session, manager = create_controller()
    service.list_employees.return_value = []

    controller.list_employees()

    assert "Aucun collaborateur trouvé" in capsys.readouterr().out
    service.list_employees.assert_called_once_with(manager)


def test_list_employees_displays_service_error(capsys) -> None:
    controller, service, _session, manager = create_controller()
    service.list_employees.side_effect = AuthorizationError(
        "Accès interdit."
    )

    controller.list_employees()

    assert "Erreur : Accès interdit." in capsys.readouterr().out
    service.list_employees.assert_called_once_with(manager)


def test_get_employee_displays_employee(monkeypatch, capsys) -> None:
    controller, service, _session, manager = create_controller()
    employee = create_employee_mock(role=Role.SUPPORT)
    service.get_employee.return_value = employee

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "2",
    )

    controller.get_employee()

    output = capsys.readouterr().out

    assert "=== Collaborateur ===" in output
    assert "ID : 2" in output
    assert "Prénom : Alice" in output
    assert "Nom : Martin" in output
    assert "Email : alice@test.com" in output
    assert "Rôle : SUPPORT" in output

    service.get_employee.assert_called_once_with(
        current_employee=manager,
        employee_id=2,
    )


def test_get_employee_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _manager = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    controller.get_employee()

    assert (
        "L'identifiant doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.get_employee.assert_not_called()


def test_get_employee_displays_not_found_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, manager = create_controller()
    service.get_employee.side_effect = NotFoundError(
        "Collaborateur introuvable."
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "999",
    )

    controller.get_employee()

    assert "Erreur : Collaborateur introuvable." in capsys.readouterr().out
    service.get_employee.assert_called_once_with(
        current_employee=manager,
        employee_id=999,
    )


# ---------------------------------------------------------------------------
# Création
# ---------------------------------------------------------------------------


def test_create_employee_calls_service(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, manager = create_controller()

    created_employee = create_employee_mock(
        employee_id=2,
        role=Role.COMMERCIAL,
    )
    service.create_employee.return_value = created_employee

    input_values = iter(
        [
            "Alice",
            "Martin",
            "alice@test.com",
            "1",
        ]
    )
    password_values = iter(
        [
            "Password123!",
            "Password123!",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )
    monkeypatch.setattr(
        "app.controllers.employee_controller.getpass",
        lambda _message="": next(password_values),
    )

    controller.create_employee()

    output = capsys.readouterr().out

    assert "Collaborateur créé avec succès" in output
    assert "Alice Martin" in output
    assert "COMMERCIAL" in output

    service.create_employee.assert_called_once_with(
        current_employee=manager,
        first_name="Alice",
        last_name="Martin",
        email="alice@test.com",
        password="Password123!",
        role=Role.COMMERCIAL,
    )


def test_create_employee_rejects_password_mismatch(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _manager = create_controller()

    input_values = iter(
        [
            "Alice",
            "Martin",
            "alice@test.com",
            "1",
        ]
    )
    password_values = iter(
        [
            "Password123!",
            "DifferentPassword123!",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )
    monkeypatch.setattr(
        "app.controllers.employee_controller.getpass",
        lambda _message="": next(password_values),
    )

    controller.create_employee()

    output = capsys.readouterr().out

    assert "les mots de passe ne correspondent pas" in output
    service.create_employee.assert_not_called()


def test_create_employee_rejects_invalid_role(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _manager = create_controller()

    input_values = iter(
        [
            "Alice",
            "Martin",
            "alice@test.com",
            "99",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_employee()

    assert "Rôle invalide." in capsys.readouterr().out
    service.create_employee.assert_not_called()


def test_create_employee_displays_duplicate_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, manager = create_controller()

    service.create_employee.side_effect = DuplicateError(
        "Un collaborateur utilise déjà cette adresse email."
    )

    input_values = iter(
        [
            "Alice",
            "Martin",
            "alice@test.com",
            "3",
        ]
    )
    password_values = iter(
        [
            "Password123!",
            "Password123!",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )
    monkeypatch.setattr(
        "app.controllers.employee_controller.getpass",
        lambda _message="": next(password_values),
    )

    controller.create_employee()

    assert (
        "Erreur : Un collaborateur utilise déjà cette adresse email."
        in capsys.readouterr().out
    )
    service.create_employee.assert_called_once_with(
        current_employee=manager,
        first_name="Alice",
        last_name="Martin",
        email="alice@test.com",
        password="Password123!",
        role=Role.SUPPORT,
    )


# ---------------------------------------------------------------------------
# Modification
# ---------------------------------------------------------------------------


def test_update_employee_calls_service(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, manager = create_controller()

    updated_employee = create_employee_mock(
        employee_id=2,
        role=Role.SUPPORT,
    )
    service.update_employee.return_value = updated_employee

    input_values = iter(
        [
            "2",
            "Alice",
            "Martin",
            "alice.new@test.com",
            "o",
            "3",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_employee()

    assert (
        "Collaborateur 2 mis à jour avec succès."
        in capsys.readouterr().out
    )

    service.update_employee.assert_called_once_with(
        current_employee=manager,
        employee_id=2,
        first_name="Alice",
        last_name="Martin",
        email="alice.new@test.com",
        role=Role.SUPPORT,
    )


def test_update_employee_passes_none_for_empty_fields(
    monkeypatch,
) -> None:
    controller, service, _session, manager = create_controller()

    updated_employee = create_employee_mock(employee_id=2)
    service.update_employee.return_value = updated_employee

    input_values = iter(
        [
            "2",
            "",
            "",
            "",
            "n",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_employee()

    service.update_employee.assert_called_once_with(
        current_employee=manager,
        employee_id=2,
        first_name=None,
        last_name=None,
        email=None,
        role=None,
    )


def test_update_employee_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _manager = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "invalid",
    )

    controller.update_employee()

    assert (
        "L'identifiant doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.update_employee.assert_not_called()


def test_update_employee_stops_when_new_role_is_invalid(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _manager = create_controller()

    input_values = iter(
        [
            "2",
            "",
            "",
            "",
            "o",
            "99",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_employee()

    assert "Rôle invalide." in capsys.readouterr().out
    service.update_employee.assert_not_called()


# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------


def test_delete_employee_calls_service_when_confirmed(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, manager = create_controller()

    input_values = iter(["2", "o"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_employee()

    assert (
        "Collaborateur supprimé avec succès."
        in capsys.readouterr().out
    )
    service.delete_employee.assert_called_once_with(
        current_employee=manager,
        employee_id=2,
    )


def test_delete_employee_does_not_call_service_when_cancelled(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _manager = create_controller()

    input_values = iter(["2", "n"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_employee()

    assert "Suppression annulée." in capsys.readouterr().out
    service.delete_employee.assert_not_called()


def test_delete_employee_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _manager = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "invalid",
    )

    controller.delete_employee()

    assert (
        "L'identifiant doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.delete_employee.assert_not_called()


def test_delete_employee_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, manager = create_controller()

    service.delete_employee.side_effect = AuthorizationError(
        "Suppression interdite."
    )

    input_values = iter(["2", "o"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_employee()

    assert (
        "Erreur : Suppression interdite."
        in capsys.readouterr().out
    )
    service.delete_employee.assert_called_once_with(
        current_employee=manager,
        employee_id=2,
    )


# ---------------------------------------------------------------------------
# Menu et helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("choice", "method_name"),
    [
        ("1", "list_employees"),
        ("2", "get_employee"),
        ("3", "create_employee"),
        ("4", "update_employee"),
        ("5", "delete_employee"),
    ],
)
def test_run_calls_selected_action(
    monkeypatch,
    choice,
    method_name,
) -> None:
    controller, _service, current_session, _manager = create_controller()

    selected_method = Mock()
    monkeypatch.setattr(
        controller,
        method_name,
        selected_method,
    )

    states = iter([True, False])
    monkeypatch.setattr(
        type(current_session),
        "is_authenticated",
        property(lambda _self: next(states, False)),
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": choice,
    )

    controller.run()

    selected_method.assert_called_once_with()


def test_run_returns_on_zero(monkeypatch) -> None:
    controller, _service, _session, _manager = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "0",
    )

    assert controller.run() is None


def test_run_displays_invalid_choice(
    monkeypatch,
    capsys,
) -> None:
    controller, _service, current_session, _manager = create_controller()

    states = iter([True, False])
    monkeypatch.setattr(
        type(current_session),
        "is_authenticated",
        property(lambda _self: next(states, False)),
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "99",
    )

    controller.run()

    assert "Choix invalide." in capsys.readouterr().out


def test_get_current_employee_raises_when_session_is_empty() -> None:
    controller = EmployeeController(
        employee_service=Mock(),
        current_session=CurrentSession(),
    )

    with pytest.raises(
        RuntimeError,
        match="Aucun collaborateur connecté dans la session",
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

    assert EmployeeController._ask_integer("ID : ") == expected


def test_ask_integer_returns_none_for_invalid_value(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    result = EmployeeController._ask_integer("ID : ")

    assert result is None
    assert (
        "L'identifiant doit être un nombre entier."
        in capsys.readouterr().out
    )


@pytest.mark.parametrize(
    ("choice", "expected"),
    [
        ("1", Role.COMMERCIAL),
        ("2", Role.GESTION),
        ("3", Role.SUPPORT),
    ],
)
def test_ask_role_returns_expected_role(
    monkeypatch,
    choice,
    expected,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": choice,
    )

    assert EmployeeController._ask_role() == expected


def test_ask_role_returns_none_for_invalid_choice(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "99",
    )

    result = EmployeeController._ask_role()

    assert result is None
    assert "Rôle invalide." in capsys.readouterr().out