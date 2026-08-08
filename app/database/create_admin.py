import logging
from getpass import getpass

import app.models

from app.database.session import SessionLocal
from app.models.employee import Employee, Role
from app.repositories.employee_repository import EmployeeRepository
from app.utils.password import hash_password
from app.utils.logging_config import configure_logging


logger = logging.getLogger(__name__)


def create_first_management_employee() -> None:
    """Crée le premier collaborateur du service gestion."""

    session = SessionLocal()

    try:
        repository = EmployeeRepository(session)

        email = input(
            "Email du premier compte gestion : "
        ).strip().lower()

        if repository.get_by_email(email) is not None:
            print(
                "Un collaborateur utilise déjà cette adresse email."
            )

            logger.warning(
                "Création du premier compte gestion annulée : "
                "adresse email déjà utilisée."
            )

            return

        first_name = input("Prénom : ").strip()
        last_name = input("Nom : ").strip()

        password = getpass("Mot de passe : ")
        password_confirmation = getpass(
            "Confirmez le mot de passe : "
        )

        if password != password_confirmation:
            print(
                "Les mots de passe ne correspondent pas."
            )

            logger.warning(
                "Création du premier compte gestion annulée : "
                "confirmation du mot de passe incorrecte."
            )

            return

        employee = Employee(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=hash_password(password),
            role=Role.GESTION,
        )

        created_employee = repository.create(employee)
        session.commit()

        logger.info(
            "Premier compte gestion créé : employee_id=%s.",
            created_employee.id,
        )

        print(
            "Premier collaborateur GESTION créé avec succès."
        )

    except Exception:
        session.rollback()

        logger.exception(
            "Erreur technique lors de la création "
            "du premier compte gestion."
        )

        raise

    finally:
        session.close()

        logger.debug(
            "Session PostgreSQL de create_admin fermée."
        )


if __name__ == "__main__":
    configure_logging()
    create_first_management_employee()