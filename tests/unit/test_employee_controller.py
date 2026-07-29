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
    """Crée une session applicative contenant un gestionnaire connecté."""
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

    return controller, employee_service, current_session, manager


def test_list_employees_displays_employees(capsys) -> None:
    controller, employee_service, _current_session, manager = create_controller()

    employee = Mock(spec=Employee)
    employee.id = 2
    employee.first_name = "Alice"
    employee.last_name = "Martin"
    employee.email = "alice@test.com"
    employee.role = Role.COMMERCIAL

    employee_service.list_employees.return_value = [employee]

    controller.list_employees()

    captured = capsys.readouterr()

    assert "Liste des employés" in captured.out
    assert "Alice Martin" in captured.out
    assert "alice@test.com" in captured.out
    assert "COMMERCIAL" in captured.out
    employee_service.list_employees.assert_called_once_with(manager)


def test_list_employees_displays_empty_message(capsys) -> None:
    controller, employee_service, _current_session, manager = create_controller()

    employee_service.list_employees.return_value = []

    controller.list_employees()

    captured = capsys.readouterr()

    assert "Aucun employé trouvé" in captured.out
    employee_service.list_employees.assert_called_once_with(manager)


def test_list_employees_displays_service_error(capsys) -> None:
    controller, employee_service, _current_session, manager = create_controller()

    employee_service.list_employees.side_effect = AuthorizationError("Accès interdit.")

    controller.list_employees()

    captured = capsys.readouterr()

    assert "Erreur : Accès interdit." in captured.out
    employee_service.list_employees.assert_called_once_with(manager)


def test_get_employee_displays_employee(monkeypatch, capsys) -> None:
    controller, employee_service, _current_session, manager = create_controller()

    employee = Mock(spec=Employee)
    employee.id = 2
    employee.first_name = "Alice"
    employee.last_name = "Martin"
    employee.email = "alice@test.com"
    employee.role = Role.SUPPORT

    employee_service.get_employee.return_value = employee

    monkeypatch.setattr("builtins.input", lambda _message="": "2")

    controller.get_employee()

    captured = capsys.readouterr()

    assert "Employé" in captured.out
    assert "Alice" in captured.out
    assert "Martin" in captured.out
    assert "alice@test.com" in captured.out
    assert "SUPPORT" in captured.out
    employee_service.get_employee.assert_called_once_with(
        current_employee=manager,
        employee_id=2,
    )


def test_get_employee_rejects_invalid_identifier(monkeypatch, capsys) -> None:
    controller, employee_service, _current_session, _manager = create_controller()

    monkeypatch.setattr("builtins.input", lambda _message="": "abc")

    controller.get_employee()

    captured = capsys.readouterr()

    assert "doit être un nombre entier" in captured.out
    employee_service.get_employee.assert_not_called()


def test_get_employee_displays_not_found_error(monkeypatch, capsys) -> None:
    controller, employee_service, _current_session, manager = create_controller()

    employee_service.get_employee.side_effect = NotFoundError("Employé introuvable.")

    monkeypatch.setattr("builtins.input", lambda _message="": "999")

    controller.get_employee()

    captured = capsys.readouterr()

    assert "Erreur : Employé introuvable." in captured.out
    employee_service.get_employee.assert_called_once_with(
        current_employee=manager,
        employee_id=999,
    )


def test_create_employee_calls_service(monkeypatch, capsys) -> None:
    controller, employee_service, _current_session, manager = create_controller()

    created_employee = Mock(spec=Employee)
    created_employee.id = 2
    created_employee.first_name = "Alice"
    created_employee.last_name = "Martin"
    created_employee.role = Role.COMMERCIAL

    employee_service.create_employee.return_value = created_employee

    input_values = iter(["Alice", "Martin", "alice@test.com", "1"])
    password_values = iter(["Password123!", "Password123!"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )
    monkeypatch.setattr(
        "app.controllers.employee_controller.getpass",
        lambda _message="": next(password_values),
    )

    controller.create_employee()

    captured = capsys.readouterr()

    assert "Employé créé avec succès" in captured.out
    assert "Alice Martin" in captured.out
    assert "COMMERCIAL" in captured.out
    employee_service.create_employee.assert_called_once_with(
        current_employee=manager,
        first_name="Alice",
        last_name="Martin",
        email="alice@test.com",
        password="Password123!",
        role=Role.COMMERCIAL,
    )


def test_create_employee_rejects_password_mismatch(monkeypatch, capsys) -> None:
    controller, employee_service, _current_session, _manager = create_controller()

    input_values = iter(["Alice", "Martin", "alice@test.com", "1"])
    password_values = iter(["Password123!", "DifferentPassword123!"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )
    monkeypatch.setattr(
        "app.controllers.employee_controller.getpass",
        lambda _message="": next(password_values),
    )

    controller.create_employee()

    captured = capsys.readouterr()

    assert "les mots de passe ne correspondent pas" in captured.out
    employee_service.create_employee.assert_not_called()


def test_create_employee_rejects_invalid_role(monkeypatch, capsys) -> None:
    controller, employee_service, _current_session, _manager = create_controller()

    input_values = iter(["Alice", "Martin", "alice@test.com", "99"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_employee()

    captured = capsys.readouterr()

    assert "Rôle invalide" in captured.out
    employee_service.create_employee.assert_not_called()


def test_create_employee_displays_duplicate_error(monkeypatch, capsys) -> None:
    controller, employee_service, _current_session, manager = create_controller()

    employee_service.create_employee.side_effect = DuplicateError(
        "Cet email est déjà utilisé."
    )

    input_values = iter(["Alice", "Martin", "alice@test.com", "3"])
    password_values = iter(["Password123!", "Password123!"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )
    monkeypatch.setattr(
        "app.controllers.employee_controller.getpass",
        lambda _message="": next(password_values),
    )

    controller.create_employee()

    captured = capsys.readouterr()

    assert "Erreur : Cet email est déjà utilisé." in captured.out
    employee_service.create_employee.assert_called_once_with(
        current_employee=manager,
        first_name="Alice",
        last_name="Martin",
        email="alice@test.com",
        password="Password123!",
        role=Role.SUPPORT,
    )


def test_update_employee_calls_service(monkeypatch, capsys) -> None:
    controller, employee_service, _current_session, manager = create_controller()

    updated_employee = Mock(spec=Employee)
    updated_employee.id = 2
    employee_service.update_employee.return_value = updated_employee

    input_values = iter(["2", "Alice", "Martin", "alice.new@test.com", "o", "3"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_employee()

    captured = capsys.readouterr()

    assert "Employé 2 mis à jour avec succès" in captured.out
    employee_service.update_employee.assert_called_once_with(
        current_employee=manager,
        employee_id=2,
        first_name="Alice",
        last_name="Martin",
        email="alice.new@test.com",
        role=Role.SUPPORT,
    )


def test_update_employee_passes_none_for_empty_fields(monkeypatch) -> None:
    controller, employee_service, _current_session, manager = create_controller()

    updated_employee = Mock(spec=Employee)
    updated_employee.id = 2
    employee_service.update_employee.return_value = updated_employee

    input_values = iter(["2", "", "", "", "n"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_employee()

    employee_service.update_employee.assert_called_once_with(
        current_employee=manager,
        employee_id=2,
        first_name=None,
        last_name=None,
        email=None,
        role=None,
    )


def test_update_employee_rejects_invalid_identifier(monkeypatch, capsys) -> None:
    controller, employee_service, _current_session, _manager = create_controller()

    monkeypatch.setattr("builtins.input", lambda _message="": "invalid")

    controller.update_employee()

    captured = capsys.readouterr()

    assert "doit être un nombre entier" in captured.out
    employee_service.update_employee.assert_not_called()


def test_update_employee_stops_when_new_role_is_invalid(monkeypatch, capsys) -> None:
    controller, employee_service, _current_session, _manager = create_controller()

    input_values = iter(["2", "", "", "", "o", "99"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_employee()

    captured = capsys.readouterr()

    assert "Rôle invalide" in captured.out
    employee_service.update_employee.assert_not_called()


def test_delete_employee_calls_service_when_confirmed(monkeypatch, capsys) -> None:
    controller, employee_service, _current_session, manager = create_controller()

    input_values = iter(["2", "o"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_employee()

    captured = capsys.readouterr()

    assert "Employé supprimé avec succès" in captured.out
    employee_service.delete_employee.assert_called_once_with(
        current_employee=manager,
        employee_id=2,
    )


def test_delete_employee_does_not_call_service_when_cancelled(
    monkeypatch, capsys
) -> None:
    controller, employee_service, _current_session, _manager = create_controller()

    input_values = iter(["2", "n"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_employee()

    captured = capsys.readouterr()

    assert "Suppression annulée" in captured.out
    employee_service.delete_employee.assert_not_called()


def test_delete_employee_rejects_invalid_identifier(monkeypatch, capsys) -> None:
    controller, employee_service, _current_session, _manager = create_controller()

    monkeypatch.setattr("builtins.input", lambda _message="": "invalid")

    controller.delete_employee()

    captured = capsys.readouterr()

    assert "doit être un nombre entier" in captured.out
    employee_service.delete_employee.assert_not_called()


def test_run_calls_selected_action_and_returns(monkeypatch) -> None:
    controller, _employee_service, _current_session, _manager = create_controller()

    controller.list_employees = Mock()
    input_values = iter(["1", "0"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.run()

    controller.list_employees.assert_called_once()


def test_run_displays_invalid_choice(monkeypatch, capsys) -> None:
    controller, _employee_service, _current_session, _manager = create_controller()

    input_values = iter(["99", "0"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.run()

    captured = capsys.readouterr()

    assert "Choix invalide" in captured.out


def test_get_current_employee_raises_when_session_is_empty() -> None:
    employee_service = Mock()
    current_session = CurrentSession()
    controller = EmployeeController(
        employee_service=employee_service,
        current_session=current_session,
    )

    with pytest.raises(RuntimeError, match="Aucun employé connecté"):
        controller._get_current_employee()
