from datetime import datetime
from unittest.mock import Mock

import pytest

from app.controllers.event_controller import EventController
from app.models.employee import Employee, Role
from app.models.event import Event
from app.session.current_session import CurrentSession
from app.utils.exceptions import AuthorizationError, NotFoundError


def create_current_session() -> tuple[CurrentSession, Employee]:
    """Crée une session contenant un employé connecté."""
    employee = Mock(spec=Employee)
    employee.id = 1
    employee.first_name = "Alice"
    employee.last_name = "Martin"
    employee.email = "alice@test.com"
    employee.role = Role.SUPPORT

    current_session = CurrentSession()
    current_session.login(
        employee=employee,
        access_token="fake-token",
    )

    return current_session, employee


def create_controller() -> tuple[
    EventController,
    Mock,
    CurrentSession,
    Employee,
]:
    """Construit un EventController avec un service simulé."""
    current_session, employee = create_current_session()
    event_service = Mock()

    controller = EventController(
        event_service=event_service,
        current_session=current_session,
    )

    return controller, event_service, current_session, employee


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


def test_list_events_displays_events(capsys) -> None:
    controller, service, _session, employee = create_controller()
    event = create_event_mock()
    service.list_events.return_value = [event]

    controller.list_events()

    captured = capsys.readouterr()

    assert "Liste des événements" in captured.out
    assert "Contrat 10" in captured.out
    assert "Paris" in captured.out
    assert "Support : 4" in captured.out
    service.list_events.assert_called_once_with(employee)


def test_list_events_displays_empty_message(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_events.return_value = []

    controller.list_events()

    captured = capsys.readouterr()

    assert "Aucun événement trouvé." in captured.out
    service.list_events.assert_called_once_with(employee)


def test_list_events_displays_service_error(capsys) -> None:
    controller, service, _session, employee = create_controller()
    service.list_events.side_effect = AuthorizationError("Accès interdit.")

    controller.list_events()

    captured = capsys.readouterr()

    assert "Erreur : Accès interdit." in captured.out
    service.list_events.assert_called_once_with(employee)


def test_get_event_displays_event(monkeypatch, capsys) -> None:
    controller, service, _session, employee = create_controller()
    event = create_event_mock()
    service.get_event.return_value = event

    monkeypatch.setattr("builtins.input", lambda _message="": "2")

    controller.get_event()

    captured = capsys.readouterr()

    assert "=== Événement ===" in captured.out
    assert "ID : 2" in captured.out
    assert "Contrat ID : 10" in captured.out
    assert "Support ID : 4" in captured.out
    assert "Début : 2026-08-15 18:30:00" in captured.out
    assert "Fin : 2026-08-15 23:00:00" in captured.out
    assert "Lieu : Paris" in captured.out
    assert "Participants : 120" in captured.out
    assert "Notes : Événement important" in captured.out
    service.get_event.assert_called_once_with(
        current_employee=employee,
        event_id=2,
    )


def test_get_event_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    monkeypatch.setattr("builtins.input", lambda _message="": "abc")

    controller.get_event()

    captured = capsys.readouterr()

    assert "La valeur doit être un nombre entier." in captured.out
    service.get_event.assert_not_called()


def test_get_event_displays_not_found_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.get_event.side_effect = NotFoundError("Événement introuvable.")

    monkeypatch.setattr("builtins.input", lambda _message="": "999")

    controller.get_event()

    captured = capsys.readouterr()

    assert "Erreur : Événement introuvable." in captured.out
    service.get_event.assert_called_once_with(
        current_employee=employee,
        event_id=999,
    )


def test_create_event_calls_service(monkeypatch, capsys) -> None:
    controller, service, _session, employee = create_controller()
    event = create_event_mock()
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

    captured = capsys.readouterr()

    assert "Création d'un événement" in captured.out
    assert "Événement créé avec succès" in captured.out
    assert "id=2" in captured.out
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
    monkeypatch.setattr("builtins.input", lambda _message="": "abc")

    controller.create_event()

    captured = capsys.readouterr()

    assert "La valeur doit être un nombre entier." in captured.out
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

    captured = capsys.readouterr()

    assert "Format invalide. Utilisez JJ/MM/AAAA HH:MM." in captured.out
    service.create_event.assert_not_called()


def test_create_event_stops_for_invalid_end_date(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()
    input_values = iter(["10", "15/08/2026 18:30", "date invalide"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.create_event()

    captured = capsys.readouterr()

    assert "Format invalide. Utilisez JJ/MM/AAAA HH:MM." in captured.out
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

    captured = capsys.readouterr()

    assert "La valeur doit être un nombre entier." in captured.out
    service.create_event.assert_not_called()


def test_create_event_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.create_event.side_effect = AuthorizationError("Création interdite.")

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

    captured = capsys.readouterr()

    assert "Erreur : Création interdite." in captured.out
    service.create_event.assert_called_once_with(
        current_employee=employee,
        contract_id=10,
        start_date=datetime(2026, 8, 15, 18, 30),
        end_date=datetime(2026, 8, 15, 23, 0),
        location="Paris",
        attendees=120,
        notes="Notes",
    )


def test_update_event_calls_service(monkeypatch, capsys) -> None:
    controller, service, _session, employee = create_controller()
    event = create_event_mock()
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

    captured = capsys.readouterr()

    assert "Événement 2 mis à jour avec succès." in captured.out
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
    controller, service, _session, employee = create_controller()
    event = create_event_mock()
    service.update_event.return_value = event

    input_values = iter(["2", "", "", "", "", ""])
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
    controller, service, _session, _employee = create_controller()
    monkeypatch.setattr("builtins.input", lambda _message="": "abc")

    controller.update_event()

    captured = capsys.readouterr()

    assert "La valeur doit être un nombre entier." in captured.out
    service.update_event.assert_not_called()


def test_update_event_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.update_event.side_effect = AuthorizationError("Modification interdite.")

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

    captured = capsys.readouterr()

    assert "Erreur : Modification interdite." in captured.out
    service.update_event.assert_called_once_with(
        current_employee=employee,
        event_id=2,
        start_date=None,
        end_date=None,
        location="Lyon",
        attendees=150,
        notes=None,
    )


def test_list_events_without_support_displays_events(capsys) -> None:
    controller, service, _session, employee = create_controller()
    event = create_event_mock(support_id=None)
    service.list_events_without_support.return_value = [event]

    controller.list_events_without_support()

    captured = capsys.readouterr()

    assert "Liste des événements" in captured.out
    assert "Support : Non affecté" in captured.out
    service.list_events_without_support.assert_called_once_with(employee)


def test_list_events_without_support_displays_empty_message(
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.list_events_without_support.return_value = []

    controller.list_events_without_support()

    captured = capsys.readouterr()

    assert "Aucun événement trouvé." in captured.out
    service.list_events_without_support.assert_called_once_with(employee)


def test_list_events_without_support_displays_service_error(
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.list_events_without_support.side_effect = AuthorizationError(
        "Accès interdit."
    )

    controller.list_events_without_support()

    captured = capsys.readouterr()

    assert "Erreur : Accès interdit." in captured.out
    service.list_events_without_support.assert_called_once_with(employee)


def test_assign_support_calls_service(monkeypatch, capsys) -> None:
    controller, service, _session, employee = create_controller()
    event = create_event_mock(event_id=2, support_id=4)
    service.assign_support.return_value = event

    input_values = iter(["2", "4"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.assign_support()

    captured = capsys.readouterr()

    assert "Support 4 affecté à l'événement 2." in captured.out
    service.assign_support.assert_called_once_with(
        current_employee=employee,
        event_id=2,
        support_id=4,
    )


def test_assign_support_stops_for_invalid_event_id(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()
    monkeypatch.setattr("builtins.input", lambda _message="": "abc")

    controller.assign_support()

    captured = capsys.readouterr()

    assert "La valeur doit être un nombre entier." in captured.out
    service.assign_support.assert_not_called()


def test_assign_support_stops_for_invalid_support_id(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()
    input_values = iter(["2", "abc"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.assign_support()

    captured = capsys.readouterr()

    assert "La valeur doit être un nombre entier." in captured.out
    service.assign_support.assert_not_called()


def test_assign_support_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.assign_support.side_effect = AuthorizationError("Affectation interdite.")

    input_values = iter(["2", "4"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.assign_support()

    captured = capsys.readouterr()

    assert "Erreur : Affectation interdite." in captured.out
    service.assign_support.assert_called_once_with(
        current_employee=employee,
        event_id=2,
        support_id=4,
    )


def test_remove_support_calls_service(monkeypatch, capsys) -> None:
    controller, service, _session, employee = create_controller()
    event = create_event_mock(event_id=2, support_id=None)
    service.remove_support.return_value = event

    monkeypatch.setattr("builtins.input", lambda _message="": "2")

    controller.remove_support()

    captured = capsys.readouterr()

    assert "Support retiré de l'événement 2." in captured.out
    service.remove_support.assert_called_once_with(
        current_employee=employee,
        event_id=2,
    )


def test_remove_support_stops_for_invalid_event_id(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()
    monkeypatch.setattr("builtins.input", lambda _message="": "abc")

    controller.remove_support()

    captured = capsys.readouterr()

    assert "La valeur doit être un nombre entier." in captured.out
    service.remove_support.assert_not_called()


def test_remove_support_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.remove_support.side_effect = AuthorizationError("Retrait interdit.")

    monkeypatch.setattr("builtins.input", lambda _message="": "2")

    controller.remove_support()

    captured = capsys.readouterr()

    assert "Erreur : Retrait interdit." in captured.out
    service.remove_support.assert_called_once_with(
        current_employee=employee,
        event_id=2,
    )


def test_delete_event_calls_service_when_confirmed(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()

    input_values = iter(["2", "o"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_event()

    captured = capsys.readouterr()

    assert "Événement supprimé avec succès." in captured.out
    service.delete_event.assert_called_once_with(
        current_employee=employee,
        event_id=2,
    )


def test_delete_event_does_not_call_service_when_cancelled(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()

    input_values = iter(["2", "n"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_event()

    captured = capsys.readouterr()

    assert "Suppression annulée." in captured.out
    service.delete_event.assert_not_called()


def test_delete_event_rejects_invalid_identifier(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, _employee = create_controller()
    monkeypatch.setattr("builtins.input", lambda _message="": "abc")

    controller.delete_event()

    captured = capsys.readouterr()

    assert "La valeur doit être un nombre entier." in captured.out
    service.delete_event.assert_not_called()


def test_delete_event_displays_service_error(
    monkeypatch,
    capsys,
) -> None:
    controller, service, _session, employee = create_controller()
    service.delete_event.side_effect = AuthorizationError("Suppression interdite.")

    input_values = iter(["2", "o"])
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(input_values),
    )

    controller.delete_event()

    captured = capsys.readouterr()

    assert "Erreur : Suppression interdite." in captured.out
    service.delete_event.assert_called_once_with(
        current_employee=employee,
        event_id=2,
    )


@pytest.mark.parametrize(
    ("choice", "method_name"),
    [
        ("1", "list_events"),
        ("2", "get_event"),
        ("3", "create_event"),
        ("4", "update_event"),
        ("5", "list_events_without_support"),
        ("6", "assign_support"),
        ("7", "remove_support"),
        ("8", "delete_event"),
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


def test_run_displays_invalid_choice(monkeypatch, capsys) -> None:
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
    controller = EventController(
        event_service=Mock(),
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

    assert EventController._ask_integer("ID : ") == expected


def test_ask_integer_returns_none_for_invalid_value(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _message="": "abc")

    result = EventController._ask_integer("ID : ")

    captured = capsys.readouterr()

    assert result is None
    assert "La valeur doit être un nombre entier." in captured.out


def test_ask_optional_integer_returns_none_for_empty_value(
    monkeypatch,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _message="": "   ")

    result = EventController._ask_optional_integer("Nombre : ")

    assert result is None


def test_ask_optional_integer_returns_integer(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _message="": "150")

    result = EventController._ask_optional_integer("Nombre : ")

    assert result == 150


def test_ask_optional_integer_returns_none_for_invalid_value(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _message="": "abc")

    result = EventController._ask_optional_integer("Nombre : ")

    captured = capsys.readouterr()

    assert result is None
    assert "La valeur doit être un nombre entier." in captured.out


def test_ask_datetime_returns_datetime(monkeypatch) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "15/08/2026 18:30",
    )

    result = EventController._ask_datetime("Date : ")

    assert result == datetime(2026, 8, 15, 18, 30)


def test_ask_datetime_returns_none_for_invalid_value(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "2026-08-15",
    )

    result = EventController._ask_datetime("Date : ")

    captured = capsys.readouterr()

    assert result is None
    assert "Format invalide. Utilisez JJ/MM/AAAA HH:MM." in captured.out


def test_ask_optional_datetime_returns_none_for_empty_value(
    monkeypatch,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _message="": "   ")

    result = EventController._ask_optional_datetime("Date : ")

    assert result is None


def test_ask_optional_datetime_returns_datetime(monkeypatch) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "15/08/2026 18:30",
    )

    result = EventController._ask_optional_datetime("Date : ")

    assert result == datetime(2026, 8, 15, 18, 30)


def test_ask_optional_datetime_returns_none_for_invalid_value(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": "date invalide",
    )

    result = EventController._ask_optional_datetime("Date : ")

    captured = capsys.readouterr()

    assert result is None
    assert "Format invalide. Utilisez JJ/MM/AAAA HH:MM." in captured.out


def test_display_event_displays_unassigned_support(capsys) -> None:
    event = create_event_mock(support_id=None)

    EventController._display_event(event)

    captured = capsys.readouterr()

    assert "Support ID : Non affecté" in captured.out


def test_display_event_list_displays_empty_message(capsys) -> None:
    EventController._display_event_list([])

    captured = capsys.readouterr()

    assert "Aucun événement trouvé." in captured.out


def test_display_event_list_displays_assigned_and_unassigned_support(
    capsys,
) -> None:
    assigned_event = create_event_mock(
        event_id=1,
        support_id=4,
    )
    unassigned_event = create_event_mock(
        event_id=2,
        support_id=None,
    )

    EventController._display_event_list([assigned_event, unassigned_event])

    captured = capsys.readouterr()

    assert "Liste des événements" in captured.out
    assert "Support : 4" in captured.out
    assert "Support : Non affecté" in captured.out