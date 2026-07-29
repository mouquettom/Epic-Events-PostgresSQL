from sqlalchemy.orm import Session

from app.models.employee import Role
from app.repositories.event_repository import EventRepository
from tests.factories import (
    create_client,
    create_contract,
    create_employee,
    create_event,
)


def test_get_events_without_support(db_session: Session) -> None:
    commercial = create_employee(
        db_session,
        role=Role.COMMERCIAL,
    )
    support = create_employee(
        db_session,
        role=Role.SUPPORT,
    )
    client = create_client(
        db_session,
        commercial=commercial,
    )
    contract = create_contract(
        db_session,
        client=client,
        commercial=commercial,
    )

    assigned_event = create_event(
        db_session,
        contract=contract,
        support=support,
    )
    unassigned_event = create_event(
        db_session,
        contract=contract,
        support=None,
    )

    repository = EventRepository(db_session)

    events = repository.get_events_without_support()

    event_ids = {event.id for event in events}

    assert unassigned_event.id in event_ids
    assert assigned_event.id not in event_ids


def test_get_events_by_support(db_session: Session) -> None:
    commercial = create_employee(
        db_session,
        role=Role.COMMERCIAL,
    )
    support = create_employee(
        db_session,
        role=Role.SUPPORT,
    )
    client = create_client(
        db_session,
        commercial=commercial,
    )
    contract = create_contract(
        db_session,
        client=client,
        commercial=commercial,
    )
    event = create_event(
        db_session,
        contract=contract,
        support=support,
    )

    repository = EventRepository(db_session)

    events = repository.get_by_support_id(support.id)

    assert [stored_event.id for stored_event in events] == [event.id]