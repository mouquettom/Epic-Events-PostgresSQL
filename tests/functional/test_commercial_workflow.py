from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.client import Client
from app.models.contract import Contract
from app.models.employee import Role
from app.models.event import Event
from main import run_application
from tests.functional.helpers import seed_employee


def test_commercial_creates_client_contract_and_event(
    monkeypatch,
    capsys,
    functional_session_factory: sessionmaker[Session],
) -> None:

    seed_employee(
        functional_session_factory,
        first_name="Alice",
        last_name="Commercial",
        email="commercial@functional.test",
        password="CommercialPassword123!",
        role=Role.COMMERCIAL,
    )

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
            # Menu commercial → contrats
            "2",
            "3",
            "1",
            "10000",
            "7500",
            "o",
            "0",
            # Menu commercial → événements
            "3",
            "3",
            "1",
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
    assert "Contrat créé avec succès" in captured.out
    assert "Événement créé avec succès" in captured.out

    verification_session = functional_session_factory()

    try:
        client = verification_session.scalar(
            select(Client).where(Client.email == "jean.client@functional.test")
        )
        contract = verification_session.scalar(select(Contract))
        event = verification_session.scalar(select(Event))

        assert client is not None
        assert contract is not None
        assert event is not None

        assert contract.client_id == client.id
        assert contract.is_signed is True
        assert event.contract_id == contract.id
        assert event.location == "Paris"

    finally:
        verification_session.close()