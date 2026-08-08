from datetime import datetime
from unittest.mock import Mock

import pytest

from app.controllers.event_controller import EventController
from app.models.employee import Employee, Role
from app.models.event import Event
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
    EventController,
    Mock,
    CurrentSession,
    Employee,
]:
    """Construit un EventController avec un service simulé."""
    current_session, employee = create_current_session(role)
    event_service = Mock()

    controller = EventController(
        event_service=event_service,
        current_session=current_session,
    )

    return (
        controller,
        event_service,
        current_session,
        employee,
    )


def create_event_mock(
    *,
    event_id: int = 2,
    contract_id: int = 10,
    support_id: int | None = 4,
    start_date: datetime = datetime(2026, 8, 15, 18, 30),
    end_date: datetime = datetime(2026, 8, 15, 23, 0),
    location: str = "Paris",
    attendees: int = 120,
    notes: str = "Événement important",
) -> Event:
    """Crée un faux événement réutilisable."""
    event = Mock(spec=Event)
    event.id = event_id
    event.contract_id = contract_id
    event.support_id = support_id
    event.start_date = start_date
    event.end_date = end_date
    event.location = location
    event.attendees = attendees
    event.notes = notes

    return event


# ---------------------------------------------------------------------------
# Consultation globale
# ---------------------------------------------------------------------------


def test_list_events_displays_events(capsys) -> None:
    controller, service, _session, employee = create_controller()
    event = create_event_mock()
    service.list_events.return_value = [event]

    controller.list_events()

    output = capsys.readouterr().out

    assert "Liste des événements" in output
    assert "Contrat 10" in output
    assert "Paris" in output
    assert "Support : 4" in output
    service.list_events.assert_called_once_with(employee)


def test_list_events_displays_empty_message(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_events.return_value = []

    controller.list_events()

    assert "Aucun événement trouvé." in capsys.readouterr().out
    service.list_events.assert_called_once_with(employee)


def test_list_events_displays_service_error(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_events.side_effect = AuthorizationError(
        "Accès interdit."
    )

    controller.list_events()

    assert "Erreur : Accès interdit." in capsys.readouterr().out
    service.list_events.assert_called_once_with(employee)


def test_get_event_displays_event(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    event = create_event_mock()
    service.get_event.return_value = event

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "2",
    )

    controller.get_event()

    output = capsys.readouterr().out

    assert "=== Événement ===" in output
    assert "ID : 2" in output
    assert "Contrat ID : 10" in output
    assert "Support responsable ID : 4" in output
    assert "Début : 2026-08-15 18:30:00" in output
    assert "Fin : 2026-08-15 23:00:00" in output
    assert "Lieu : Paris" in output
    assert "Participants : 120" in output
    assert "Notes : Événement important" in output

    service.get_event.assert_called_once_with(
        current_employee=employee,
        event_id=2,
    )


def test_get_event_displays_unassigned_support(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    event = create_event_mock(support_id=None)
    service.get_event.return_value = event

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "2",
    )

    controller.get_event()

    assert "Support responsable ID : Non affecté" in capsys.readouterr().out
    service.get_event.assert_called_once_with(
        current_employee=employee,
        event_id=2,
    )


def test_get_event_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    controller.get_event()

    assert (
        "La valeur doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.get_event.assert_not_called()


def test_get_event_displays_not_found_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.get_event.side_effect = NotFoundError(
        "Événement introuvable."
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "999",
    )

    controller.get_event()

    assert (
        "Erreur : Événement introuvable."
        in capsys.readouterr().out
    )
    service.get_event.assert_called_once_with(
        current_employee=employee,
        event_id=999,
    )


# ---------------------------------------------------------------------------
# Création - commercial
# ---------------------------------------------------------------------------


def test_create_event_calls_service(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller(
        Role.COMMERCIAL
    )
    event = create_event_mock(support_id=None)
    service.create_event.return_value = event

    input_values = iter(
        [
            "10",
            "15/08/2026 18:30",
            "15/08/2026 23:00",
            "Paris",
            "120",
            "Événement important",
        ]
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_event()

    output = capsys.readouterr().out

    assert "Création d'un événement" in output
    assert "Événement créé avec succès" in output
    assert "id=2" in output

    service.create_event.assert_called_once_with(
        current_employee=employee,
        contract_id=10,
        start_date=datetime(2026, 8, 15, 18, 30),
        end_date=datetime(2026, 8, 15, 23, 0),
        location="Paris",
        attendees=120,
        notes="Événement important",
    )


def test_create_event_stops_for_invalid_contract_id(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    controller.create_event()

    assert (
        "La valeur doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.create_event.assert_not_called()


def test_create_event_stops_for_invalid_start_date(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    input_values = iter(["10", "date invalide"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_event()

    assert (
        "Format invalide. Utilisez JJ/MM/AAAA HH:MM."
        in capsys.readouterr().out
    )
    service.create_event.assert_not_called()


def test_create_event_stops_for_invalid_end_date(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    input_values = iter(
        [
            "10",
            "15/08/2026 18:30",
            "date invalide",
        ]
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_event()

    assert (
        "Format invalide. Utilisez JJ/MM/AAAA HH:MM."
        in capsys.readouterr().out
    )
    service.create_event.assert_not_called()


def test_create_event_stops_for_invalid_attendees(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    input_values = iter(
        [
            "10",
            "15/08/2026 18:30",
            "15/08/2026 23:00",
            "Paris",
            "abc",
        ]
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_event()

    assert (
        "La valeur doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.create_event.assert_not_called()


def test_create_event_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller(
        Role.COMMERCIAL
    )
    service.create_event.side_effect = AuthorizationError(
        "Création interdite."
    )

    input_values = iter(
        [
            "10",
            "15/08/2026 18:30",
            "15/08/2026 23:00",
            "Paris",
            "120",
            "Notes",
        ]
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_event()

    assert "Erreur : Création interdite." in capsys.readouterr().out
    service.create_event.assert_called_once_with(
        current_employee=employee,
        contract_id=10,
        start_date=datetime(2026, 8, 15, 18, 30),
        end_date=datetime(2026, 8, 15, 23, 0),
        location="Paris",
        attendees=120,
        notes="Notes",
    )


# ---------------------------------------------------------------------------
# Modification - support affecté
# ---------------------------------------------------------------------------


def test_update_event_calls_service(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller(
        Role.SUPPORT
    )
    event = create_event_mock(support_id=employee.id)
    service.update_event.return_value = event

    input_values = iter(
        [
            "2",
            "16/08/2026 19:00",
            "17/08/2026 01:00",
            "Lyon",
            "150",
            "Nouvelles notes",
        ]
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_event()

    assert (
        "Événement 2 mis à jour avec succès."
        in capsys.readouterr().out
    )
    service.update_event.assert_called_once_with(
        current_employee=employee,
        event_id=2,
        start_date=datetime(2026, 8, 16, 19, 0),
        end_date=datetime(2026, 8, 17, 1, 0),
        location="Lyon",
        attendees=150,
        notes="Nouvelles notes",
    )


def test_update_event_passes_none_for_empty_values(
    monkeypatch,
) -> None:
    controller, service, _session, employee = create_controller(
        Role.SUPPORT
    )
    event = create_event_mock(support_id=employee.id)
    service.update_event.return_value = event

    input_values = iter(
        [
            "2",
            "",
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

    controller.update_event()

    service.update_event.assert_called_once_with(
        current_employee=employee,
        event_id=2,
        start_date=None,
        end_date=None,
        location=None,
        attendees=None,
        notes=None,
    )


def test_update_event_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller(
        Role.SUPPORT
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    controller.update_event()

    assert (
        "La valeur doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.update_event.assert_not_called()


def test_update_event_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller(
        Role.SUPPORT
    )
    service.update_event.side_effect = AuthorizationError(
        "Modification interdite."
    )

    input_values = iter(
        [
            "2",
            "",
            "",
            "Lyon",
            "150",
            "",
        ]
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.update_event()

    assert (
        "Erreur : Modification interdite."
        in capsys.readouterr().out
    )
    service.update_event.assert_called_once_with(
        current_employee=employee,
        event_id=2,
        start_date=None,
        end_date=None,
        location="Lyon",
        attendees=150,
        notes=None,
    )


# ---------------------------------------------------------------------------
# Filtres et affectation
# ---------------------------------------------------------------------------


def test_list_events_without_support_displays_events(capsys) -> None:
    controller, service, _session, employee = create_controller(
        Role.GESTION
    )
    event = create_event_mock(support_id=None)
    service.list_events_without_support.return_value = [event]

    controller.list_events_without_support()

    output = capsys.readouterr().out

    assert "Liste des événements" in output
    assert "Support : Non affecté" in output
    service.list_events_without_support.assert_called_once_with(employee)


def test_list_events_without_support_displays_empty_message(capsys) -> None:
    controller, service, _session, employee = create_controller(
        Role.GESTION
    )
    service.list_events_without_support.return_value = []

    controller.list_events_without_support()

    assert "Aucun événement trouvé." in capsys.readouterr().out
    service.list_events_without_support.assert_called_once_with(employee)


def test_list_assigned_events_displays_events(capsys) -> None:
    controller, service, _session, employee = create_controller(
        Role.SUPPORT
    )
    event = create_event_mock(support_id=employee.id)
    service.list_assigned_events.return_value = [event]

    controller.list_assigned_events()

    output = capsys.readouterr().out

    assert "Liste des événements" in output
    assert "Support : 1" in output
    service.list_assigned_events.assert_called_once_with(employee)


def test_list_assigned_events_displays_empty_message(capsys) -> None:
    controller, service, _session, employee = create_controller(
        Role.SUPPORT
    )
    service.list_assigned_events.return_value = []

    controller.list_assigned_events()

    assert "Aucun événement trouvé." in capsys.readouterr().out
    service.list_assigned_events.assert_called_once_with(employee)


def test_assign_support_calls_service(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller(
        Role.GESTION
    )
    event = create_event_mock(
        event_id=2,
        support_id=4,
    )
    service.assign_support.return_value = event

    input_values = iter(["2", "4"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.assign_support()

    assert (
        "Collaborateur support 4 affecté à l'événement 2."
        in capsys.readouterr().out
    )
    service.assign_support.assert_called_once_with(
        current_employee=employee,
        event_id=2,
        support_id=4,
    )


def test_assign_support_stops_for_invalid_event_id(
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

    controller.assign_support()

    assert (
        "La valeur doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.assign_support.assert_not_called()


def test_assign_support_stops_for_invalid_support_id(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller(
        Role.GESTION
    )

    input_values = iter(["2", "abc"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.assign_support()

    assert (
        "La valeur doit être un nombre entier."
        in capsys.readouterr().out
    )
    service.assign_support.assert_not_called()


def test_assign_support_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller(
        Role.GESTION
    )
    service.assign_support.side_effect = AuthorizationError(
        "Affectation interdite."
    )

    input_values = iter(["2", "4"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.assign_support()

    assert (
        "Erreur : Affectation interdite."
        in capsys.readouterr().out
    )
    service.assign_support.assert_called_once_with(
        current_employee=employee,
        event_id=2,
        support_id=4,
    )


# ---------------------------------------------------------------------------
# Menus par rôle
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("choice", "method_name"),
    [
        ("1", "list_events"),
        ("2", "get_event"),
        ("3", "list_events_without_support"),
        ("4", "assign_support"),
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
        ("1", "list_events"),
        ("2", "get_event"),
        ("3", "create_event"),
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
        ("1", "list_events"),
        ("2", "get_event"),
        ("3", "list_assigned_events"),
        ("4", "update_event"),
    ],
)
def test_support_menu_calls_selected_action(
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

    should_return = controller._run_support_menu()

    assert should_return is False
    selected_method.assert_called_once_with()


@pytest.mark.parametrize(
    "method_name",
    [
        "_run_management_menu",
        "_run_commercial_menu",
        "_run_support_menu",
    ],
)
def test_role_menu_returns_on_zero(
    monkeypatch,
    method_name,
) -> None:
    controller, _service, _session, _employee = create_controller()

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "0",
    )

    assert getattr(controller, method_name)() is True


@pytest.mark.parametrize(
    ("role", "menu_method"),
    [
        (Role.GESTION, "_run_management_menu"),
        (Role.COMMERCIAL, "_run_commercial_menu"),
        (Role.SUPPORT, "_run_support_menu"),
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
    support_menu = Mock(return_value=False)

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

    menus = {
        "_run_management_menu": management_menu,
        "_run_commercial_menu": commercial_menu,
        "_run_support_menu": support_menu,
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
    controller = EventController(
        event_service=Mock(),
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

    assert EventController._ask_integer("ID : ") == expected


def test_ask_integer_returns_none_for_invalid_value(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "abc",
    )

    result = EventController._ask_integer("ID : ")

    assert result is None
    assert (
        "La valeur doit être un nombre entier."
        in capsys.readouterr().out
    )


def test_ask_optional_integer_returns_none_for_empty_value(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "   ",
    )

    assert EventController._ask_optional_integer("Valeur : ") is None


def test_ask_optional_integer_returns_integer(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "15",
    )

    assert EventController._ask_optional_integer("Valeur : ") == 15


def test_ask_datetime_returns_datetime(monkeypatch) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "15/08/2026 18:30",
    )

    assert EventController._ask_datetime(
        "Date : "
    ) == datetime(2026, 8, 15, 18, 30)


def test_ask_datetime_returns_none_for_invalid_value(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "invalid",
    )

    result = EventController._ask_datetime("Date : ")

    assert result is None
    assert (
        "Format invalide. Utilisez JJ/MM/AAAA HH:MM."
        in capsys.readouterr().out
    )


def test_ask_optional_datetime_returns_none_for_empty_value(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "",
    )

    assert EventController._ask_optional_datetime("Date : ") is None


def test_ask_optional_datetime_returns_datetime(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "15/08/2026 18:30",
    )

    assert EventController._ask_optional_datetime(
        "Date : "
    ) == datetime(2026, 8, 15, 18, 30)