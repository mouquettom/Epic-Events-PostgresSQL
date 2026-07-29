from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models.employee import Role
from app.services.event_service import EventService
from app.utils.exceptions import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)

BASE_START = datetime(2026, 8, 10, 9, 0)
BASE_END = datetime(2026, 8, 10, 18, 0)


def make_employee(
    *,
    employee_id: int = 1,
    role: Role = Role.GESTION,
):
    """Crée un employé minimal utilisable par EventService."""
    return SimpleNamespace(
        id=employee_id,
        first_name="Alice",
        last_name="Martin",
        email="alice@example.com",
        role=role,
    )


def make_contract(
    *,
    contract_id: int = 10,
    commercial_id: int = 1,
    is_signed: bool = True,
):
    """Crée un contrat minimal utilisable par EventService."""
    return SimpleNamespace(
        id=contract_id,
        commercial_id=commercial_id,
        is_signed=is_signed,
    )


def make_event(
    *,
    event_id: int = 20,
    commercial_id: int = 1,
    support_id: int | None = None,
    start_date: datetime = BASE_START,
    end_date: datetime = BASE_END,
    location: str = "Paris",
    attendees: int = 100,
    notes: str = "Notes initiales",
):
    """Crée un événement minimal avec son contrat associé."""
    contract = make_contract(commercial_id=commercial_id)

    return SimpleNamespace(
        id=event_id,
        contract_id=contract.id,
        contract=contract,
        support_id=support_id,
        start_date=start_date,
        end_date=end_date,
        location=location,
        attendees=attendees,
        notes=notes,
    )


@pytest.fixture
def session():
    session_mock = Mock()
    session_mock.commit = Mock()
    session_mock.rollback = Mock()
    return session_mock


@pytest.fixture
def service(session):
    event_service = EventService(session)
    event_service.event_repository = Mock()
    event_service.contract_repository = Mock()
    event_service.employee_repository = Mock()
    return event_service


# ---------------------------------------------------------------------------
# create_event
# ---------------------------------------------------------------------------


def test_create_event_creates_normalized_event_and_commits(
    service,
    session,
) -> None:
    employee = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    contract = make_contract(
        contract_id=10,
        commercial_id=employee.id,
        is_signed=True,
    )
    service.contract_repository.get_by_id.return_value = contract
    service.event_repository.create.side_effect = lambda event: event

    result = service.create_event(
        current_employee=employee,
        contract_id=contract.id,
        start_date=BASE_START,
        end_date=BASE_END,
        location="  Paris Expo  ",
        attendees=150,
        notes="  Installation à 7 h  ",
    )

    assert result.start_date == BASE_START
    assert result.end_date == BASE_END
    assert result.location == "Paris Expo"
    assert result.attendees == 150
    assert result.notes == "Installation à 7 h"
    assert result.contract_id == contract.id
    assert result.support_id is None

    service.contract_repository.get_by_id.assert_called_once_with(contract.id)
    service.event_repository.create.assert_called_once_with(result)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_create_event_uses_empty_normalized_notes(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.COMMERCIAL)
    contract = make_contract(commercial_id=employee.id, is_signed=True)
    service.contract_repository.get_by_id.return_value = contract
    service.event_repository.create.side_effect = lambda event: event

    result = service.create_event(
        current_employee=employee,
        contract_id=contract.id,
        start_date=BASE_START,
        end_date=BASE_END,
        location="Paris",
        attendees=10,
        notes="   ",
    )

    assert result.notes == ""
    session.commit.assert_called_once_with()


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_create_event_requires_commercial_role(
    service,
    session,
    role,
) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Seul un commercial peut créer un événement",
    ):
        service.create_event(
            current_employee=employee,
            contract_id=10,
            start_date=BASE_START,
            end_date=BASE_END,
            location="Paris",
            attendees=100,
        )

    service.contract_repository.get_by_id.assert_not_called()
    service.event_repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_create_event_rejects_unknown_contract(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.COMMERCIAL)
    service.contract_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Contrat introuvable"):
        service.create_event(
            current_employee=employee,
            contract_id=999,
            start_date=BASE_START,
            end_date=BASE_END,
            location="Paris",
            attendees=100,
        )

    service.event_repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_create_event_rejects_contract_owned_by_another_commercial(
    service,
    session,
) -> None:
    employee = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    contract = make_contract(
        commercial_id=2,
        is_signed=True,
    )
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez créer un événement que pour vos propres contrats",
    ):
        service.create_event(
            current_employee=employee,
            contract_id=contract.id,
            start_date=BASE_START,
            end_date=BASE_END,
            location="Paris",
            attendees=100,
        )

    service.event_repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_create_event_rejects_unsigned_contract(
    service,
    session,
) -> None:
    employee = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    contract = make_contract(
        commercial_id=employee.id,
        is_signed=False,
    )
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(
        ValidationError,
        match="Un événement ne peut être créé que pour un contrat signé",
    ):
        service.create_event(
            current_employee=employee,
            contract_id=contract.id,
            start_date=BASE_START,
            end_date=BASE_END,
            location="Paris",
            attendees=100,
        )

    service.event_repository.create.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        (BASE_START, BASE_START),
        (BASE_START, BASE_START - timedelta(minutes=1)),
    ],
)
def test_create_event_rejects_invalid_date_order(
    service,
    session,
    start_date,
    end_date,
) -> None:
    employee = make_employee(role=Role.COMMERCIAL)
    contract = make_contract(
        commercial_id=employee.id,
        is_signed=True,
    )
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(
        ValidationError,
        match="La date de fin doit être postérieure à la date de début",
    ):
        service.create_event(
            current_employee=employee,
            contract_id=contract.id,
            start_date=start_date,
            end_date=end_date,
            location="Paris",
            attendees=100,
        )

    service.event_repository.create.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "location",
    ["", "   "],
)
def test_create_event_rejects_empty_location(
    service,
    session,
    location,
) -> None:
    employee = make_employee(role=Role.COMMERCIAL)
    contract = make_contract(
        commercial_id=employee.id,
        is_signed=True,
    )
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(
        ValidationError,
        match="Le lieu de l'événement est obligatoire",
    ):
        service.create_event(
            current_employee=employee,
            contract_id=contract.id,
            start_date=BASE_START,
            end_date=BASE_END,
            location=location,
            attendees=100,
        )

    service.event_repository.create.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "attendees",
    [0, -1, -100],
)
def test_create_event_rejects_non_positive_attendees(
    service,
    session,
    attendees,
) -> None:
    employee = make_employee(role=Role.COMMERCIAL)
    contract = make_contract(
        commercial_id=employee.id,
        is_signed=True,
    )
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(
        ValidationError,
        match="Le nombre de participants doit être supérieur à zéro",
    ):
        service.create_event(
            current_employee=employee,
            contract_id=contract.id,
            start_date=BASE_START,
            end_date=BASE_END,
            location="Paris",
            attendees=attendees,
        )

    service.event_repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_create_event_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.COMMERCIAL)
    contract = make_contract(
        commercial_id=employee.id,
        is_signed=True,
    )
    service.contract_repository.get_by_id.return_value = contract
    service.event_repository.create.side_effect = RuntimeError("database failure")

    with pytest.raises(RuntimeError, match="database failure"):
        service.create_event(
            current_employee=employee,
            contract_id=contract.id,
            start_date=BASE_START,
            end_date=BASE_END,
            location="Paris",
            attendees=100,
        )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# get_event
# ---------------------------------------------------------------------------


def test_get_event_returns_event_for_management(service) -> None:
    employee = make_employee(role=Role.GESTION)
    event = make_event()
    service.event_repository.get_by_id.return_value = event

    result = service.get_event(employee, event.id)

    assert result is event
    service.event_repository.get_by_id.assert_called_once_with(event.id)


def test_get_event_returns_event_for_owner_commercial(service) -> None:
    employee = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    event = make_event(commercial_id=employee.id)
    service.event_repository.get_by_id.return_value = event

    result = service.get_event(employee, event.id)

    assert result is event


def test_get_event_returns_event_for_assigned_support(service) -> None:
    employee = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event(support_id=employee.id)
    service.event_repository.get_by_id.return_value = event

    result = service.get_event(employee, event.id)

    assert result is event


def test_get_event_rejects_unknown_event(service) -> None:
    service.event_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Événement introuvable"):
        service.get_event(
            make_employee(role=Role.GESTION),
            999,
        )


def test_get_event_rejects_commercial_for_another_contract(
    service,
) -> None:
    employee = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    event = make_event(commercial_id=2)
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez consulter que les événements liés à vos contrats",
    ):
        service.get_event(employee, event.id)


def test_get_event_rejects_unassigned_support(service) -> None:
    employee = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event(support_id=6)
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez consulter que les événements qui vous sont attribués",
    ):
        service.get_event(employee, event.id)


def test_get_event_rejects_unknown_role(service) -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"
    event = make_event()
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter cet événement",
    ):
        service.get_event(employee, event.id)


# ---------------------------------------------------------------------------
# list_events
# ---------------------------------------------------------------------------


def test_list_events_returns_support_events(service) -> None:
    employee = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    events = [
        make_event(event_id=1, support_id=5),
        make_event(event_id=2, support_id=5),
    ]
    service.event_repository.get_by_support_id.return_value = events

    result = service.list_events(employee)

    assert result is events
    service.event_repository.get_by_support_id.assert_called_once_with(5)
    service.event_repository.get_all.assert_not_called()


def test_list_events_returns_all_for_management(service) -> None:
    employee = make_employee(role=Role.GESTION)
    events = [
        make_event(event_id=1, commercial_id=1),
        make_event(event_id=2, commercial_id=2),
    ]
    service.event_repository.get_all.return_value = events

    result = service.list_events(employee)

    assert result is events
    service.event_repository.get_all.assert_called_once_with()
    service.event_repository.get_by_support_id.assert_not_called()


def test_list_events_filters_by_contract_owner_for_commercial(
    service,
) -> None:
    employee = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    own_event = make_event(event_id=1, commercial_id=1)
    other_event = make_event(event_id=2, commercial_id=2)
    service.event_repository.get_all.return_value = [
        own_event,
        other_event,
    ]

    result = service.list_events(employee)

    assert result == [own_event]
    service.event_repository.get_all.assert_called_once_with()


def test_list_events_returns_empty_list_when_commercial_has_no_events(
    service,
) -> None:
    employee = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    service.event_repository.get_all.return_value = [
        make_event(event_id=2, commercial_id=2)
    ]

    result = service.list_events(employee)

    assert result == []


def test_list_events_rejects_unknown_role(service) -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter les événements",
    ):
        service.list_events(employee)

    service.event_repository.get_all.assert_not_called()
    service.event_repository.get_by_support_id.assert_not_called()


# ---------------------------------------------------------------------------
# list_events_without_support
# ---------------------------------------------------------------------------


def test_list_events_without_support_returns_repository_result(
    service,
) -> None:
    employee = make_employee(role=Role.GESTION)
    events = [make_event(support_id=None)]
    service.event_repository.get_events_without_support.return_value = events

    result = service.list_events_without_support(employee)

    assert result is events
    service.event_repository.get_events_without_support.assert_called_once_with()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_list_events_without_support_requires_management(
    service,
    role,
) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        service.list_events_without_support(employee)

    service.event_repository.get_events_without_support.assert_not_called()


# ---------------------------------------------------------------------------
# update_event
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_update_event_updates_all_fields_and_commits(
    service,
    session,
    role,
) -> None:
    employee_id = 5 if role == Role.SUPPORT else 1
    employee = make_employee(
        employee_id=employee_id,
        role=role,
    )
    event = make_event(support_id=employee_id if role == Role.SUPPORT else None)
    service.event_repository.get_by_id.return_value = event
    service.event_repository.update.side_effect = lambda value: value

    new_start = BASE_START + timedelta(days=1)
    new_end = BASE_END + timedelta(days=1)

    result = service.update_event(
        current_employee=employee,
        event_id=event.id,
        start_date=new_start,
        end_date=new_end,
        location="  Lyon  ",
        attendees=250,
        notes="  Nouvelles notes  ",
    )

    assert result is event
    assert event.start_date == new_start
    assert event.end_date == new_end
    assert event.location == "Lyon"
    assert event.attendees == 250
    assert event.notes == "Nouvelles notes"

    service.event_repository.update.assert_called_once_with(event)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_update_event_without_values_keeps_existing_data(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.GESTION)
    event = make_event()
    service.event_repository.get_by_id.return_value = event
    service.event_repository.update.return_value = event

    result = service.update_event(employee, event.id)

    assert result is event
    assert event.start_date == BASE_START
    assert event.end_date == BASE_END
    assert event.location == "Paris"
    assert event.attendees == 100
    assert event.notes == "Notes initiales"
    session.commit.assert_called_once_with()


def test_update_event_can_clear_notes(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.GESTION)
    event = make_event(notes="Anciennes notes")
    service.event_repository.get_by_id.return_value = event
    service.event_repository.update.return_value = event

    result = service.update_event(
        current_employee=employee,
        event_id=event.id,
        notes="   ",
    )

    assert result.notes == ""
    session.commit.assert_called_once_with()


def test_update_event_rejects_unknown_event(
    service,
    session,
) -> None:
    service.event_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Événement introuvable"):
        service.update_event(
            current_employee=make_employee(role=Role.GESTION),
            event_id=999,
            location="Paris",
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL],
)
def test_update_event_rejects_commercial(
    service,
    session,
    role,
) -> None:
    employee = make_employee(
        employee_id=1,
        role=role,
    )
    event = make_event(commercial_id=employee.id)
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à modifier cet événement",
    ):
        service.update_event(
            current_employee=employee,
            event_id=event.id,
            location="Lyon",
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_event_rejects_support_not_assigned_to_event(
    service,
    session,
) -> None:
    employee = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event(support_id=6)
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à modifier cet événement",
    ):
        service.update_event(
            current_employee=employee,
            event_id=event.id,
            location="Lyon",
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_event_rejects_unknown_role(
    service,
    session,
) -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"
    event = make_event()
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à modifier cet événement",
    ):
        service.update_event(
            current_employee=employee,
            event_id=event.id,
            location="Lyon",
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        (BASE_START, BASE_START),
        (BASE_START, BASE_START - timedelta(minutes=1)),
    ],
)
def test_update_event_rejects_invalid_date_order(
    service,
    session,
    start_date,
    end_date,
) -> None:
    employee = make_employee(role=Role.GESTION)
    event = make_event()
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(
        ValidationError,
        match="La date de fin doit être postérieure à la date de début",
    ):
        service.update_event(
            current_employee=employee,
            event_id=event.id,
            start_date=start_date,
            end_date=end_date,
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_event_rejects_new_start_after_existing_end(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.GESTION)
    event = make_event()
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(
        ValidationError,
        match="La date de fin doit être postérieure à la date de début",
    ):
        service.update_event(
            current_employee=employee,
            event_id=event.id,
            start_date=BASE_END + timedelta(hours=1),
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_event_rejects_new_end_before_existing_start(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.GESTION)
    event = make_event()
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(
        ValidationError,
        match="La date de fin doit être postérieure à la date de début",
    ):
        service.update_event(
            current_employee=employee,
            event_id=event.id,
            end_date=BASE_START - timedelta(hours=1),
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "location",
    ["", "   "],
)
def test_update_event_rejects_empty_location(
    service,
    session,
    location,
) -> None:
    employee = make_employee(role=Role.GESTION)
    event = make_event()
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(
        ValidationError,
        match="Le lieu de l'événement est obligatoire",
    ):
        service.update_event(
            current_employee=employee,
            event_id=event.id,
            location=location,
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "attendees",
    [0, -1],
)
def test_update_event_rejects_non_positive_attendees(
    service,
    session,
    attendees,
) -> None:
    employee = make_employee(role=Role.GESTION)
    event = make_event()
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(
        ValidationError,
        match="Le nombre de participants doit être supérieur à zéro",
    ):
        service.update_event(
            current_employee=employee,
            event_id=event.id,
            attendees=attendees,
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_event_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    employee = make_employee(role=Role.GESTION)
    event = make_event()
    service.event_repository.get_by_id.return_value = event
    service.event_repository.update.side_effect = RuntimeError("update failure")

    with pytest.raises(RuntimeError, match="update failure"):
        service.update_event(
            current_employee=employee,
            event_id=event.id,
            location="Lyon",
        )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# assign_support
# ---------------------------------------------------------------------------


def test_assign_support_assigns_support_and_commits(
    service,
    session,
) -> None:
    current_employee = make_employee(role=Role.GESTION)
    event = make_event(support_id=None)
    support = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )

    service.event_repository.get_by_id.return_value = event
    service.employee_repository.get_by_id.return_value = support
    service.event_repository.update.return_value = event

    result = service.assign_support(
        current_employee=current_employee,
        event_id=event.id,
        support_id=support.id,
    )

    assert result is event
    assert event.support_id == support.id
    service.event_repository.update.assert_called_once_with(event)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_assign_support_requires_management(
    service,
    session,
    role,
) -> None:
    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        service.assign_support(
            current_employee=make_employee(role=role),
            event_id=20,
            support_id=5,
        )

    service.event_repository.get_by_id.assert_not_called()
    service.employee_repository.get_by_id.assert_not_called()
    session.commit.assert_not_called()


def test_assign_support_rejects_unknown_event(
    service,
    session,
) -> None:
    service.event_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Événement introuvable"):
        service.assign_support(
            current_employee=make_employee(role=Role.GESTION),
            event_id=999,
            support_id=5,
        )

    service.employee_repository.get_by_id.assert_not_called()
    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_assign_support_rejects_unknown_employee(
    service,
    session,
) -> None:
    event = make_event()
    service.event_repository.get_by_id.return_value = event
    service.employee_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Employé introuvable"):
        service.assign_support(
            current_employee=make_employee(role=Role.GESTION),
            event_id=event.id,
            support_id=999,
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.COMMERCIAL],
)
def test_assign_support_rejects_employee_outside_support(
    service,
    session,
    role,
) -> None:
    event = make_event()
    employee = make_employee(employee_id=5, role=role)
    service.event_repository.get_by_id.return_value = event
    service.employee_repository.get_by_id.return_value = employee

    with pytest.raises(
        ValidationError,
        match="L'employé sélectionné n'appartient pas au service support",
    ):
        service.assign_support(
            current_employee=make_employee(role=Role.GESTION),
            event_id=event.id,
            support_id=employee.id,
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_assign_support_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    event = make_event()
    support = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    service.event_repository.get_by_id.return_value = event
    service.employee_repository.get_by_id.return_value = support
    service.event_repository.update.side_effect = RuntimeError("assignment failure")

    with pytest.raises(RuntimeError, match="assignment failure"):
        service.assign_support(
            current_employee=make_employee(role=Role.GESTION),
            event_id=event.id,
            support_id=support.id,
        )

    assert event.support_id == support.id
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# remove_support
# ---------------------------------------------------------------------------


def test_remove_support_removes_support_and_commits(
    service,
    session,
) -> None:
    event = make_event(support_id=5)
    service.event_repository.get_by_id.return_value = event
    service.event_repository.update.return_value = event

    result = service.remove_support(
        current_employee=make_employee(role=Role.GESTION),
        event_id=event.id,
    )

    assert result is event
    assert event.support_id is None
    service.event_repository.update.assert_called_once_with(event)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_remove_support_requires_management(
    service,
    session,
    role,
) -> None:
    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        service.remove_support(
            current_employee=make_employee(role=role),
            event_id=20,
        )

    service.event_repository.get_by_id.assert_not_called()
    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_remove_support_rejects_unknown_event(
    service,
    session,
) -> None:
    service.event_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Événement introuvable"):
        service.remove_support(
            current_employee=make_employee(role=Role.GESTION),
            event_id=999,
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_remove_support_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    event = make_event(support_id=5)
    service.event_repository.get_by_id.return_value = event
    service.event_repository.update.side_effect = RuntimeError("remove failure")

    with pytest.raises(RuntimeError, match="remove failure"):
        service.remove_support(
            current_employee=make_employee(role=Role.GESTION),
            event_id=event.id,
        )

    assert event.support_id is None
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# delete_event
# ---------------------------------------------------------------------------


def test_delete_event_deletes_and_commits(
    service,
    session,
) -> None:
    event = make_event()
    service.event_repository.get_by_id.return_value = event

    result = service.delete_event(
        current_employee=make_employee(role=Role.GESTION),
        event_id=event.id,
    )

    assert result is None
    service.event_repository.delete.assert_called_once_with(event)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_delete_event_requires_management(
    service,
    session,
    role,
) -> None:
    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        service.delete_event(
            current_employee=make_employee(role=role),
            event_id=20,
        )

    service.event_repository.get_by_id.assert_not_called()
    service.event_repository.delete.assert_not_called()
    session.commit.assert_not_called()


def test_delete_event_rejects_unknown_event(
    service,
    session,
) -> None:
    service.event_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Événement introuvable"):
        service.delete_event(
            current_employee=make_employee(role=Role.GESTION),
            event_id=999,
        )

    service.event_repository.delete.assert_not_called()
    session.commit.assert_not_called()


def test_delete_event_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    event = make_event()
    service.event_repository.get_by_id.return_value = event
    service.event_repository.delete.side_effect = RuntimeError("delete failure")

    with pytest.raises(RuntimeError, match="delete failure"):
        service.delete_event(
            current_employee=make_employee(role=Role.GESTION),
            event_id=event.id,
        )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# Private helpers: retrieval
# ---------------------------------------------------------------------------


def test_get_existing_event_returns_event(service) -> None:
    event = make_event()
    service.event_repository.get_by_id.return_value = event

    result = service._get_existing_event(event.id)

    assert result is event


def test_get_existing_event_raises_not_found(service) -> None:
    service.event_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Événement introuvable"):
        service._get_existing_event(999)


def test_get_existing_contract_returns_contract(service) -> None:
    contract = make_contract()
    service.contract_repository.get_by_id.return_value = contract

    result = service._get_existing_contract(contract.id)

    assert result is contract


def test_get_existing_contract_raises_not_found(service) -> None:
    service.contract_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Contrat introuvable"):
        service._get_existing_contract(999)


def test_get_existing_employee_returns_employee(service) -> None:
    employee = make_employee()
    service.employee_repository.get_by_id.return_value = employee

    result = service._get_existing_employee(employee.id)

    assert result is employee


def test_get_existing_employee_raises_not_found(service) -> None:
    service.employee_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Employé introuvable"):
        service._get_existing_employee(999)


# ---------------------------------------------------------------------------
# Private helpers: authorization
# ---------------------------------------------------------------------------


def test_require_commercial_role_accepts_commercial() -> None:
    employee = make_employee(role=Role.COMMERCIAL)

    assert EventService._require_commercial_role(employee) is None


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.SUPPORT],
)
def test_require_commercial_role_rejects_other_roles(role) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Seul un commercial peut créer un événement",
    ):
        EventService._require_commercial_role(employee)


def test_require_management_role_accepts_management() -> None:
    employee = make_employee(role=Role.GESTION)

    assert EventService._require_management_role(employee) is None


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
        EventService._require_management_role(employee)


def test_require_contract_owner_accepts_owner() -> None:
    employee = make_employee(employee_id=1, role=Role.COMMERCIAL)
    contract = make_contract(commercial_id=employee.id)

    assert EventService._require_contract_owner(employee, contract) is None


def test_require_contract_owner_rejects_wrong_owner() -> None:
    employee = make_employee(employee_id=1, role=Role.COMMERCIAL)
    contract = make_contract(commercial_id=2)

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez créer un événement que pour vos propres contrats",
    ):
        EventService._require_contract_owner(employee, contract)


def test_require_event_access_accepts_management() -> None:
    employee = make_employee(role=Role.GESTION)
    event = make_event()

    assert EventService._require_event_access(employee, event) is None


def test_require_event_access_accepts_owner_commercial() -> None:
    employee = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    event = make_event(commercial_id=employee.id)

    assert EventService._require_event_access(employee, event) is None


def test_require_event_access_rejects_wrong_commercial() -> None:
    employee = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    event = make_event(commercial_id=2)

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez consulter que les événements liés à vos contrats",
    ):
        EventService._require_event_access(employee, event)


def test_require_event_access_accepts_assigned_support() -> None:
    employee = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event(support_id=employee.id)

    assert EventService._require_event_access(employee, event) is None


def test_require_event_access_rejects_unassigned_support() -> None:
    employee = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event(support_id=6)

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez consulter que les événements qui vous sont attribués",
    ):
        EventService._require_event_access(employee, event)


def test_require_event_access_rejects_unknown_role() -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"
    event = make_event()

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter cet événement",
    ):
        EventService._require_event_access(employee, event)


def test_require_event_update_permission_accepts_management() -> None:
    employee = make_employee(role=Role.GESTION)
    event = make_event()

    assert EventService._require_event_update_permission(employee, event) is None


def test_require_event_update_permission_accepts_assigned_support() -> None:
    employee = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event(support_id=employee.id)

    assert EventService._require_event_update_permission(employee, event) is None


@pytest.mark.parametrize(
    ("role", "employee_id", "support_id"),
    [
        (Role.COMMERCIAL, 1, None),
        (Role.SUPPORT, 5, 6),
    ],
)
def test_require_event_update_permission_rejects_unauthorized(
    role,
    employee_id,
    support_id,
) -> None:
    employee = make_employee(
        employee_id=employee_id,
        role=role,
    )
    event = make_event(support_id=support_id)

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à modifier cet événement",
    ):
        EventService._require_event_update_permission(employee, event)


# ---------------------------------------------------------------------------
# Private helper: validation
# ---------------------------------------------------------------------------


def test_validate_event_data_accepts_valid_values() -> None:
    assert (
        EventService._validate_event_data(
            start_date=BASE_START,
            end_date=BASE_END,
            location="Paris",
            attendees=1,
        )
        is None
    )


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        (BASE_START, BASE_START),
        (BASE_START, BASE_START - timedelta(seconds=1)),
    ],
)
def test_validate_event_data_rejects_invalid_date_order(
    start_date,
    end_date,
) -> None:
    with pytest.raises(
        ValidationError,
        match="La date de fin doit être postérieure à la date de début",
    ):
        EventService._validate_event_data(
            start_date=start_date,
            end_date=end_date,
            location="Paris",
            attendees=10,
        )


@pytest.mark.parametrize(
    "location",
    ["", None],
)
def test_validate_event_data_rejects_missing_location(
    location,
) -> None:
    with pytest.raises(
        ValidationError,
        match="Le lieu de l'événement est obligatoire",
    ):
        EventService._validate_event_data(
            start_date=BASE_START,
            end_date=BASE_END,
            location=location,
            attendees=10,
        )


@pytest.mark.parametrize(
    "attendees",
    [0, -1, -100],
)
def test_validate_event_data_rejects_invalid_attendees(
    attendees,
) -> None:
    with pytest.raises(
        ValidationError,
        match="Le nombre de participants doit être supérieur à zéro",
    ):
        EventService._validate_event_data(
            start_date=BASE_START,
            end_date=BASE_END,
            location="Paris",
            attendees=attendees,
        )