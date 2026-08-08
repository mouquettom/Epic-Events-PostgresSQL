from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.client import Client
from app.models.contract import Contract
from app.models.employee import Role
from app.models.event import Event
from main import run_application
from tests.factories import create_client, create_contract
from tests.functional.helpers import seed_employee


def test_commercial_creates_client_and_event_for_signed_contract(
    monkeypatch,
    capsys,
    functional_session_factory: sessionmaker[Session],
) -> None:
    commercial = seed_employee(
        functional_session_factory,
        first_name="Alice",
        last_name="Commercial",
        email="commercial@functional.test",
        password="CommercialPassword123!",
        role=Role.COMMERCIAL,
    )

    # Le contrat est préparé en base car, selon le brief,
    # sa création appartient au service gestion et non au commercial.
    setup_session = functional_session_factory()

    try:
        existing_client = create_client(
            setup_session,
            commercial=commercial,
            company="Entreprise existante",
        )
        signed_contract = create_contract(
            setup_session,
            client=existing_client,
            commercial=commercial,
            is_signed=True,
        )
        contract_id = signed_contract.id
        setup_session.commit()
    finally:
        setup_session.close()

    user_inputs = iter(
        [
            "1",
            "commercial@functional.test",
            # Menu commercial → clients
            "1",
            "3",
            "Jean Dupont",
            "jean.client@functional.test",
            "0601020304",
            "Entreprise Test",
            "0",
            # Menu commercial → événements
            "3",
            "3",
            str(contract_id),
            "15/12/2027 09:00",
            "15/12/2027 18:00",
            "Paris",
            "120",
            "Événement fonctionnel",
            "0",
            # Déconnexion puis fermeture
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
        lambda _message="": "CommercialPassword123!",
    )

    run_application(session_factory=functional_session_factory)

    captured = capsys.readouterr()

    assert "Client créé avec succès" in captured.out
    assert "Événement créé avec succès" in captured.out

    verification_session = functional_session_factory()

    try:
        created_client = verification_session.scalar(
            select(Client).where(
                Client.email == "jean.client@functional.test"
            )
        )
        contract = verification_session.get(Contract, contract_id)
        event = verification_session.scalar(
            select(Event).where(Event.contract_id == contract_id)
        )

        assert created_client is not None
        assert contract is not None
        assert contract.is_signed is True
        assert event is not None
        assert event.contract_id == contract.id
        assert event.location == "Paris"
        assert event.support_id is None
    finally:
        verification_session.close()