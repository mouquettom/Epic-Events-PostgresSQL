from getpass import getpass

from sqlalchemy.orm import Session

from app.services.auth_service import AuthService
from app.session.current_session import CurrentSession
from app.utils.exceptions import AuthorizationError


class AuthController:
    """ Gère les interactions liées à l'authentification. """

    def __init__(self, db_session: Session, current_session: CurrentSession) -> None:

        self.auth_service = AuthService(db_session)
        self.current_session = current_session

    def login(self) -> bool:
        print("\n=== Connexion à Epic Events ===")

        email = input("Email : ").strip().lower()
        password = getpass("Mot de passe : ")

        try:
            token = self.auth_service.authenticate(
                email=email,
                password=password,
            )

            employee = self.auth_service.get_current_employee(token)

            self.current_session.login(
                employee=employee,
                access_token=token,
            )

            print(
                f"\nConnexion réussie. "
                f"Bienvenue {employee.first_name} "
                f"{employee.last_name}."
            )
            print(f"Rôle : {employee.role.value}")

            return True

        except AuthorizationError as error:
            print(f"\nErreur : {error}")
            return False

    def logout(self) -> None:
        self.current_session.logout()
        print("\nVous êtes maintenant déconnecté.")