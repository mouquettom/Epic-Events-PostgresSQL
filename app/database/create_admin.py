from getpass import getpass

import app.models

from app.database.session import SessionLocal
from app.models.employee import Employee, Role
from app.repositories.employee_repository import EmployeeRepository
from app.utils.password import hash_password


def create_first_management_employee() -> None:
    session = SessionLocal()

    try:
        repository = EmployeeRepository(session)

        email = input("Email du premier compte gestion : ").strip().lower()

        if repository.get_by_email(email) is not None:
            print("Un employé utilise déjà cette adresse email.")
            return

        first_name = input("Prénom : ").strip()
        last_name = input("Nom : ").strip()

        password = getpass("Mot de passe : ")
        password_confirmation = getpass("Confirmez le mot de passe : ")

        if password != password_confirmation:
            print("Les mots de passe ne correspondent pas.")
            return

        employee = Employee(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=hash_password(password),
            role=Role.GESTION,
        )

        repository.create(employee)
        session.commit()

        print("Premier employé GESTION créé.")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    create_first_management_employee()