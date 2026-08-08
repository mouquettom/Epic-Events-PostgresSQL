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


BASE_START = datetime(2026, 8, 15, 18, 30)
BASE_END = datetime(2026, 8, 15, 23, 0)


def make_employee(
    *,
    employee_id: int = 1,
    role: Role = Role.COMMERCIAL,
):
    """Crée un collaborateur minimal pour les tests du service."""
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
    """Crée un contrat minimal pour les tests du service."""
    return SimpleNamespace(
        id=contract_id,
        commercial_id=commercial_id,
        is_signed=is_signed,
    )


def make_event(
    *,
    event_id: int = 20,
    contract_id: int = 10,
    support_id: int | None = None,
    start_date: datetime = BASE_START,
    end_date: datetime = BASE_END,
    location: str = "Paris",
    attendees: int = 100,
    notes: str = "Notes",
):
    """Crée un événement minimal pour les tests du service."""
    return SimpleNamespace(
        id=event_id,
        contract_id=contract_id,
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


def test_create_event_creates_event_for_signed_owned_contract(
    service,
    session,
) -> None:
    commercial = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    contract = make_contract(
        contract_id=10,
        commercial_id=commercial.id,
        is_signed=True,
    )

    service.contract_repository.get_by_id.return_value = contract
    service.event_repository.create.side_effect = lambda event: event

    result = service.create_event(
        current_employee=commercial,
        contract_id=contract.id,
        start_date=BASE_START,
        end_date=BASE_END,
        location="  Paris  ",
        attendees=120,
        notes="  Important  ",
    )

    assert result.contract_id == contract.id
    assert result.support_id is None
    assert result.start_date == BASE_START
    assert result.end_date == BASE_END
    assert result.location == "Paris"
    assert result.attendees == 120
    assert result.notes == "Important"

    service.contract_repository.get_by_id.assert_called_once_with(
        contract.id
    )
    service.event_repository.create.assert_called_once_with(result)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


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
    commercial = make_employee(role=Role.COMMERCIAL)
    service.contract_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Contrat introuvable"):
        service.create_event(
            current_employee=commercial,
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
    commercial = make_employee(
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
        match="Vous ne pouvez créer un événement que pour "
        "un contrat associé à l'un de vos clients",
    ):
        service.create_event(
            current_employee=commercial,
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
    commercial = make_employee(role=Role.COMMERCIAL)
    contract = make_contract(
        commercial_id=commercial.id,
        is_signed=False,
    )
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(
        ValidationError,
        match="Un événement ne peut être créé que pour un contrat signé",
    ):
        service.create_event(
            current_employee=commercial,
            contract_id=contract.id,
            start_date=BASE_START,
            end_date=BASE_END,
            location="Paris",
            attendees=100,
        )

    service.event_repository.create.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("start_date", "end_date", "location", "attendees", "message"),
    [
        (
            BASE_START,
            BASE_START,
            "Paris",
            100,
            "La date de fin doit être postérieure à la date de début",
        ),
        (
            BASE_START,
            BASE_END,
            "   ",
            100,
            "Le lieu de l'événement est obligatoire",
        ),
        (
            BASE_START,
            BASE_END,
            "Paris",
            0,
            "Le nombre de participants doit être supérieur à zéro",
        ),
    ],
)
def test_create_event_rejects_invalid_event_data(
    service,
    session,
    start_date,
    end_date,
    location,
    attendees,
    message,
) -> None:
    commercial = make_employee(role=Role.COMMERCIAL)
    contract = make_contract(
        commercial_id=commercial.id,
        is_signed=True,
    )
    service.contract_repository.get_by_id.return_value = contract

    with pytest.raises(ValidationError, match=message):
        service.create_event(
            current_employee=commercial,
            contract_id=contract.id,
            start_date=start_date,
            end_date=end_date,
            location=location,
            attendees=attendees,
        )

    service.event_repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_create_event_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    commercial = make_employee(role=Role.COMMERCIAL)
    contract = make_contract(
        commercial_id=commercial.id,
        is_signed=True,
    )
    service.contract_repository.get_by_id.return_value = contract
    service.event_repository.create.side_effect = RuntimeError(
        "database failure"
    )

    with pytest.raises(RuntimeError, match="database failure"):
        service.create_event(
            current_employee=commercial,
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


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.COMMERCIAL, Role.SUPPORT],
)
def test_get_event_is_available_to_all_valid_roles(
    service,
    role,
) -> None:
    employee = make_employee(role=role)
    event = make_event()
    service.event_repository.get_by_id.return_value = event

    result = service.get_event(
        current_employee=employee,
        event_id=event.id,
    )

    assert result is event
    service.event_repository.get_by_id.assert_called_once_with(
        event.id
    )


def test_get_event_rejects_unknown_event(service) -> None:
    service.event_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Événement introuvable"):
        service.get_event(
            current_employee=make_employee(role=Role.GESTION),
            event_id=999,
        )


def test_get_event_rejects_unknown_role_before_lookup(service) -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter les événements",
    ):
        service.get_event(
            current_employee=employee,
            event_id=20,
        )

    service.event_repository.get_by_id.assert_not_called()


# ---------------------------------------------------------------------------
# list_events
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.COMMERCIAL, Role.SUPPORT],
)
def test_list_events_returns_all_events_for_valid_roles(
    service,
    role,
) -> None:
    employee = make_employee(role=role)
    events = [
        make_event(event_id=1),
        make_event(event_id=2),
    ]
    service.event_repository.get_all.return_value = events

    result = service.list_events(employee)

    assert result is events
    service.event_repository.get_all.assert_called_once_with()


def test_list_events_rejects_unknown_role(service) -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter les événements",
    ):
        service.list_events(employee)

    service.event_repository.get_all.assert_not_called()


# ---------------------------------------------------------------------------
# list_events_without_support
# ---------------------------------------------------------------------------


def test_list_events_without_support_returns_repository_result(
    service,
) -> None:
    manager = make_employee(role=Role.GESTION)
    events = [
        make_event(event_id=1, support_id=None),
        make_event(event_id=2, support_id=None),
    ]
    service.event_repository.get_events_without_support.return_value = (
        events
    )

    result = service.list_events_without_support(manager)

    assert result is events
    service.event_repository.get_events_without_support.assert_called_once_with()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_list_events_without_support_requires_management_role(
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
# list_assigned_events
# ---------------------------------------------------------------------------


def test_list_assigned_events_returns_support_events(
    service,
) -> None:
    support = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    events = [
        make_event(event_id=1, support_id=5),
        make_event(event_id=2, support_id=5),
    ]
    service.event_repository.get_by_support_id.return_value = events

    result = service.list_assigned_events(support)

    assert result is events
    service.event_repository.get_by_support_id.assert_called_once_with(
        support.id
    )


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.COMMERCIAL],
)
def test_list_assigned_events_requires_support_role(
    service,
    role,
) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service support",
    ):
        service.list_assigned_events(employee)

    service.event_repository.get_by_support_id.assert_not_called()


# ---------------------------------------------------------------------------
# update_event
# ---------------------------------------------------------------------------


def test_update_event_by_assigned_support_updates_all_fields(
    service,
    session,
) -> None:
    support = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event(
        support_id=support.id,
    )
    service.event_repository.get_by_id.return_value = event
    service.event_repository.update.side_effect = lambda value: value

    new_start = BASE_START + timedelta(days=1)
    new_end = BASE_END + timedelta(days=1)

    result = service.update_event(
        current_employee=support,
        event_id=event.id,
        start_date=new_start,
        end_date=new_end,
        location="  Lyon  ",
        attendees=150,
        notes="  Nouvelles notes  ",
    )

    assert result is event
    assert event.start_date == new_start
    assert event.end_date == new_end
    assert event.location == "Lyon"
    assert event.attendees == 150
    assert event.notes == "Nouvelles notes"

    service.event_repository.update.assert_called_once_with(event)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_update_event_without_values_keeps_existing_data(
    service,
    session,
) -> None:
    support = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event(
        support_id=support.id,
    )
    service.event_repository.get_by_id.return_value = event
    service.event_repository.update.return_value = event

    result = service.update_event(
        current_employee=support,
        event_id=event.id,
    )

    assert result is event
    assert event.start_date == BASE_START
    assert event.end_date == BASE_END
    assert event.location == "Paris"
    assert event.attendees == 100
    assert event.notes == "Notes"
    session.commit.assert_called_once_with()


@pytest.mark.parametrize(
    ("role", "employee_id", "support_id", "message"),
    [
        (
            Role.GESTION,
            1,
            1,
            "Seul le service support peut modifier",
        ),
        (
            Role.COMMERCIAL,
            1,
            1,
            "Seul le service support peut modifier",
        ),
        (
            Role.SUPPORT,
            5,
            6,
            "Vous ne pouvez modifier que les événements "
            "dont vous êtes responsable",
        ),
    ],
)
def test_update_event_rejects_unauthorized_employee(
    service,
    session,
    role,
    employee_id,
    support_id,
    message,
) -> None:
    employee = make_employee(
        employee_id=employee_id,
        role=role,
    )
    event = make_event(
        support_id=support_id,
    )
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(AuthorizationError, match=message):
        service.update_event(
            current_employee=employee,
            event_id=event.id,
            location="Lyon",
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_event_rejects_unknown_event(
    service,
    session,
) -> None:
    service.event_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Événement introuvable"):
        service.update_event(
            current_employee=make_employee(
                role=Role.SUPPORT
            ),
            event_id=999,
            location="Lyon",
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("start_date", "end_date", "location", "attendees", "message"),
    [
        (
            BASE_START,
            BASE_START,
            None,
            None,
            "La date de fin doit être postérieure à la date de début",
        ),
        (
            None,
            None,
            "   ",
            None,
            "Le lieu de l'événement est obligatoire",
        ),
        (
            None,
            None,
            None,
            0,
            "Le nombre de participants doit être supérieur à zéro",
        ),
    ],
)
def test_update_event_rejects_invalid_data(
    service,
    session,
    start_date,
    end_date,
    location,
    attendees,
    message,
) -> None:
    support = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event(
        support_id=support.id,
    )
    service.event_repository.get_by_id.return_value = event

    with pytest.raises(ValidationError, match=message):
        service.update_event(
            current_employee=support,
            event_id=event.id,
            start_date=start_date,
            end_date=end_date,
            location=location,
            attendees=attendees,
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_event_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    support = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event(
        support_id=support.id,
    )
    service.event_repository.get_by_id.return_value = event
    service.event_repository.update.side_effect = RuntimeError(
        "update failure"
    )

    with pytest.raises(RuntimeError, match="update failure"):
        service.update_event(
            current_employee=support,
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
    manager = make_employee(
        employee_id=1,
        role=Role.GESTION,
    )
    support = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event(
        event_id=20,
        support_id=None,
    )

    service.event_repository.get_by_id.return_value = event
    service.employee_repository.get_by_id.return_value = support
    service.event_repository.update.side_effect = lambda value: value

    result = service.assign_support(
        current_employee=manager,
        event_id=event.id,
        support_id=support.id,
    )

    assert result is event
    assert event.support_id == support.id

    service.event_repository.get_by_id.assert_called_once_with(event.id)
    service.employee_repository.get_by_id.assert_called_once_with(
        support.id
    )
    service.event_repository.update.assert_called_once_with(event)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.COMMERCIAL, Role.SUPPORT],
)
def test_assign_support_requires_management_role(
    service,
    session,
    role,
) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service gestion",
    ):
        service.assign_support(
            current_employee=employee,
            event_id=20,
            support_id=5,
        )

    service.event_repository.get_by_id.assert_not_called()
    service.employee_repository.get_by_id.assert_not_called()
    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_assign_support_rejects_unknown_event(
    service,
    session,
) -> None:
    manager = make_employee(role=Role.GESTION)
    service.event_repository.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Événement introuvable"):
        service.assign_support(
            current_employee=manager,
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
    manager = make_employee(role=Role.GESTION)
    event = make_event()
    service.event_repository.get_by_id.return_value = event
    service.employee_repository.get_by_id.return_value = None

    with pytest.raises(
        NotFoundError,
        match="Collaborateur introuvable",
    ):
        service.assign_support(
            current_employee=manager,
            event_id=event.id,
            support_id=999,
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.COMMERCIAL],
)
def test_assign_support_rejects_non_support_employee(
    service,
    session,
    role,
) -> None:
    manager = make_employee(role=Role.GESTION)
    employee = make_employee(
        employee_id=5,
        role=role,
    )
    event = make_event()

    service.event_repository.get_by_id.return_value = event
    service.employee_repository.get_by_id.return_value = employee

    with pytest.raises(
        ValidationError,
        match="n'appartient pas au service support",
    ):
        service.assign_support(
            current_employee=manager,
            event_id=event.id,
            support_id=employee.id,
        )

    service.event_repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_assign_support_rolls_back_when_repository_fails(
    service,
    session,
) -> None:
    manager = make_employee(role=Role.GESTION)
    support = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event()

    service.event_repository.get_by_id.return_value = event
    service.employee_repository.get_by_id.return_value = support
    service.event_repository.update.side_effect = RuntimeError(
        "assignment failure"
    )

    with pytest.raises(RuntimeError, match="assignment failure"):
        service.assign_support(
            current_employee=manager,
            event_id=event.id,
            support_id=support.id,
        )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def test_get_existing_event_returns_event(service) -> None:
    event = make_event()
    service.event_repository.get_by_id.return_value = event

    result = service._get_existing_event(event.id)

    assert result is event
    service.event_repository.get_by_id.assert_called_once_with(event.id)


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
    employee = make_employee(employee_id=5, role=Role.SUPPORT)
    service.employee_repository.get_by_id.return_value = employee

    result = service._get_existing_employee(employee.id)

    assert result is employee


def test_get_existing_employee_raises_not_found(service) -> None:
    service.employee_repository.get_by_id.return_value = None

    with pytest.raises(
        NotFoundError,
        match="Collaborateur introuvable",
    ):
        service._get_existing_employee(999)


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.COMMERCIAL, Role.SUPPORT],
)
def test_require_valid_role_accepts_application_roles(role) -> None:
    employee = make_employee(role=role)

    assert EventService._require_valid_role(employee) is None


def test_require_valid_role_rejects_unknown_role() -> None:
    employee = make_employee()
    employee.role = "UNKNOWN"

    with pytest.raises(
        AuthorizationError,
        match="Vous n'êtes pas autorisé à consulter les événements",
    ):
        EventService._require_valid_role(employee)


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


def test_require_support_role_accepts_support() -> None:
    employee = make_employee(role=Role.SUPPORT)

    assert EventService._require_support_role(employee) is None


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.COMMERCIAL],
)
def test_require_support_role_rejects_other_roles(role) -> None:
    employee = make_employee(role=role)

    with pytest.raises(
        AuthorizationError,
        match="Cette action est réservée au service support",
    ):
        EventService._require_support_role(employee)


def test_require_contract_owner_accepts_owner() -> None:
    commercial = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    contract = make_contract(
        commercial_id=1,
    )

    assert EventService._require_contract_owner(
        commercial,
        contract,
    ) is None


def test_require_contract_owner_rejects_wrong_commercial() -> None:
    commercial = make_employee(
        employee_id=1,
        role=Role.COMMERCIAL,
    )
    contract = make_contract(
        commercial_id=2,
    )

    with pytest.raises(
        AuthorizationError,
        match="Vous ne pouvez créer un événement que pour "
        "un contrat associé à l'un de vos clients",
    ):
        EventService._require_contract_owner(
            commercial,
            contract,
        )


def test_require_assigned_support_accepts_assigned_support() -> None:
    support = make_employee(
        employee_id=5,
        role=Role.SUPPORT,
    )
    event = make_event(
        support_id=5,
    )

    assert EventService._require_assigned_support(
        support,
        event,
    ) is None


@pytest.mark.parametrize(
    ("role", "employee_id", "support_id", "message"),
    [
        (
            Role.GESTION,
            1,
            1,
            "Seul le service support peut modifier",
        ),
        (
            Role.COMMERCIAL,
            1,
            1,
            "Seul le service support peut modifier",
        ),
        (
            Role.SUPPORT,
            5,
            6,
            "Vous ne pouvez modifier que les événements "
            "dont vous êtes responsable",
        ),
    ],
)
def test_require_assigned_support_rejects_unauthorized(
    role,
    employee_id,
    support_id,
    message,
) -> None:
    employee = make_employee(
        employee_id=employee_id,
        role=role,
    )
    event = make_event(
        support_id=support_id,
    )

    with pytest.raises(AuthorizationError, match=message):
        EventService._require_assigned_support(
            employee,
            event,
        )


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
        (
            BASE_START,
            BASE_START - timedelta(seconds=1),
        ),
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