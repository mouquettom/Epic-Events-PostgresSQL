from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.controllers.main_menu_controller import MainMenuController
from app.models.employee import Role


class SessionStub:
    """Session minimale permettant de contrôler la boucle du menu."""

    def __init__(
        self,
        *,
        employee=None,
        authentication_states: list[bool] | None = None,
    ) -> None:
        self.current_employee = employee
        self._authentication_states = iter(authentication_states or [True, False])

    @property
    def is_authenticated(self) -> bool:
        return next(self._authentication_states, False)


def create_employee(
    role: Role = Role.GESTION,
):
    """Crée un employé minimal pour les tests du menu."""
    return SimpleNamespace(
        id=1,
        first_name="Alice",
        last_name="Martin",
        email="alice@test.com",
        role=role,
    )


def create_controller(
    *,
    role: Role = Role.GESTION,
    employee=None,
    authentication_states: list[bool] | None = None,
) -> tuple[
    MainMenuController,
    SessionStub,
    Mock,
    Mock,
    Mock,
    Mock,
    Mock,
]:
    """Construit le menu principal avec tous ses contrôleurs simulés."""
    if employee is None:
        employee = create_employee(role)

    current_session = SessionStub(
        employee=employee,
        authentication_states=authentication_states,
    )

    auth_controller = Mock()
    employee_controller = Mock()
    client_controller = Mock()
    contract_controller = Mock()
    event_controller = Mock()

    controller = MainMenuController(
        current_session=current_session,
        auth_controller=auth_controller,
        employee_controller=employee_controller,
        client_controller=client_controller,
        contract_controller=contract_controller,
        event_controller=event_controller,
    )

    return (
        controller,
        current_session,
        auth_controller,
        employee_controller,
        client_controller,
        contract_controller,
        event_controller,
    )


@pytest.mark.parametrize(
    ("role", "menu_method_name"),
    [
        (Role.GESTION, "_run_management_menu"),
        (Role.COMMERCIAL, "_run_commercial_menu"),
        (Role.SUPPORT, "_run_support_menu"),
    ],
)
def test_run_dispatches_to_menu_matching_employee_role(
    monkeypatch,
    role: Role,
    menu_method_name: str,
) -> None:
    (
        controller,
        _session,
        _auth,
        _employee_controller,
        _client_controller,
        _contract_controller,
        _event_controller,
    ) = create_controller(
        role=role,
        authentication_states=[True, False],
    )

    display_header = Mock()
    selected_menu = Mock()

    monkeypatch.setattr(
        controller,
        "_display_header",
        display_header,
    )
    monkeypatch.setattr(
        controller,
        menu_method_name,
        selected_menu,
    )

    controller.run()

    display_header.assert_called_once_with()
    selected_menu.assert_called_once_with()


def test_run_returns_when_authenticated_session_has_no_employee(
    monkeypatch,
) -> None:
    (
        controller,
        _session,
        _auth,
        _employee_controller,
        _client_controller,
        _contract_controller,
        _event_controller,
    ) = create_controller(
        employee=None,
        authentication_states=[True],
    )
    controller.current_session.current_employee = None

    display_header = Mock()
    management_menu = Mock()
    commercial_menu = Mock()
    support_menu = Mock()

    monkeypatch.setattr(
        controller,
        "_display_header",
        display_header,
    )
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
        "_run_support_menu",
        support_menu,
    )

    controller.run()

    display_header.assert_not_called()
    management_menu.assert_not_called()
    commercial_menu.assert_not_called()
    support_menu.assert_not_called()


def test_run_does_nothing_when_session_is_not_authenticated(
    monkeypatch,
) -> None:
    (
        controller,
        _session,
        _auth,
        _employee_controller,
        _client_controller,
        _contract_controller,
        _event_controller,
    ) = create_controller(authentication_states=[False])

    display_header = Mock()
    monkeypatch.setattr(
        controller,
        "_display_header",
        display_header,
    )

    controller.run()

    display_header.assert_not_called()


def test_display_header_displays_connected_employee(capsys) -> None:
    (
        controller,
        _session,
        _auth,
        _employee_controller,
        _client_controller,
        _contract_controller,
        _event_controller,
    ) = create_controller(role=Role.GESTION)

    controller._display_header()

    captured = capsys.readouterr()

    assert "EPIC EVENTS CRM" in captured.out
    assert "Utilisateur : Alice Martin" in captured.out
    assert f"Rôle : {Role.GESTION.value}" in captured.out
    assert "=" * 45 in captured.out


def test_display_header_returns_when_employee_is_missing(
    capsys,
) -> None:
    (
        controller,
        session,
        _auth,
        _employee_controller,
        _client_controller,
        _contract_controller,
        _event_controller,
    ) = create_controller()

    session.current_employee = None

    controller._display_header()

    captured = capsys.readouterr()

    assert captured.out == ""


@pytest.mark.parametrize(
    ("choice", "controller_position"),
    [
        ("1", "employee"),
        ("2", "client"),
        ("3", "contract"),
        ("4", "event"),
    ],
)
def test_management_menu_calls_selected_controller(
    monkeypatch,
    choice: str,
    controller_position: str,
) -> None:
    (
        controller,
        _session,
        auth_controller,
        employee_controller,
        client_controller,
        contract_controller,
        event_controller,
    ) = create_controller(role=Role.GESTION)

    controllers = {
        "employee": employee_controller,
        "client": client_controller,
        "contract": contract_controller,
        "event": event_controller,
    }

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": choice,
    )

    controller._run_management_menu()

    controllers[controller_position].run.assert_called_once_with()
    auth_controller.logout.assert_not_called()


def test_management_menu_logs_out(monkeypatch) -> None:
    (
        controller,
        _session,
        auth_controller,
        employee_controller,
        client_controller,
        contract_controller,
        event_controller,
    ) = create_controller(role=Role.GESTION)

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "0",
    )

    controller._run_management_menu()

    auth_controller.logout.assert_called_once_with()
    employee_controller.run.assert_not_called()
    client_controller.run.assert_not_called()
    contract_controller.run.assert_not_called()
    event_controller.run.assert_not_called()


def test_management_menu_displays_invalid_choice(
    monkeypatch,
    capsys,
) -> None:
    (
        controller,
        _session,
        auth_controller,
        employee_controller,
        client_controller,
        contract_controller,
        event_controller,
    ) = create_controller(role=Role.GESTION)

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "99",
    )

    controller._run_management_menu()

    captured = capsys.readouterr()

    assert "Choix invalide." in captured.out
    auth_controller.logout.assert_not_called()
    employee_controller.run.assert_not_called()
    client_controller.run.assert_not_called()
    contract_controller.run.assert_not_called()
    event_controller.run.assert_not_called()


@pytest.mark.parametrize(
    ("choice", "controller_position"),
    [
        ("1", "client"),
        ("2", "contract"),
        ("3", "event"),
    ],
)
def test_commercial_menu_calls_selected_controller(
    monkeypatch,
    choice: str,
    controller_position: str,
) -> None:
    (
        controller,
        _session,
        auth_controller,
        employee_controller,
        client_controller,
        contract_controller,
        event_controller,
    ) = create_controller(role=Role.COMMERCIAL)

    controllers = {
        "client": client_controller,
        "contract": contract_controller,
        "event": event_controller,
    }

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": choice,
    )

    controller._run_commercial_menu()

    controllers[controller_position].run.assert_called_once_with()
    auth_controller.logout.assert_not_called()
    employee_controller.run.assert_not_called()


def test_commercial_menu_logs_out(monkeypatch) -> None:
    (
        controller,
        _session,
        auth_controller,
        employee_controller,
        client_controller,
        contract_controller,
        event_controller,
    ) = create_controller(role=Role.COMMERCIAL)

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "0",
    )

    controller._run_commercial_menu()

    auth_controller.logout.assert_called_once_with()
    employee_controller.run.assert_not_called()
    client_controller.run.assert_not_called()
    contract_controller.run.assert_not_called()
    event_controller.run.assert_not_called()


def test_commercial_menu_displays_invalid_choice(
    monkeypatch,
    capsys,
) -> None:
    (
        controller,
        _session,
        auth_controller,
        employee_controller,
        client_controller,
        contract_controller,
        event_controller,
    ) = create_controller(role=Role.COMMERCIAL)

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "99",
    )

    controller._run_commercial_menu()

    captured = capsys.readouterr()

    assert "Choix invalide." in captured.out
    auth_controller.logout.assert_not_called()
    employee_controller.run.assert_not_called()
    client_controller.run.assert_not_called()
    contract_controller.run.assert_not_called()
    event_controller.run.assert_not_called()


def test_support_menu_calls_event_controller(
    monkeypatch,
) -> None:
    (
        controller,
        _session,
        auth_controller,
        employee_controller,
        client_controller,
        contract_controller,
        event_controller,
    ) = create_controller(role=Role.SUPPORT)

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "1",
    )

    controller._run_support_menu()

    event_controller.run.assert_called_once_with()
    auth_controller.logout.assert_not_called()
    employee_controller.run.assert_not_called()
    client_controller.run.assert_not_called()
    contract_controller.run.assert_not_called()


def test_support_menu_logs_out(monkeypatch) -> None:
    (
        controller,
        _session,
        auth_controller,
        employee_controller,
        client_controller,
        contract_controller,
        event_controller,
    ) = create_controller(role=Role.SUPPORT)

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "0",
    )

    controller._run_support_menu()

    auth_controller.logout.assert_called_once_with()
    employee_controller.run.assert_not_called()
    client_controller.run.assert_not_called()
    contract_controller.run.assert_not_called()
    event_controller.run.assert_not_called()


def test_support_menu_displays_invalid_choice(
    monkeypatch,
    capsys,
) -> None:
    (
        controller,
        _session,
        auth_controller,
        employee_controller,
        client_controller,
        contract_controller,
        event_controller,
    ) = create_controller(role=Role.SUPPORT)

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "99",
    )

    controller._run_support_menu()

    captured = capsys.readouterr()

    assert "Choix invalide." in captured.out
    auth_controller.logout.assert_not_called()
    employee_controller.run.assert_not_called()
    client_controller.run.assert_not_called()
    contract_controller.run.assert_not_called()
    event_controller.run.assert_not_called()


def test_not_implemented_displays_feature_name(capsys) -> None:
    MainMenuController._not_implemented("Gestion des statistiques")

    captured = capsys.readouterr()

    assert "Gestion des statistiques : fonctionnalité à venir." in captured.out