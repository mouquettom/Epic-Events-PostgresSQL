from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from app.models.employee import Role
from app.repositories.event_repository import EventRepository
from main import run_application
from tests.factories import (
    create_client,
    create_contract,
    create_event,
)
from tests.functional.helpers import seed_employee


def test_support_updates_assigned_event(
    monkeypatch,
    capsys,
    functional_session_factory: sessionmaker[Session],
) -> None:

    commercial = seed_employee(
        functional_session_factory,
        first_name="Alice",
        last_name="Commercial",
        email="commercial@support.test",
        password="CommercialPassword123!",
        role=Role.COMMERCIAL,
    )

    support = seed_employee(
        functional_session_factory,
        first_name="Bob",
        last_name="Support",
        email="support@functional.test",
        password="SupportPassword123!",
        role=Role.SUPPORT,
    )

    setup_session = functional_session_factory()

    try:
        client = create_client(
            setup_session,
            commercial=commercial,
        )
        contract = create_contract(
            setup_session,
            client=client,
            commercial=commercial,
            is_signed=True,
        )
        event = create_event(
            setup_session,
            contract=contract,
            support=support,
            start_date=datetime.now(UTC) + timedelta(days=10),
        )

        event_id = event.id
        setup_session.commit()

    finally:
        setup_session.close()

    user_inputs = iter(
        [
            "1",
            "support@functional.test",
            "3",  # menu principal support → événements
            "4",  # modifier
            str(event_id),
            "",  # début inchangé
            "",  # fin inchangée
            "Lyon",
            "200",
            "Informations mises à jour",
            "0",
            "0",
            "0",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(user_inputs),
    )
    monkeypatch.setattr(
        "app.controllers.auth_controller.getpass",
        lambda _message="": "SupportPassword123!",
    )

    run_application(session_factory=functional_session_factory)

    captured = capsys.readouterr()

    assert "mis à jour avec succès" in captured.out

    verification_session = functional_session_factory()

    try:
        repository = EventRepository(verification_session)
        stored_event = repository.get_by_id(event_id)

        assert stored_event is not None
        assert stored_event.location == "Lyon"
        assert stored_event.attendees == 200
        assert stored_event.notes == ("Informations mises à jour")

    finally:
        verification_session.close()