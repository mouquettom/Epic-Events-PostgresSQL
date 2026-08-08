from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.employee import Employee, Role
from main import run_application
from tests.functional.helpers import seed_employee


def test_management_can_create_employees(
    monkeypatch,
    capsys,
    functional_session_factory: sessionmaker[Session],
) -> None:

    seed_employee(
        functional_session_factory,
        first_name="Admin",
        last_name="Epic Events",
        email="admin@functional.test",
        password="AdminPassword123!",
        role=Role.GESTION,
    )

    user_inputs = iter(
        [
            "1",  # se connecter
            "admin@functional.test",  # email
            "1",  # gérer les employés
            "3",  # créer un employé
            "Alice",  # prénom
            "Martin",  # nom
            "alice@functional.test",  # email
            "1",  # rôle commercial
            "0",  # retour employés
            "0",  # déconnexion
            "0",  # quitter
        ]
    )

    password_inputs = iter(
        [
            "AdminPassword123!",  # connexion
            "CommercialPassword123!",  # création
            "CommercialPassword123!",  # confirmation
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _message="": next(user_inputs),
    )
    monkeypatch.setattr(
        "app.controllers.auth_controller.getpass",
        lambda _message="": next(password_inputs),
    )
    monkeypatch.setattr(
        "app.controllers.employee_controller.getpass",
        lambda _message="": next(password_inputs),
    )

    run_application(session_factory=functional_session_factory)

    captured = capsys.readouterr()

    assert "Connexion réussie" in captured.out
    assert "Collaborateur créé avec succès" in captured.out

    verification_session = functional_session_factory()

    try:
        employee = verification_session.scalar(
            select(Employee).where(Employee.email == "alice@functional.test")
        )

        assert employee is not None
        assert employee.role == Role.COMMERCIAL

    finally:
        verification_session.close()