from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.utils.exceptions import AuthorizationError
from app.utils.jwt import create_access_token, decode_access_token
from app.utils.password import verify_password


class AuthService:
    """ Gère l’authentification des employés. """

    def __init__(self, session: Session) -> None:
        self.employee_repository = EmployeeRepository(session)

    def authenticate(self, email: str, password: str) -> str:
        normalized_email = email.strip().lower()

        employee = self.employee_repository.get_by_email(normalized_email)

        if employee is None:
            raise AuthorizationError("Email ou mot de passe incorrect.")

        if not verify_password(password, employee.password_hash):
            raise AuthorizationError("Email ou mot de passe incorrect.")

        return create_access_token(employee.id)

    def get_current_employee(self, token: str) -> Employee:
        try:
            employee_id = decode_access_token(token)
        except Exception as error:
            raise AuthorizationError("Token invalide ou expiré.") from error

        employee = self.employee_repository.get_by_id(employee_id)

        if employee is None:
            raise AuthorizationError("L’utilisateur associé au token n’existe plus.")

        return employee