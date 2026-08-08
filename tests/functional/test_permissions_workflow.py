from sqlalchemy.orm import Session, sessionmaker

from app.models.employee import Role
from app.repositories.client_repository import ClientRepository
from main import run_application
from tests.factories import create_client
from tests.functional.helpers import seed_employee


def test_commercial_cannot_update_another_commercial_client(
    monkeypatch,
    capsys,
    functional_session_factory: sessionmaker[Session],
) -> None:

    owner = seed_employee(
        functional_session_factory,
        first_name="Alice",
        last_name="Owner",
        email="owner@functional.test",
        password="OwnerPassword123!",
        role=Role.COMMERCIAL,
    )

    other_commercial = seed_employee(
        functional_session_factory,
        first_name="Bob",
        last_name="Other",
        email="other@functional.test",
        password="OtherPassword123!",
        role=Role.COMMERCIAL,
    )

    setup_session = functional_session_factory()

    try:
        client = create_client(
            setup_session,
            commercial=owner,
            company="Original Company",
        )
        client_id = client.id
        setup_session.commit()

    finally:
        setup_session.close()

    user_inputs = iter(
        [
            "1",
            "other@functional.test",
            "1",  # gérer clients
            "4",  # modifier client
            str(client_id),
            "",  # nom inchangé
            "",  # email inchangé
            "",  # téléphone inchangé
            "Unauthorized Company",
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
        lambda _message="": "OtherPassword123!",
    )

    run_application(session_factory=functional_session_factory)

    captured = capsys.readouterr()

    assert "Vous ne pouvez modifier que les clients dont vous êtes responsable" in captured.out

    verification_session = functional_session_factory()

    try:
        repository = ClientRepository(verification_session)
        stored_client = repository.get_by_id(client_id)

        assert stored_client is not None
        assert stored_client.company == "Original Company"

    finally:
        verification_session.close()